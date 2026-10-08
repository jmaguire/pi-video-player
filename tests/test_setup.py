import contextlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

KIT = Path(__file__).resolve().parent.parent / 'exhibit-kit'
sys.path.insert(0, str(KIT))
import common
import configure
import control
import monitor
import player
import diagnose

OUTPUTS = '''HDMI-A-1 "Screen A (HDMI-A-1)"
  Enabled: yes
  Modes:
    1920x1080 px, 60 Hz (current)
HDMI-A-2 "Screen B (HDMI-A-2)"
  Enabled: yes
DP-1 "Unconnected screen"
  Enabled: no
'''


class KitTests(unittest.TestCase):
    def test_rules_preserve_other_desktop_settings_and_stay_idempotent(self):
        initial = b'''<labwc_config><!-- keep this --><keyboard><keybind key="C-A-t"/></keyboard>
          <windowRules><windowRule title="Other app"><action name="Maximize"/></windowRule></windowRules>
          </labwc_config>'''
        first = common.patch_rules(initial, 'HDMI-A-1', 'HDMI-A-2')
        second = common.patch_rules(first, 'HDMI-A-1', 'HDMI-A-2')
        root = ET.fromstring(second)
        self.assertIsNotNone(root.find('keyboard/keybind'))
        self.assertIsNotNone(root.find('windowRules/windowRule[@title="Other app"]'))
        for app, output in [('ddw-exhibit-a', 'HDMI-A-1'), ('ddw-exhibit-b', 'HDMI-A-2')]:
            rules = root.findall(f'windowRules/windowRule[@identifier="{app}"]')
            self.assertEqual(len(rules), 1)
            self.assertIsNone(rules[0].get('matchOnce'))
            self.assertEqual([a.get('name') for a in rules[0]], ['MoveToOutput', 'ToggleFullscreen'])
            self.assertEqual(rules[0][0].get('output'), output)
        self.assertIn(b'keep this', second)

    def test_namespace_and_reconfigured_outputs(self):
        xml = b'<labwc_config xmlns="urn:test"><windowRules/></labwc_config>'
        updated = common.patch_rules(xml, 'HDMI-A-7', 'HDMI-A-8')
        updated = common.patch_rules(updated, 'HDMI-A-7')
        root = ET.fromstring(updated)
        self.assertEqual(root.tag, '{urn:test}labwc_config')
        self.assertEqual(len(root.findall('{urn:test}windowRules/{urn:test}windowRule')), 2)

    def test_invalid_config_is_rejected(self):
        with self.assertRaises(ValueError):
            common.patch_rules(b'<wrong-root />', 'HDMI-A-1')

    def test_disabled_display_is_not_ready(self):
        outputs = common.parse_outputs(OUTPUTS)
        enabled = [o['name'] for o in outputs if o['enabled']]
        self.assertEqual(enabled, ['HDMI-A-1', 'HDMI-A-2'])
        preferred = common.parse_outputs(OUTPUTS.replace('(current)', '(preferred, current)'))
        self.assertIn('1920x1080 px, 60 Hz (preferred, current)', preferred[0]['layout'])

    def test_installer_writes_controls_units_and_backup_without_replacing_movies(self):
        for mode, responses, expected in [('independent', ['1', '1', '1', '1'], 'video-a.mp4'),
                                          ('shared', ['2', '1', '2'], 'shared.mp4')]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                home = Path(td)
                config_dir = home / '.config'
                rc = config_dir / 'labwc/rc.xml'
                rc.parent.mkdir(parents=True)
                original = b'<labwc_config><keyboard><keybind key="C-A-t"/></keyboard></labwc_config>'
                rc.write_bytes(original)
                movie = home / 'exhibit' / expected
                movie.parent.mkdir()
                movie.write_bytes(b'keep existing artwork')
                def fake_output(args, **kwargs):
                    return OUTPUTS if args[0] == 'wlr-randr' else str(home / 'Desktop') + '\n'
                with patch.object(configure.Path, 'home', return_value=home), \
                     patch.object(configure, 'require_writable_setup'), \
                     patch.dict('os.environ', {'XDG_CONFIG_HOME': str(config_dir),
                                               'XDG_DATA_HOME': str(home / '.local/share')}), \
                     patch('builtins.input', side_effect=responses), \
                     patch.object(configure.subprocess, 'check_output', side_effect=fake_output), \
                     patch.object(configure.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                     contextlib.redirect_stdout(io.StringIO()):
                    configure.main()
                settings = json.loads((home / 'exhibit/settings.json').read_text())
                self.assertEqual(settings['mode'], mode)
                self.assertEqual(movie.read_bytes(), b'keep existing artwork')
                backup = list((home / 'exhibit/backups').glob('*/rc.xml'))
                self.assertEqual(len(backup), 1)
                self.assertEqual(backup[0].read_bytes(), original)
                self.assertTrue((home / '.config/autostart/exhibit.desktop').exists())
                self.assertTrue((home / 'Desktop/Start Exhibit.desktop').exists())
                unit = (home / '.config/systemd/user/exhibit-a.service').read_text()
                self.assertIn('Restart=always', unit)
                self.assertIn('RestartSec=5s', unit)
                self.assertNotIn('WantedBy', unit)
                self.assertTrue((home / 'exhibit/A').is_dir())
                self.assertTrue((home / 'exhibit/B').is_dir())
                self.assertTrue((home / 'exhibit/Shared').is_dir())
                watcher = (home / '.config/systemd/user/exhibit-monitor.service').read_text()
                self.assertIn('monitor.py', watcher)
                self.assertIn('Restart=always', watcher)

    def test_player_uses_native_wayland_and_waits_for_window_rule_fullscreen(self):
        class ExecIntercept(Exception):
            pass
        recorded = []
        def intercept(binary, args):
            recorded.extend(args)
            raise ExecIntercept()
        config = {'audio_a': False, 'device_a': 'auto'}
        with patch.object(Path, 'read_text', return_value=json.dumps(config)), \
             patch('common.movie_path', return_value=Path('/art/Final film.mp4')), \
             patch('sys.argv', ['player.py', 'a']), patch('os.execv', side_effect=intercept):
            with self.assertRaises(ExecIntercept):
                runpy.run_path(str(KIT / 'player.py'), run_name='__main__')
        self.assertIn('--gpu-context=wayland', recorded)
        self.assertIn('--wayland-app-id=ddw-exhibit-a', recorded)
        self.assertIn('--fullscreen=no', recorded)
        self.assertIn('--audio=no', recorded)
        self.assertIn('--loop-file=inf', recorded)
        self.assertEqual(recorded[-1], '/art/Final film.mp4')

    def test_artist_filenames_and_legacy_files_with_ambiguous_movies_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            folder = base / 'A'
            folder.mkdir()
            legacy = base / 'video-a.mp4'
            legacy.write_bytes(b'old artwork')
            self.assertEqual(common.movie_path(base, 'a'), legacy)
            artwork = folder / 'Graduation — final cut.MP4'
            artwork.write_bytes(b'new artwork')
            (folder / '._Graduation.mp4').write_bytes(b'mac metadata')
            self.assertEqual(common.movie_path(base, 'a'), artwork)
            (folder / 'Old version.mp4').write_bytes(b'old')
            with self.assertRaisesRegex(ValueError, 'more than one MP4'):
                common.movie_path(base, 'a')

    def test_missing_and_empty_movie_require_artist_action(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            with self.assertRaisesRegex(ValueError, 'Home > exhibit > B'):
                common.movie_path(base, 'b')
            (base / 'B').mkdir()
            (base / 'B/Empty.mp4').touch()
            with self.assertRaisesRegex(ValueError, 'non-empty MP4'):
                common.movie_path(base, 'b')

    def test_screen_watch_waits_beyond_old_timeout_and_recovers_from_disconnect(self):
        watch = monitor.ScreenWatch(['HDMI-A-1', 'HDMI-A-2'])
        full = common.parse_outputs(OUTPUTS)
        one = common.parse_outputs(OUTPUTS.replace('  Enabled: yes\nDP-1', '  Enabled: no\nDP-1'))
        for _ in range(200):
            self.assertEqual(watch.update(one), ([], False))
        self.assertEqual(watch.update(full), ([], True))
        self.assertEqual(watch.update(full), ([], True))
        self.assertEqual(watch.update(full), (['restart'], True))
        self.assertEqual(watch.update(full), ([], True))
        self.assertEqual(watch.update(one), (['stop'], False))
        self.assertEqual(watch.update(one), ([], False))
        watch.update(full)
        watch.update(full)
        self.assertEqual(watch.update(full), (['restart'], True))

    def test_layout_changes_restart_and_unrelated_outputs_do_not(self):
        watch = monitor.ScreenWatch(['HDMI-A-1'], settle_polls=1)
        full = common.parse_outputs(OUTPUTS)
        self.assertEqual(watch.update(full)[0], ['restart'])
        changed = common.parse_outputs(OUTPUTS.replace('60 Hz (current)', '50 Hz (current)'))
        self.assertEqual(watch.update(changed)[0], ['stop', 'restart'])
        self.assertEqual(watch.update(changed[:-1])[0], [])
        self.assertEqual(watch.update([])[0], ['stop'])

    def test_start_validates_movies_then_starts_watcher_without_waiting_for_screens(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / 'settings.json').write_text(json.dumps({'mode': 'independent'}))
            for folder in ('A', 'B'):
                (base / folder).mkdir()
                (base / folder / 'Final.mp4').write_bytes(b'artwork')
            with patch.object(control, 'BASE', base), \
                 patch.dict('os.environ', {'WAYLAND_DISPLAY': 'wayland-0'}), \
                 patch.object(control, 'systemctl') as systemctl, \
                 patch.object(control.subprocess, 'run', return_value=
                              subprocess.CompletedProcess([], 0, stdout='video\n')) as probe:
                control.start()
            self.assertEqual(probe.call_count, 2)
            self.assertEqual(systemctl.call_args_list[-1].args, ('restart', control.MONITOR))

    def test_stop_shuts_down_watcher_before_players_and_disabled_autostart_stays_off(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            with patch.object(control, 'BASE', base), \
                 patch('sys.argv', ['control.py', 'disable']), \
                 patch.object(control, 'systemctl') as systemctl:
                control.main()
                self.assertEqual(systemctl.call_args_list[0].args, ('stop', control.MONITOR))
                self.assertEqual(systemctl.call_args_list[1].args, ('stop', *control.UNITS))
                systemctl.reset_mock()
                control.start(automatic=True)
                systemctl.assert_not_called()

    def test_protected_mode_refuses_temporary_setup_changes(self):
        for mounts in ('overlay / overlay rw 0 0\n', '/dev/mmcblk0p1 /boot/firmware vfat ro,relatime 0 0\n'):
            with self.subTest(mounts=mounts), patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'read_text', return_value=mounts):
                with self.assertRaisesRegex(ValueError, 'Protected exhibition mode'):
                    common.require_writable_setup()

    def test_diagnostic_and_normal_playback_share_arguments(self):
        settings = {'audio_shared': False, 'device_shared': 'auto'}
        with patch.object(player, 'movie_path', return_value=Path('/art/Shared.mp4')):
            normal = player.player_args(Path('/art'), settings, 'shared')
            trial = player.player_args(Path('/art'), settings, 'shared', 'drm')
        self.assertIn('--hwdec=auto', normal)
        self.assertIn('--hwdec=drm', trial)
        self.assertEqual([a for a in normal if not a.startswith('--hwdec=')],
                         [a for a in trial if not a.startswith('--hwdec=')])

    def test_watcher_drives_correct_services_for_each_mode_and_cleans_up(self):
        for mode, active in [('independent', ['exhibit-a.service', 'exhibit-b.service']),
                             ('shared', ['exhibit-shared.service'])]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                base = Path(td)
                (base / 'settings.json').write_text(json.dumps({
                    'mode': mode, 'output_a': 'HDMI-A-1', 'output_b': 'HDMI-A-2'}))
                full = subprocess.CompletedProcess([], 0, stdout=OUTPUTS)
                failed_query = subprocess.TimeoutExpired('wlr-randr', 5)
                replies = [full] * 3 + [failed_query] + [full] * 3
                with patch.object(monitor, 'BASE', base), \
                     patch.object(monitor.signal, 'signal'), \
                     patch.object(monitor.subprocess, 'run', side_effect=replies), \
                     patch.object(monitor, 'systemctl') as systemctl, \
                     patch.object(monitor.time, 'sleep', side_effect=[None] * 6 + [SystemExit(0)]), \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        monitor.main()
                self.assertEqual([call.args for call in systemctl.call_args_list], [
                    ('stop', *monitor.PLAYERS), ('restart', *active),
                    ('stop', *monitor.PLAYERS), ('restart', *active), ('stop', *monitor.PLAYERS)])

    def test_decoder_check_reports_actual_hardware_and_software_without_saving_trial(self):
        for decoder in ('drm', 'no', None):
            with self.subTest(decoder=decoder), tempfile.TemporaryDirectory() as td:
                base = Path(td)
                settings_path = base / 'settings.json'
                settings_path.write_text(json.dumps({'audio_shared': False, 'device_shared': 'auto'}))
                original = settings_path.read_bytes()
                output = io.StringIO()
                with patch.object(diagnose, 'BASE', base), \
                     patch('sys.argv', ['diagnose.py', 'shared', '--decoder', 'drm']), \
                     patch.object(player, 'movie_path', return_value=Path('/art/Shared.mp4')), \
                     patch.object(diagnose.subprocess, 'run') as stop, \
                     patch.object(diagnose.subprocess, 'Popen') as popen, \
                     patch.object(diagnose, 'property_value', side_effect=[0.2, decoder, 'hevc']), \
                     contextlib.redirect_stdout(output):
                    process = popen.return_value
                    process.poll.return_value = 1 if decoder is None else None
                    code = diagnose.main()
                    process.terminate.assert_called_once()
                    process.wait.assert_called_once_with(timeout=5)
                self.assertEqual(code, 0 if decoder == 'drm' else 1)
                self.assertIn('--hwdec=drm', popen.call_args.args[0])
                self.assertEqual(stop.call_args.args[0][-1], 'stop')
                self.assertEqual(settings_path.read_bytes(), original)
                self.assertIn('Hardware decoding is active' if decoder == 'drm' else
                              'Software decoding is active' if decoder == 'no' else
                              'could not confirm decoding', output.getvalue())


if __name__ == '__main__':
    unittest.main()
