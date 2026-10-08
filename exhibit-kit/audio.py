#!/usr/bin/env python3
"""Optional guided sound routing. Playback must be stopped first."""
import json
from pathlib import Path
import re
import subprocess
import sys
from common import require_writable_setup

try:
    require_writable_setup()
except ValueError as error:
    sys.exit(str(error))

base = Path(__file__).resolve().parent
settings_path = base / 'settings.json'
settings = json.loads(settings_path.read_text())
subprocess.run([sys.executable, str(base / 'control.py'), 'stop'], check=True)
result = subprocess.run(['mpv', '--no-config', '--audio-device=help'], capture_output=True, text=True, check=True)
devices = re.findall(r"^\s*'([^']+)'\s*\((.*)\)\s*$", result.stdout + result.stderr, re.MULTILINE)
if not devices:
    sys.exit('No sound outputs found. Connect speakers / enable HDMI sound, then try again.')
print('Choose sound for each movie. A display position does not choose its audio output.')
print('0. Silent')
for index, (device, label) in enumerate(devices, 1):
    print(f'{index}. {label} [{device}]')
screens = ('a', 'b') if settings['mode'] == 'independent' else ('shared',)
for screen in screens:
    while True:
        answer = input(f'Audio for {screen.upper()} (number; Enter = silent): ').strip() or '0'
        if answer.isdigit() and 0 <= int(answer) <= len(devices):
            choice = int(answer)
            settings['audio_' + screen] = choice != 0
            settings['device_' + screen] = devices[choice - 1][0] if choice else 'auto'
            break
        print('Choose a number from the list.')
temporary = settings_path.with_suffix('.tmp')
temporary.write_text(json.dumps(settings, indent=2) + '\n')
temporary.replace(settings_path)
print('Sound settings saved. Click Start Exhibit and listen at each screen.')
print('If two movies use the same output, their sound will mix. Choose distinct named outputs to separate them.')
