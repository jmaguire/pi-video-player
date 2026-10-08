#!/usr/bin/env python3
"""Interactive installer. Run on the Pi, as the desktop user."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from common import patch_rules, parse_outputs


def choose(prompt, items, default=1):
    print('\n' + prompt)
    for index, label in enumerate(items, 1):
        print(f'  {index}. {label}')
    while True:
        answer = input(f'Enter a number, then press Enter [{default}]: ').strip()
        try:
            value = int(answer or default)
            if 1 <= value <= len(items):
                return value - 1
        except ValueError:
            pass
        print('Please choose one of the numbers above.')


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.exhibit-tmp')
    temporary.write_bytes(content if isinstance(content, bytes) else content.encode())
    temporary.replace(path)


def main():
    home = Path.home()
    kit = Path(__file__).resolve().parent
    exhibit = home / 'exhibit'
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config')))
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
    exhibit.mkdir(exist_ok=True)
    mode_index = choose('Choose your wiring (see pages 2 and 10 of the manual):', [
        'INDEPENDENT: one video per Pi HDMI port; no extra controller',
        'SHARED TIMELINE: one combined movie through an external video wall controller',
    ])
    mode = ('independent', 'shared')[mode_index]
    display_text = subprocess.check_output(['wlr-randr'], text=True)
    print('\nDetected displays:\n' + display_text)
    outputs = [o['name'] for o in parse_outputs(display_text) if o['enabled']]
    needed = 2 if mode == 'independent' else 1
    if len(outputs) < needed:
        sys.exit(f'Need {needed} enabled display output(s). Turn the screens on and check Screens settings first.')
    label = 'Which output is Screen A?' if mode == 'independent' else 'Which output feeds the video wall controller?'
    output_a = outputs[choose(label + ' Usually HDMI-A-1.', outputs)]
    output_b = None
    if mode == 'independent':
        remaining = [o for o in outputs if o != output_a]
        output_b = remaining[choose('Which output is Screen B? Usually HDMI-A-2.', remaining)]
    audio_index = choose('Choose sound (you can change it later):', [
        'SILENT: no audio from either video',
        'SOUND: Video A (or the shared movie) uses the desktop default sound output',
    ])
    print('\nThis will add exhibition window rules, startup and Start/Stop controls.')
    print('Existing labwc configuration will be backed up; your movies will be kept.')
    # Prepare and validate the XML before changing the desktop configuration.
    rc = config_home / 'labwc/rc.xml'
    original = rc.read_bytes() if rc.exists() else None
    base = original
    if base is None:
        for directory in os.environ.get('XDG_CONFIG_DIRS', '/etc/xdg').split(':'):
            candidate = Path(directory) / 'labwc/rc.xml'
            if candidate.exists():
                base = candidate.read_bytes()
                break
    if base is None:
        base = b'<?xml version="1.0"?><labwc_config />'
    updated_xml = patch_rules(base, output_a, output_b)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = exhibit / 'backups' / stamp
    backup.mkdir(parents=True)
    for name, path in [('rc.xml', rc), ('settings.json', exhibit / 'settings.json'),
                       ('exhibit.desktop', config_home / 'autostart/exhibit.desktop')]:
        if path.exists():
            shutil.copy2(path, backup / name)
    if original is None:
        (backup / 'NO_PREVIOUS_USER_RC.txt').write_text('No user rc.xml existed before this installation.\n')
    subprocess.run(['systemctl', '--user', 'stop', 'exhibit-a.service', 'exhibit-b.service',
                    'exhibit-shared.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for name in ('common.py', 'control.py', 'player.py', 'audio.py'):
        shutil.copy2(kit / name, exhibit / name)
    settings = {'mode': mode, 'output_a': output_a, 'output_b': output_b,
                'audio_a': audio_index == 1, 'audio_b': False,
                'audio_shared': audio_index == 1,
                'device_a': 'auto', 'device_b': 'auto', 'device_shared': 'auto'}
    atomic_write(exhibit / 'settings.json', json.dumps(settings, indent=2) + '\n')
    atomic_write(rc, updated_xml)
    for screen in ('a', 'b', 'shared'):
        unit = f'''[Unit]
Description=Exhibition video {screen}
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/usr/bin/python3 "%h/exhibit/player.py" {screen}
Restart=always
RestartSec=5s
TimeoutStopSec=10s
'''
        atomic_write(config_home / f'systemd/user/exhibit-{screen}.service', unit)
    # Raspberry Pi OS's desktop session runs standard XDG autostart entries.
    desktop_base = '''[Desktop Entry]
Type=Application
Terminal=false
Categories=AudioVideo;
'''
    # Usernames generated by Imager contain no spaces; quote the absolute path anyway.
    control_path = str(exhibit / 'control.py').replace('\\', '\\\\').replace('"', '\\"')
    atomic_write(config_home / 'autostart/exhibit.desktop', desktop_base +
                 f'Name=Exhibit Playback\nExec=/usr/bin/python3 "{control_path}" autostart\n')
    try:
        desktop_dir = Path(subprocess.check_output(['xdg-user-dir', 'DESKTOP'], text=True).strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        desktop_dir = home / 'Desktop'
    for action, title, icon in [('start', 'Start Exhibit', 'media-playback-start'),
                                ('stop', 'Stop Exhibit', 'media-playback-stop')]:
        text = desktop_base + f'Name={title}\nIcon={icon}\nExec=/usr/bin/python3 "{control_path}" {action}\n'
        for path in (data_home / f'applications/exhibit-{action}.desktop',
                     desktop_dir / f'{title}.desktop'):
            atomic_write(path, text)
            path.chmod(0o755)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['labwc', '--reconfigure'], check=True)
    (exhibit / 'disabled').unlink(missing_ok=True)
    print('\nSETUP COMPLETE. Playback has not been started yet.')
    print(f'Copy your movie file(s) to {exhibit}')
    print('Use video-a.mp4 and video-b.mp4 for independent mode, or shared.mp4 for shared mode.')
    print('Then double-click Start Exhibit, or run: python3 ~/exhibit/control.py start')
    print('Desktop auto login and screen blanking are configured in Control Centre (manual page 7).')
    print(f'Configuration backups: {backup}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f'Setup stopped: {error}. Keep this message for your helper.')
