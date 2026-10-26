#!/usr/bin/env python3
import argparse
import importlib.util
from pathlib import Path
import shutil
import tarfile

spec = importlib.util.spec_from_file_location('candidate', Path(__file__).with_name('prepare_candidate.py'))
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def package(original, plugin, output, previous=None):
    output = output.resolve()
    repo = Path(__file__).resolve().parent.parent
    if output == repo or repo in output.parents:
        raise ValueError('Use a private output directory outside the repository.')
    archive = output.with_name(output.name + '.tar.gz')
    if output.exists() or archive.exists():
        raise ValueError('Output directory or archive already exists.')
    if previous is not None and not previous.is_file():
        raise ValueError('Previous plugin must be a private copy from the target device.')
    candidate.prepare(original, plugin, output)
    previous_hash = 'absent'
    if previous is not None:
        shutil.copyfile(previous, output / 'previous-plugin.jar')
        previous_hash = candidate.digest(output / 'previous-plugin.jar')
    replacements = {
        '@ORIGINAL@': candidate.ORIGINAL_HASH,
        '@CANDIDATE@': candidate.digest(output / 'ReaderSDK-impl.candidate.jar'),
        '@PLUGIN@': candidate.digest(output / 'explain-preview.jar'),
        '@PREVIOUS@': previous_hash,
    }
    for template, filename in [('install-package.sh', 'install.sh'),
                               ('rollback-package.sh', 'rollback.sh')]:
        script = Path(__file__).with_name(template).read_text()
        for name, value in replacements.items():
            script = script.replace(name, value)
        (output / filename).write_text(script)
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(output, arcname='sentence-assistant-package')
    print(f'Private installer package: {archive}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare a private, device-specific SSH installer package.')
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--plugin', required=True, type=Path)
    parser.add_argument('--previous-plugin', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    package(args.original, args.plugin, args.output, args.previous_plugin)
