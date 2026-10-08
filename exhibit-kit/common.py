"""Small, dependency-free helpers for the exhibition setup."""
import re
import xml.etree.ElementTree as ET

APP_IDS = ('ddw-exhibit-a', 'ddw-exhibit-b', 'ddw-exhibit-shared')


def parse_outputs(text):
    outputs = []
    current = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            current = {'name': line.split()[0], 'enabled': False}
            outputs.append(current)
        elif current and re.match(r'\s+Enabled:\s+yes\s*$', line):
            current['enabled'] = True
    return outputs


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
