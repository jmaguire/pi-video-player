"""Small, dependency-free helpers for the exhibition setup."""
import re
from pathlib import Path
import xml.etree.ElementTree as ET

APP_IDS = ('ddw-exhibit-a', 'ddw-exhibit-b', 'ddw-exhibit-shared')


def parse_outputs(text):
    outputs = []
    current = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            current = {'name': line.split()[0], 'enabled': False, 'layout': []}
            outputs.append(current)
        elif current and re.match(r'\s+Enabled:\s+yes\s*$', line):
            current['enabled'] = True
        elif current and (re.search(r'\([^)]*\bcurrent\b[^)]*\)', line) or
                          re.match(r'\s+(Position|Transform|Scale):', line)):
            current['layout'].append(line.strip())
    return outputs


FOLDERS = {'a': 'A', 'b': 'B', 'shared': 'Shared'}
LEGACY_MOVIES = {'a': 'video-a.mp4', 'b': 'video-b.mp4', 'shared': 'shared.mp4'}


def movie_path(base, screen):
    """Accept an artist's filename, but never guess between two artworks."""
    folder = base / FOLDERS[screen]
    movies = sorted(p for p in folder.glob('*') if p.is_file() and
                    not p.name.startswith('.') and p.suffix.lower() == '.mp4')
    if len(movies) > 1:
        raise ValueError(f'Home > exhibit > {folder.name} contains more than one MP4. '
                         'Keep only the movie for this screen, then click Start Exhibit.')
    path = movies[0] if movies else base / LEGACY_MOVIES[screen]
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'Put one non-empty MP4 in Home > exhibit > {folder.name}, '
                         'then click Start Exhibit. The filename can stay as it is.')
    return path


def require_writable_setup():
    """Do not report temporary overlay changes as a successful installation."""
    mounts = Path('/proc/mounts')
    if mounts.exists() and any(len(parts) > 3 and (
            parts[1:3] == ['/', 'overlay'] or
            (parts[1] == '/boot/firmware' and 'ro' in parts[3].split(',')))
            for parts in map(str.split, mounts.read_text().splitlines())):
        raise ValueError('Protected exhibition mode is on. Turn off Use Overlay and '
                         'boot-partition protection in Control Centre, reboot, then make changes. '
                         'See the helper pages in the manual.')


def patch_rules(xml_bytes, output_a, output_b=None):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(xml_bytes, parser=parser)
    if root.tag.split('}')[-1] != 'labwc_config':
        raise ValueError('The labwc configuration has an unexpected root element.')
    ns = root.tag.rsplit('}', 1)[0] + '}' if '}' in root.tag else ''
    if ns:
        ET.register_namespace('', ns[1:-1])
    rules = root.find(ns + 'windowRules')
    if rules is None:
        rules = ET.SubElement(root, ns + 'windowRules')
    for rule in list(rules):
        if rule.get('identifier') in APP_IDS:
            rules.remove(rule)
    assignments = [('ddw-exhibit-a', output_a), ('ddw-exhibit-shared', output_a)]
    if output_b:
        assignments.append(('ddw-exhibit-b', output_b))
    for app_id, output in assignments:
        rule = ET.SubElement(rules, ns + 'windowRule', {'identifier': app_id})
        ET.SubElement(rule, ns + 'action', {'name': 'MoveToOutput', 'output': output})
        ET.SubElement(rule, ns + 'action', {'name': 'ToggleFullscreen'})
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)
