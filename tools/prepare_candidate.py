#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

ORIGINAL_HASH = 'a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce'
PLUGIN_CLASS = 'org.kindlesentence.nativeui.ExplainPlugin'
PLUGIN_PATH = '/mnt/us/extensions/sentence-assistant/explain-preview.jar'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(original, plugin, output):
    if digest(original) != ORIGINAL_HASH:
        raise ValueError('Original firmware JAR hash mismatch')
    with zipfile.ZipFile(plugin) as z:
        if z.testzip() is not None:
            raise ValueError('Plugin CRC failure')
        names = z.namelist()
        if PLUGIN_CLASS.replace('.', '/') + '.class' not in names:
            raise ValueError('Plugin entry class missing')
        if not all(n.startswith('org/kindlesentence/') and n.endswith('.class') for n in names):
            raise ValueError('Unexpected plugin contents')
    with zipfile.ZipFile(original) as src:
        names = src.namelist()
        if len(names) != len(set(names)) or src.testzip() is not None:
            raise ValueError('Duplicate entries or corrupt original')
        if any(n.upper().endswith(('.SF', '.RSA', '.DSA', '.EC')) for n in names):
            raise ValueError('Signed archive requires separate review')
        old = src.read('reader_plugins.xml')
        root = ET.fromstring(old)
        if root.tag != 'Plugins' or old.count(b'</Plugins>') != 1:
            raise ValueError('Unexpected XML structure')
        if any(e.get('class') == PLUGIN_CLASS for e in root):
            raise ValueError('Plugin already registered')
        entry = f'    <Plugin class="{PLUGIN_CLASS}" jar="{PLUGIN_PATH}" />\n'
        new = old.replace(b'</Plugins>', entry.encode() + b'</Plugins>')
        parsed = ET.fromstring(new)
        if len(parsed) != len(root) + 1 or parsed[-1].attrib != {'class': PLUGIN_CLASS, 'jar': PLUGIN_PATH}:
            raise ValueError('Registration verification failed')
        output.mkdir(parents=True, exist_ok=False)
        candidate = output / 'ReaderSDK-impl.candidate.jar'
        with zipfile.ZipFile(candidate, 'w') as dst:
            dst.comment = src.comment
            for info in src.infolist():
                copied = copy.copy(info)
                dst.writestr(copied, new if info.filename == 'reader_plugins.xml' else src.read(info))
                copied.external_attr = info.external_attr
        with zipfile.ZipFile(candidate) as dst:
            if dst.testzip() is not None or dst.namelist() != names:
                raise ValueError('Candidate archive verification failed')
            changed = [n for n in names if src.read(n) != dst.read(n)]
            if changed != ['reader_plugins.xml']:
                raise ValueError(f'Unexpected changed entries: {changed}')
    shutil.copyfile(original, output / 'ReaderSDK-impl.original.jar')
    shutil.copyfile(plugin, output / 'explain-preview.jar')
    rollback = Path(__file__).with_name('rollback-preview.sh').read_text()
    rollback = rollback.replace('@CANDIDATE_HASH@', digest(candidate))
    (output / 'rollback-preview.sh').write_text(rollback)
    manifest = {
        'status': 'LOCAL_CANDIDATE_NOT_DEPLOYED',
        'firmware': '5.17.1.0.4', 'build': '4351960007',
        'system_target': '/opt/amazon/ebook/lib/ReaderSDK-impl.jar',
        'original_mode': '0644', 'original_uid': 0, 'original_gid': 0,
        'metadata_source': 'Read-only device SSH stat and sha256sum, 2026-10-23',
        'plugin_target': PLUGIN_PATH, 'changed_entries': changed,
        'hashes': {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
        'recovery_access_verified': False,
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Prepared and verified local candidate: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.original, args.plugin, args.output)
