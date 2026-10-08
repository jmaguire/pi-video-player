#!/usr/bin/env python3
"""One native Wayland player; the compositor places it before fullscreen."""
import json
import os
from pathlib import Path
import sys
from common import movie_path


def player_args(base, settings, screen, decoder=None):
    return ['/usr/bin/mpv', '--no-config', '--vo=gpu', '--gpu-context=wayland',
            '--wayland-app-id=ddw-exhibit-' + screen, '--title=Exhibit ' + screen.upper(),
            '--fullscreen=no', '--loop-file=inf', '--osc=no', '--osd-level=0',
            '--cursor-autohide=always', '--input-default-bindings=no',
            '--input-vo-keyboard=no', '--input-terminal=no', '--stop-screensaver=yes',
            '--hwdec=' + (decoder or settings.get('hwdec_' + screen, 'auto')),
            '--panscan=0', '--keepaspect=yes',
            '--audio=' + ('auto' if settings['audio_' + screen] else 'no'),
            '--audio-device=' + settings['device_' + screen], str(movie_path(base, screen))]


def main():
    base = Path(__file__).resolve().parent
    settings = json.loads((base / 'settings.json').read_text())
    args = player_args(base, settings, sys.argv[1])
    os.execv(args[0], args)


if __name__ == '__main__':
    main()
