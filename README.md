# Two screens. One small computer.

An illustrated Raspberry Pi 5 video-looping guide for an artist's graduate exhibition at Dutch Design Week, with a companion setup kit.

**Read [the 19-page instruction manual](docs/Two-Screen-Exhibition-Manual.pdf) first.** It covers equipment, video exports, installation, portrait screens, sound, rehearsal, troubleshooting and a printable daily crew card on page 14.

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

Choose the wiring mode, display outputs and silent playback or one soundtrack. Keep your existing filenames. Copy the movies into the folders inside `~/exhibit`:

- Independent mode: one MP4 in `A` and one MP4 in `B`.
- Shared mode: one combined MP4 in `Shared`.

Each folder must contain exactly one non-empty MP4. Hidden macOS metadata files are ignored. Multiple MP4s are rejected rather than choosing a version silently. Existing `video-a.mp4`, `video-b.mp4` and `shared.mp4` files directly in `~/exhibit` remain supported when the corresponding folder is empty.

Click **Start Exhibit**, or run:

```sh
python3 ~/exhibit/control.py start
```

**Before travelling, rehearse on the real Pi with the final files, monitors, cables, enclosure and sound.** Check overnight playback, monitor off/on recovery, slow screen startup, pop-ups, offline operation and the venue power cycle (manual page 13). Automated tests cannot establish these physical behaviours.

## Updating an existing Pi

Stop Exhibit, unlock protection if active and reboot. Replace the old `Home > exhibit-kit` folder with the new kit, then rerun `bash install.sh` inside it. Choose the wiring, outputs and sound again; reinstallation resets audio choices. Your movies are kept, including the earlier fixed-filename layout. Repeat the screen-recovery and startup rehearsal before protecting the card again.

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

Close with **two brief Pi 5 power-button presses in quick succession**, then wait for the shutdown cue verified in rehearsal before disconnecting power. Holding the button forces power off. Keep the button accessible in the plinth. Power the monitors/controller before the Pi when opening.

The screen watcher keeps retrying without a startup timeout. When an assigned HDMI output disappears, it stops the players; after all required outputs settle, it restarts them so window placement rules reapply. Both independent loops restart from the beginning. Detection takes about a second, so a brief misplaced image can occur; a monitor that remains connected over HDMI while powered off cannot be detected. If recovery fails, turn both screens on and use **Start Exhibit**.

For venue power cuts, a helper can enable **both root overlay and boot-partition protection** after all changes and the spare-card test (pages 16-17). Changes made with the overlay active disappear on reboot. Unlock both protections and reboot before changing artwork or settings; the installer and sound helper refuse protected setup changes. Clean shutdown remains the daily routine. Protect and boot-test both cards separately.

## What the kit changes

- Installs `mpv`, `wlr-randr`, `ffmpeg`, `python3` and `zenity` using apt.
- Adds native Wayland app-ID rules to `~/.config/labwc/rc.xml`, moving a player to its assigned output before fullscreen. Existing unrelated desktop settings are preserved.
- Saves configuration backups in `~/exhibit/backups/<timestamp>`.
- Creates `~/.config/systemd/user/exhibit-{a,b,shared}.service` player services, restarted five seconds after exit. Only services for the chosen mode are started.
- Creates `exhibit-monitor.service`, an ongoing user-level display watcher. It waits for required enabled outputs, stops players after detection/layout changes and restarts them after three stable observations.
- Creates the `~/.config/autostart/exhibit.desktop` entry. It validates the movies, imports the desktop's Wayland environment and starts the watcher. Stop Exhibit stops the watcher before stopping players; startup does not enable services outside the desktop session.
- Saves editable playback/audio settings and startup diagnostics under `~/exhibit`.

It does not configure screen resolution, rotation, desktop auto login, monitor sleep timers or controller crops. Follow the manual for those settings. It keeps existing movies when reinstalled. Changing mode/output selection by rerunning the installer resets the kit's audio settings, which can then be selected again.

Restart-on-exit cannot detect a player that is still running with a frozen image. Neither seamless loop joins nor playback performance is guaranteed. Those checks belong in the rehearsal.

## Helper decoder check

For the 4K shared route, run this on the Pi with the final movie:

```sh
python3 ~/exhibit/diagnose.py shared
```

It stops exhibition playback, launches the movie with the actual kit arguments, queries mpv's `hwdec-current` property, stops the trial and saves `~/exhibit/decoding.log`. A named hardware decoder confirms acceleration; `no` means software. This check cannot certify smooth playback. Click Start Exhibit afterwards.

An AV helper can try `--decoder drm`; the trial does not change normal playback. If successful, set `hwdec_shared` to `drm` in `settings.json` while protection is off and repeat the normal playback rehearsal. Do not rely on a plain `mpv -v` test that omits the kit's decoder and Wayland settings.

## Files

- `docs/Two-Screen-Exhibition-Manual.pdf`: finished A4 guide with diagrams and clickable official references.
- `downloads/Exhibition-Setup-Kit.zip`: the manual and ready-to-copy kit.
- `exhibit-kit/`: installer and runtime scripts, requiring only Python's standard library beyond OS packages.
- `tools/build_manual.py`: editable text/layout source for the PDF.
- `tools/package_kit.py`: creates the ZIP without cache or development files.
- `tests/test_setup.py`: configuration preservation, installation, filenames, screen-recovery state transitions, Start / Stop ordering, protection guards and shared playback/diagnostic arguments.

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

The scripts passed static syntax and configuration-logic tests; the PDF was rendered and visually reviewed. **No physical Raspberry Pi, video wall controller or venue monitors were available for playback validation.** The supplied guide requires a full rehearsal with the final artwork and hardware. Official references are linked on page 19.
