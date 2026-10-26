#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(plugin, runtime, output):
    with zipfile.ZipFile(plugin) as jar:
        names = jar.namelist()
        if (jar.testzip() or len(names) != len(set(names))
                or 'org/kindlesentence/nativeui/ExplainPlugin.class' not in names
                or not all(n.startswith('org/kindlesentence/') and n.endswith('.class') for n in names)):
            raise ValueError('Unexpected plugin archive contents')
    libs = [runtime / name for name in ('rt.jar', 'agui.jar')]
    if not all(p.is_file() for p in libs):
        raise ValueError('Device runtime copies required')
    with tempfile.TemporaryDirectory(prefix='kindle-kual-package-') as temporary:
        temp = Path(temporary)
        classes = temp / 'classes'
        classes.mkdir()
        sources = sorted((ROOT / 'installer/src').rglob('*.java')) + [
            ROOT / 'src/org/kindlesentence/api/ApiConfig.java',
            ROOT / 'src/org/kindlesentence/core/ExplanationFailure.java']
        subprocess.run(['javac', '-source', '8', '-target', '8', '-bootclasspath',
                        ':'.join(map(str, libs)), '-d', str(classes), *map(str, sources)], check=True)
        extension = temp / 'extensions/sentence-assistant-installer'
        extension.mkdir(parents=True)
        for name in ('config.xml', 'menu.json', 'launch.sh', 'worker.sh', 'settings.sh', 'setup.html', 'setup.js'):
            source = ROOT / 'kual' / name
            if source.is_symlink() or not source.is_file():
                raise ValueError('Unexpected package source')
            shutil.copyfile(source, extension / name)
        for script in extension.glob('*.sh'):
            script.chmod(0o755)
            subprocess.run(['sh', '-n', str(script)], check=True)
        shutil.copyfile(plugin, extension / 'payload.jar')
        with zipfile.ZipFile(extension / 'registration.jar', 'w', zipfile.ZIP_DEFLATED) as jar:
            for path in sorted(classes.rglob('*.class')):
                jar.write(path, path.relative_to(classes).as_posix())
        (extension / 'runtime.sha256').write_text(''.join(
            hashlib.sha256(p.read_bytes()).hexdigest() + '  /usr/java/lib/' + p.name + '\n'
            for p in libs))
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name
                  for p in sorted(extension.iterdir()) if p.is_file()]
        (extension / 'SHA256SUMS').write_text('\n'.join(hashes) + '\n')
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(extension.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(temp).as_posix())
    print(f'KUAL test package: {output}; no Amazon libraries or credentials bundled.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--runtime-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/sentence-assistant-kual.zip')
    args = parser.parse_args()
    package(args.plugin, args.runtime_dir, args.output)
