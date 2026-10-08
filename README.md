# Two screens. One small computer.

An illustrated Raspberry Pi 5 video-looping guide for an artist's graduate exhibition at Dutch Design Week, with a companion setup kit.

**Read [the 16-page instruction manual](docs/Two-Screen-Exhibition-Manual.pdf) first.** It covers equipment, video exports, installation, portrait screens, sound, rehearsal, troubleshooting and a printable daily crew card on page 14.

## Playback choices

| Artwork requirement | Equipment and behaviour |
| --- | --- |
| Independent loops | One Pi 5, two micro-HDMI cables and two monitors. A separate mpv player loops each movie. The players are not synchronized. |
| Shared timeline | One combined movie sent from Pi HDMI0 through a separate cropping video wall controller. A technician configures one crop per screen. See manual pages 10-11. |
| Exact frame timing | Have an AV technician verify output synchronization, display latency and loop behaviour. The two independent players cannot provide this. The manual also describes a specialist BrightSign alternative. |

Shared mode does **not** span a software window across the Pi's two HDMI ports. It requires a preconfigured video wall controller; an ordinary HDMI splitter cannot show different crop regions. The 4K shared-file route also needs a real playback test, because hardware decoding depends on the installed media stack. A lower-resolution proof of concept and AV-computer fallback are described in the manual.

## Setup on the Pi

Use a fresh, dedicated microSD card with **Raspberry Pi OS (64-bit), Trixie, with Desktop** and the default Wayland/labwc desktop. Fit active cooling and use the official 27 W supply. Arrange the screens, enable desktop auto login and disable blanking as described in the manual.

Copy the entire `exhibit-kit` directory into your Pi user's Home folder. In Terminal **on the Pi**, run:

```sh
cd ~/exhibit-kit
bash install.sh
```

Run as your ordinary desktop user. Do not add `sudo` before the installer; it requests elevated privileges only to install packages from the OS repositories. Internet is needed for package installation, but local playback works offline.

Choose the wiring mode, display outputs and silent playback or one soundtrack. Copy the movies into `~/exhibit`:

- Independent mode: `video-a.mp4` and `video-b.mp4`.
- Shared mode: `shared.mp4`.

Click **Start Exhibit**, or run:

```sh
python3 ~/exhibit/control.py start
```

Reboot to verify automatic startup, then run the final artwork overnight with the exact exhibition hardware.

## Operation

```sh
# Stop for this desktop session; playback resumes after the next normal boot.
python3 ~/exhibit/control.py stop

# Start/restart and re-enable future automatic starts.
python3 ~/exhibit/control.py start

# Select sound outputs for each movie. Stops playback while editing.
python3 ~/exhibit/audio.py

# Stop and disable future automatic starts until Start Exhibit is used again.
python3 ~/exhibit/control.py disable
```

The installer creates desktop and application-menu **Start Exhibit** and **Stop Exhibit** controls. Normal mpv keyboard shortcuts are disabled to prevent accidental pauses. Use the controls above.

Shut down from the Pi desktop before disconnecting its power. Power the monitors/controller before the Pi when starting. Keep a tested clone of the finished SD card available.

## What the kit changes

- Installs `mpv`, `wlr-randr`, `ffmpeg`, `python3` and `zenity` using apt.
- Adds native Wayland app-ID rules to `~/.config/labwc/rc.xml`, moving a player to its assigned output before fullscreen. Existing unrelated desktop settings are preserved.
- Saves configuration backups in `~/exhibit/backups/<timestamp>`.
- Creates `~/.config/systemd/user/exhibit-{a,b,shared}.service` player services, restarted five seconds after exit. Only services for the chosen mode are started.
- Creates the `~/.config/autostart/exhibit.desktop` entry. It waits for required enabled displays and imports the desktop's Wayland environment before starting the services.
- Saves editable playback/audio settings and startup diagnostics under `~/exhibit`.

It does not configure screen resolution, rotation, desktop auto login, monitor sleep timers or controller crops. Follow the manual for those settings. It keeps existing movies when reinstalled. Changing mode/output selection by rerunning the installer resets the kit's audio settings, which can then be selected again.

Restart-on-exit cannot detect a player that is still running with a frozen image. Neither seamless loop joins nor playback performance is guaranteed. Those checks belong in the rehearsal.

## Files

- `docs/Two-Screen-Exhibition-Manual.pdf`: finished A4 guide with diagrams and clickable official references.
- `downloads/Exhibition-Setup-Kit.zip`: the manual and ready-to-copy kit.
- `exhibit-kit/`: installer and runtime scripts, requiring only Python's standard library beyond OS packages.
- `tools/build_manual.py`: editable text/layout source for the PDF.
- `tools/package_kit.py`: creates the ZIP without cache or development files.
- `tests/test_setup.py`: configuration preservation, installer and player-argument checks.

## Developer checks and document build

The setup tests do not require a Pi:

```sh
python3 -m unittest discover -s tests -v
bash -n exhibit-kit/install.sh
python3 -m compileall -q exhibit-kit
```

To regenerate the manual, install ReportLab in a local virtual environment and run:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-docs.txt
.venv/bin/python tools/build_manual.py --output docs/Two-Screen-Exhibition-Manual.pdf
.venv/bin/python tools/package_kit.py
```

The build uses Arial/DIN/Courier on macOS, with Liberation/DejaVu font fallbacks on Linux. Font changes can affect layout, so render and inspect every updated PDF page before publishing. Poppler's `pdftoppm` can render the pages for review. No OS fonts are bundled in this repository.

## Validation status

The scripts passed static syntax and configuration-logic tests; the PDF was rendered and visually reviewed. **No physical Raspberry Pi, video wall controller or venue monitors were available for playback validation.** The supplied guide requires a full rehearsal with the final artwork and hardware. Official references are linked on page 16.
