#!/usr/bin/env python3
"""Helper-only decoder check using the same arguments as exhibition playback."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from player import player_args

BASE = Path(__file__).resolve().parent


def property_value(ipc, name):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(2)
        connection.connect(str(ipc))
        connection.sendall((json.dumps({'command': ['get_property', name],
                                       'request_id': 1}) + '\n').encode())
        with connection.makefile('r') as stream:
            for line in stream:
                reply = json.loads(line)
                if reply.get('request_id') == 1:
                    return reply.get('data') if reply.get('error') == 'success' else None
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screen', choices=('a', 'b', 'shared'))
    parser.add_argument('--decoder', choices=('auto', 'drm'), default=None,
                        help='Optional trial only; does not change saved playback settings.')
    options = parser.parse_args()
    base = BASE
    settings = json.loads((base / 'settings.json').read_text())
    args = player_args(base, settings, options.screen, options.decoder)
    subprocess.run([sys.executable, str(base / 'control.py'), 'stop'], check=True)
    log = base / 'decoding.log'
    with tempfile.TemporaryDirectory(prefix='exhibit-') as directory, log.open('w') as output:
        ipc = Path(directory) / 'mpv.sock'
        args = args[:-1] + ['-v', '--input-ipc-server=' + str(ipc), args[-1]]
        process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT)
        decoder = codec = None
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    # Wait until a frame was decoded, rather than treating loading as software playback.
                    if property_value(ipc, 'time-pos') is not None:
                        decoder = property_value(ipc, 'hwdec-current')
                        codec = property_value(ipc, 'video-codec')
                        if decoder is not None:
                            break
                except (OSError, ValueError):
                    pass
                time.sleep(0.5)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    print(f'Codec: {codec or "unknown"}; active hardware decoder: {decoder or "unknown"}.')
    if decoder and decoder != 'no':
        print('Hardware decoding is active. Still test the whole movie for smooth playback and loop joins.')
    elif decoder == 'no':
        print('Software decoding is active. For the 4K shared route, ask for AV help before relying on playback.')
    else:
        print('The check could not confirm decoding. Ask your AV helper to read the log.')
    print(f'Log: {log}\nThis check stops playback. Click Start Exhibit afterwards.')
    if options.decoder:
        print('This was a trial decoder setting. Normal playback still uses the saved setting.')
    return 0 if decoder and decoder != 'no' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        sys.exit(f'Decoder check stopped: {error}')
