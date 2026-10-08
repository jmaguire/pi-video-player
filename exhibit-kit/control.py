#!/usr/bin/env python3
"""Start, stop and disable the exhibit without killing unrelated video players."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import parse_outputs

BASE = Path(__file__).resolve().parent
UNITS = ['exhibit-a.service', 'exhibit-b.service', 'exhibit-shared.service']


def systemctl(*args, check=True):
    return subprocess.run(['systemctl', '--user', *args], check=check)


def report(message):
    print(message, file=sys.stderr)
    (BASE / 'startup.log').write_text(str(datetime.datetime.now()) + '\n' + message + '\n')
    if os.environ.get('WAYLAND_DISPLAY'):
        subprocess.run(['zenity', '--error', '--title=Exhibit needs attention', '--text=' + message],
                       check=False)


def start(automatic=False):
    if automatic and (BASE / 'disabled').exists():
        return
    if not os.environ.get('WAYLAND_DISPLAY'):
        raise ValueError('Open Start Exhibit or Terminal inside the Pi desktop.')
    if not automatic:
        (BASE / 'disabled').unlink(missing_ok=True)
    (BASE / '.stop-requested').unlink(missing_ok=True)
    # Avoid two startup attempts when someone clicks during login.
    with (BASE / '.start-lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        settings = json.loads((BASE / 'settings.json').read_text())
        separate = settings['mode'] == 'independent'
        filenames = ['video-a.mp4', 'video-b.mp4'] if separate else ['shared.mp4']
        for name in filenames:
            path = BASE / name
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f'Missing or empty movie: {name}. Put it in Home > exhibit, then click Start Exhibit.')
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                    '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(path)],
                                   text=True, capture_output=True, timeout=30)
            if probe.returncode or 'video' not in probe.stdout:
                raise ValueError(f'{name} cannot be read as a video. Copy it again or export a fresh MP4.')
        required = {settings['output_a']}
        if separate:
            required.add(settings['output_b'])
        # Power the screens before the Pi. This wait allows detection to settle.
        for _ in range(90):
            if (BASE / '.stop-requested').exists():
                return
            result = subprocess.run(['wlr-randr'], text=True, capture_output=True, timeout=5)
            enabled = {o['name'] for o in parse_outputs(result.stdout) if o['enabled']}
            if required <= enabled:
                break
            time.sleep(1)
        else:
            raise ValueError('A required display was not detected within 90 seconds. Turn on both screens '
                             '(or the controller), check HDMI inputs and Screens settings, then click Start Exhibit.')
        env_names = [name for name in ('WAYLAND_DISPLAY', 'DISPLAY', 'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE')
                     if name in os.environ]
        systemctl('import-environment', *env_names)
        time.sleep(2)
        if (BASE / '.stop-requested').exists():
            return
        inactive = ['exhibit-shared.service'] if separate else ['exhibit-a.service', 'exhibit-b.service']
        active = ['exhibit-a.service', 'exhibit-b.service'] if separate else ['exhibit-shared.service']
        systemctl('stop', *inactive)
        systemctl('restart', *active)
        (BASE / 'startup.log').write_text(str(datetime.datetime.now()) + '\nPlayback started.\n')


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'start'
    if action in ('stop', 'disable'):
        (BASE / '.stop-requested').touch()
        if action == 'disable':
            (BASE / 'disabled').touch()
        systemctl('stop', *UNITS)
    elif action in ('start', 'autostart'):
        start(automatic=action == 'autostart')
    else:
        raise ValueError('Use start, stop, disable or autostart.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report(str(error))
        sys.exit(1)
