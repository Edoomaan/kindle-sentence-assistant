import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KualInstallerTest(unittest.TestCase):
    def test_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = list((ROOT / 'installer').rglob('*.java')) + list((ROOT / 'tests/installer').rglob('*.java')) + [
                ROOT / 'src/org/kindlesentence/api/ApiConfig.java',
                ROOT / 'src/org/kindlesentence/core/ExplanationFailure.java']
            subprocess.run(['javac', '--release', '8', '-d', tmp, *map(str, sources)], check=True)
            subprocess.run(['java', '-cp', tmp, 'org.kindlesentence.install.RegistrationTest', tmp], check=True)

    def run_scenario(self, broken_start=False, unsupported=False, initial=False, prepare=False, stale_export=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'package'
            base.mkdir()
            device = root / 'device'
            device.mkdir()
            state = device / 'install-state'
            state.mkdir()
            (state / 'lock').mkdir()
            export = state / 'recovery-export'
            export.mkdir()
            target = root / 'system.jar'
            target.write_bytes(b'known registered system')
            previous = b'previous plugin'
            (device / 'explain-preview.jar').write_bytes(previous)
            (export / 'system.before.jar').write_bytes(target.read_bytes())
            (export / 'plugin.before.jar').write_bytes(previous)
            if initial:
                (device / 'explain-preview.jar').unlink()
            if not prepare and not stale_export or initial:
                for entry in export.iterdir(): entry.unlink()
                export.rmdir()
            if stale_export:
                (export / 'system.before.jar').write_bytes(b'stale export')
            (base / 'payload.jar').write_bytes(b'new plugin')
            runtime = root / 'runtime.jar'
            runtime.write_bytes(b'unchanged runtime')
            (base / 'runtime.sha256').write_text(digest(runtime) + '  ' + str(runtime) + '\n')
            worker = (ROOT / 'kual/worker.sh').read_text()
            worker = worker.replace('/mnt/us/extensions/sentence-assistant', str(device))
            worker = worker.replace('/opt/amazon/ebook/lib/ReaderSDK-impl.jar', str(target))
            worker = worker.replace('5787dad5a8d18b6ddfd71fb5ec2bddb29c6c411cbb6a7bf88a7db71b6d5459ea', digest(target))
            worker = worker.replace("root_ro() { awk '$2 == \"/\" && $4 ~ /(^|,)ro(,|$)/ {ok=1} END {exit !ok}' /proc/mounts; }", 'root_ro() { return 0; }')
            if initial:
                worker = worker.replace('a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce', digest(target))
            vm = root / 'cvm'
            vm.write_text('#!/bin/sh\nif [ "$4" = --probe ]; then echo sentence-installer-ready; exit 0; fi\ncp "$4" "$5"\nprintf patched >> "$5"\n')
            vm.chmod(0o755)
            worker = worker.replace('/usr/java/bin/cvm', str(vm))
            (state / 'java-path').write_text(str(vm))
            (base / 'worker.sh').write_text(worker)
            (base / 'SHA256SUMS').write_text('\n'.join(digest(p) + '  ' + p.name for p in base.iterdir()) + '\n')
            bindir = root / 'bin'
            bindir.mkdir()
            scripts = {
                'id': 'echo 0',
                'stat': 'echo 0:0:644',
                'df': "echo 'mock 100000 0 100000 0% /'",
                'chown': 'exit 0',
                'eips': 'exit 0',
                'sleep': 'exit 0',
                'pidof': 'exit 1',
                'lipc-set-prop': 'exit 0',
                'lipc-get-prop': 'echo com.lab126.KPPMainApp',
                'xwininfo': "echo 'ID:com.lab126.KPPMainApp IsViewable'",
                'stop': 'touch ' + str(root / 'reader-stopped'),
                'start': 'exit 1' if broken_start else 'exit 0',
                'status': 'if [ "$1" = framework ]; then echo stop/waiting; else echo start/running; fi',
                'mount': 'exit 0' if initial else 'exit 99',
                'sync': 'exit 0',
            }
            for name, body in scripts.items():
                path = bindir / name
                path.write_text('#!/bin/sh\n' + body + '\n')
                path.chmod(0o755)
            if unsupported:
                target.write_bytes(b'unknown system')
            result = subprocess.run(['sh', str(base / 'worker.sh'), 'backup' if prepare else 'install'],
                                    env={**os.environ, 'PATH': str(bindir) + ':' + os.environ['PATH']},
                                    capture_output=True, text=True)
            if prepare:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(target.read_bytes(), b'known registered system')
                self.assertFalse((root / 'reader-stopped').exists())
                self.assertEqual((export / 'system.before.jar').read_bytes(), target.read_bytes())
                self.assertEqual(len(list(state.glob('recovery-export-*'))), 0 if initial else 1)
                if initial:
                    self.assertFalse((device / 'explain-preview.jar').exists())
                else:
                    self.assertEqual((device / 'explain-preview.jar').read_bytes(), previous)
                (state / 'lock').mkdir()
                result = subprocess.run(['sh', str(base / 'worker.sh'), 'install'],
                                        env={**os.environ, 'PATH': str(bindir) + ':' + os.environ['PATH']},
                                        capture_output=True, text=True)
            if broken_start or unsupported:
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((device / 'explain-preview.jar').read_bytes(), b'new plugin' if initial else previous)
            else:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((device / 'explain-preview.jar').read_bytes(), b'new plugin')
                self.assertFalse((state / 'prepared-payload.sha256').exists())
                (state / 'lock').mkdir()
                rollback = subprocess.run(['sh', str(base / 'worker.sh'), 'restore'],
                                          env={**os.environ, 'PATH': str(bindir) + ':' + os.environ['PATH']},
                                          capture_output=True, text=True)
                self.assertEqual(rollback.returncode, 0, rollback.stdout + rollback.stderr)
                self.assertEqual((device / 'explain-preview.jar').read_bytes(), b'new plugin' if initial else previous)
            self.assertEqual(target.read_bytes(), b'unknown system' if unsupported else b'known registered system')

    def test_update_and_restore(self):
        self.run_scenario()

    def test_start_failure_restores_previous(self):
        self.run_scenario(broken_start=True)

    def test_changed_system_refused(self):
        self.run_scenario(unsupported=True)

    def test_initial_install_and_restore(self):
        self.run_scenario(initial=True)

    def test_initial_start_failure_restores_system(self):
        self.run_scenario(initial=True, broken_start=True)

    def test_optional_export_then_initial_install(self):
        self.run_scenario(initial=True, prepare=True)

    def test_optional_export_preserves_previous_export(self):
        self.run_scenario(prepare=True)

    def test_stale_export_does_not_block_install(self):
        self.run_scenario(stale_export=True)
