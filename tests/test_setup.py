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

    def test_player_uses_native_wayland_and_waits_for_window_rule_fullscreen(self):
        class ExecIntercept(Exception):
            pass
        recorded = []
        def intercept(binary, args):
            recorded.extend(args)
            raise ExecIntercept()
        config = {'audio_a': False, 'device_a': 'auto'}
        with patch.object(Path, 'read_text', return_value=json.dumps(config)), \
             patch('sys.argv', ['player.py', 'a']), patch('os.execv', side_effect=intercept):
            with self.assertRaises(ExecIntercept):
                runpy.run_path(str(KIT / 'player.py'), run_name='__main__')
        self.assertIn('--gpu-context=wayland', recorded)
        self.assertIn('--wayland-app-id=ddw-exhibit-a', recorded)
        self.assertIn('--fullscreen=no', recorded)
        self.assertIn('--audio=no', recorded)
        self.assertIn('--loop-file=inf', recorded)


if __name__ == '__main__':
    unittest.main()
