#!/usr/bin/env python3
"""Start, stop and disable the exhibit without killing unrelated video players."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from common import movie_path

BASE = Path(__file__).resolve().parent
UNITS = ['exhibit-a.service', 'exhibit-b.service', 'exhibit-shared.service']
MONITOR = 'exhibit-monitor.service'


def stop_players():
    # The watcher must stop first, otherwise it could undo Stop Exhibit.
    systemctl('stop', MONITOR, check=False)
    systemctl('stop', *UNITS)


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
        stop_players()
        screens = ('a', 'b') if separate else ('shared',)
        for screen in screens:
            path = movie_path(BASE, screen)
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                    '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(path)],
                                   text=True, capture_output=True, timeout=30)
            if probe.returncode or 'video' not in probe.stdout:
                raise ValueError(f'{path.name} cannot be read as a video. Copy it again or export a fresh MP4.')
        env_names = [name for name in ('WAYLAND_DISPLAY', 'DISPLAY', 'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE')
                     if name in os.environ]
        systemctl('import-environment', *env_names)
        if not (BASE / '.stop-requested').exists():
            systemctl('restart', MONITOR)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'start'
    if action in ('stop', 'disable'):
        (BASE / '.stop-requested').touch()
        if action == 'disable':
            (BASE / 'disabled').touch()
        with (BASE / '.start-lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            stop_players()
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
