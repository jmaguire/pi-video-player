#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -eq 0 ]; then
  echo 'Run this as your normal desktop user: bash install.sh (without sudo).'
  exit 1
fi
if [ ! -r /proc/device-tree/model ] || ! tr -d '\0' < /proc/device-tree/model | grep -q 'Raspberry Pi 5'; then
  echo 'This setup is for a Raspberry Pi 5. Copy the kit to the Pi and run it there.'
  exit 1
fi
if [ -z "${WAYLAND_DISPLAY:-}" ] || ! pgrep -x labwc > /dev/null; then
  echo 'Open Terminal inside the Raspberry Pi OS labwc desktop and try again.'
  exit 1
fi
echo 'Installing the video player and display tools. Internet is needed for this step.'
echo 'If a password is requested, type your Pi password. No letters will appear.'
sudo apt-get update
sudo apt-get install -y mpv wlr-randr ffmpeg python3 zenity
EXHIBIT_KIT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$EXHIBIT_KIT_DIR/configure.py"
