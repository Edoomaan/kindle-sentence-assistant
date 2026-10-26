#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-ui', action='store_true')
    parser.add_argument('--check-native', action='store_true')
    parser.add_argument('--sdk-dir', action='append', type=Path, default=[])
    parser.add_argument('--runtime-dir', type=Path,
                        help='Directory containing Kindle rt.jar and agui.jar for API compatibility checks')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/explain-preview.jar')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='kindle-preview-build-') as temporary:
        output = Path(temporary)
        core = sorted((ROOT / 'src/org/kindlesentence/core').glob('*.java'))
        if args.check_ui:
            tests = sorted((ROOT / 'tests/java/org/kindlesentence/core').glob('*.java'))
            subprocess.run(['javac', '--release', '8', '-d', str(output),
                            *map(str, core + tests)], check=True)
            subprocess.run(['java', '-Djava.awt.headless=true', '-cp', str(output),
                            'org.kindlesentence.core.SelectionPreviewTest'], check=True)
            subprocess.run(['java', '-Djava.awt.headless=true', '-cp', str(output),
                            'org.kindlesentence.core.ExplanationControllerTest'], check=True)
            return
        jars = sorted({p.resolve() for folder in args.sdk_dir for p in folder.glob('*.jar')})
        required = {
            'com/amazon/kindle/reader/commons/providers/Provider.class',
            'com/amazon/kindle/agui/util/MultipleWidgetData.class',
            'com/amazon/ebook/booklet/reader/sdk/ReaderPlugin.class',
            'org/json/simple/parser/JSONParser.class',
        }
        available = set()
        for jar in jars:
            with zipfile.ZipFile(jar) as archive:
                available.update(archive.namelist())
        missing = sorted(required - available)
        if missing:
            parser.exit(1, 'Missing SDK classes; no artifact generated:\n' + '\n'.join(missing) + '\n')
        sources = sorted((ROOT / 'src').rglob('*.java'))
        if not args.runtime_dir:
            parser.exit(1, 'Native builds require --runtime-dir with Kindle rt.jar and agui.jar.\n')
        target = ['--release', '8']
        if args.runtime_dir:
            runtime = [args.runtime_dir / name for name in ('rt.jar', 'agui.jar')]
            if not all(path.is_file() for path in runtime):
                parser.exit(1, 'Kindle runtime requires rt.jar and agui.jar.\n')
            target = ['-source', '8', '-target', '8', '-bootclasspath', os.pathsep.join(map(str, runtime))]
        subprocess.run(['javac', *target, '-cp', os.pathsep.join(map(str, jars)),
                        '-d', str(output), *map(str, sources)], check=True)
        if args.check_native:
            classpath = os.pathsep.join([str(output), *map(str, jars)])
            tests = sorted((ROOT / 'tests/java/org/kindlesentence/nativeui').glob('*.java'))
            subprocess.run(['javac', '--release', '8', '-cp', classpath,
                            '-d', str(output), *map(str, tests)], check=True)
            subprocess.run(['java', '-Djava.awt.headless=true', '-cp', classpath,
                            'org.kindlesentence.nativeui.SelectionCardTest'], check=True)
            subprocess.run(['java', '-Djava.awt.headless=true', '-cp', classpath,
                            'org.kindlesentence.nativeui.ChatRequestTest'], check=True)
            return
        destination = args.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as artifact:
            for path in sorted(output.rglob('*.class')):
                artifact.write(path, path.relative_to(output).as_posix())
        print(f'Built {destination}; not validated on Kindle. No installer generated.')


if __name__ == '__main__':
    main()
