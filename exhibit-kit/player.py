#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

base = Path(__file__).resolve().parent
screen = sys.argv[1]
settings = json.loads((base / 'settings.json').read_text())
movie = {'a': 'video-a.mp4', 'b': 'video-b.mp4', 'shared': 'shared.mp4'}[screen]
args = ['/usr/bin/mpv', '--no-config', '--vo=gpu', '--gpu-context=wayland',
        '--wayland-app-id=ddw-exhibit-' + screen, '--title=Exhibit ' + screen.upper(),
        '--fullscreen=no', '--loop-file=inf', '--osc=no', '--osd-level=0',
        '--cursor-autohide=always', '--input-default-bindings=no',
        '--input-vo-keyboard=no', '--input-terminal=no', '--stop-screensaver=yes',
        '--hwdec=auto', '--panscan=0', '--keepaspect=yes',
        '--audio=' + ('auto' if settings['audio_' + screen] else 'no'),
        '--audio-device=' + settings['device_' + screen], str(base / movie)]
os.execv(args[0], args)
