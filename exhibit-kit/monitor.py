#!/usr/bin/env python3
"""Wait indefinitely for screens and reapply placement after HDMI changes."""
import datetime
import json
from pathlib import Path
import signal
import subprocess
import time
from common import parse_outputs

BASE = Path(__file__).resolve().parent
PLAYERS = ['exhibit-a.service', 'exhibit-b.service', 'exhibit-shared.service']


class ScreenWatch:
    def __init__(self, required, settle_polls=3):
        self.required = set(required)
        self.settle_polls = settle_polls
        self.previous = None
        self.stable = 0
        self.playing = False

    def update(self, outputs):
        present = {o['name']: o for o in outputs if o['enabled']}
        ready = self.required <= present.keys()
        fingerprint = tuple((name, tuple(present[name]['layout']))
                            for name in sorted(self.required)) if ready else None
        actions = []
        if not ready or fingerprint != self.previous:
            if self.playing:
                actions.append('stop')
            self.playing = False
            self.stable = 0
        self.previous = fingerprint
        if ready:
            self.stable += 1
            if self.stable >= self.settle_polls and not self.playing:
                actions.append('restart')
                self.playing = True
        return actions, ready


def systemctl(*args):
    subprocess.run(['systemctl', '--user', *args], check=True, timeout=20)


def log(message):
    (BASE / 'startup.log').write_text(str(datetime.datetime.now()) + '\n' + message + '\n')
    print(message, flush=True)


def terminate(signum, frame):
    raise SystemExit(0)


def main():
    signal.signal(signal.SIGTERM, terminate)
    settings = json.loads((BASE / 'settings.json').read_text())
    separate = settings['mode'] == 'independent'
    required = [settings['output_a']] + ([settings['output_b']] if separate else [])
    active = ['exhibit-a.service', 'exhibit-b.service'] if separate else ['exhibit-shared.service']
    watch = ScreenWatch(required)
    waiting = None
    try:
        systemctl('stop', *PLAYERS)
        while True:
            try:
                result = subprocess.run(['wlr-randr'], text=True, capture_output=True, timeout=5)
                outputs = parse_outputs(result.stdout) if result.returncode == 0 else []
            except (OSError, subprocess.SubprocessError):
                outputs = []
            actions, ready = watch.update(outputs)
            if waiting != (not ready):
                if not ready:
                    log('Waiting for the assigned screens. Turn both screens (or the controller) on; '
                        'playback will resume automatically. There is no time limit.')
                waiting = not ready
            for action in actions:
                systemctl(action, *(PLAYERS if action == 'stop' else active))
                if action == 'stop':
                    log('Screen connection/layout changed. Playback stopped while screens settle.')
                else:
                    log('Playback started on the assigned screens.')
            time.sleep(1)
    finally:
        # Also clean up players if this watcher crashes or is restarted.
        systemctl('stop', *PLAYERS)


if __name__ == '__main__':
    main()
