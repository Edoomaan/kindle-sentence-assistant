import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class USBSettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiled = tempfile.TemporaryDirectory()
        sources = [ROOT / 'installer/src/org/kindlesentence/install/ImportSettings.java',
                   ROOT / 'src/org/kindlesentence/api/ApiConfig.java',
                   ROOT / 'src/org/kindlesentence/core/ExplanationFailure.java']
        subprocess.run(['javac', '--release', '8', '-d', cls.compiled.name, *map(str, sources)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.compiled.cleanup()

    def test_browser_roundtrip(self):
        instruction = 'Use simple words.\nExplain “déjà vu” 😀 = # ! \\ briefly.'
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            values = ['openai', 'account/model-1', 'test-key-only', instruction]
            script = 'const {encodeSettings}=require(process.argv[1]); process.stdout.write(encodeSettings(...JSON.parse(process.argv[2])));'
            result = subprocess.run(['node', '-e', script, str(ROOT / 'kual/setup.js'), json.dumps(values)], capture_output=True, check=True)
            source = stage / 'input'
            source.write_bytes(result.stdout)
            subprocess.run(['java', '-cp', self.compiled.name, 'org.kindlesentence.install.ImportSettings', str(source), str(stage)], check=True)
            self.assertEqual((stage / 'header').read_text(), 'Authorization: Bearer test-key-only\n')
            self.assertNotIn('test-key-only', (stage / 'api.properties').read_text())
            # Re-import the Java-produced settings to validate escaped properties without a new key.
            next_stage = stage / 'next'
            next_stage.mkdir()
            subprocess.run(['java', '-cp', self.compiled.name, 'org.kindlesentence.install.ImportSettings', str(stage / 'api.properties'), str(next_stage)], check=True)
            self.assertFalse((next_stage / 'header').exists())
            def values(path):
                return sorted(line for line in path.read_text().splitlines() if line and not line.startswith('#'))
            self.assertEqual(values(stage / 'api.properties'), values(next_stage / 'api.properties'))

    def run_import(self, content, existing=True, fail_publish=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        base = root / 'package'; base.mkdir()
        target = root / 'private'; target.mkdir(mode=0o700)
        state = root / 'state'; state.mkdir(); (state / 'lock').mkdir()
        if existing:
            (target / 'openai-header').write_text('Authorization: Bearer previous-test-key\n')
        (target / 'evren-header').write_text('X-API-Key: separate-test-key\n')
        (target / 'api.properties').write_text('provider=evren\nmodel=qwen3.8-flash-next\n')
        if 'instruction=' not in content:
            content += 'instruction=Explain in Turkish.\n'
        (base / 'setup.properties').write_text(content)
        bindir = root / 'bin'; bindir.mkdir()
        vm = root / 'cvm'
        vm.write_text('#!/bin/sh\nshift 2\ntest -f "$3/ownership-ready" || exit 1\nrm "$3/ownership-ready"\nexec java -cp ' + self.compiled.name + ' "$@"\n')
        vm.chmod(0o755)
        runtime = root / 'runtime'; runtime.write_bytes(b'fixture')
        (base / 'runtime.sha256').write_text(hashlib.sha256(runtime.read_bytes()).hexdigest() + '  ' + str(runtime) + '\n')
        worker = (ROOT / 'kual/settings.sh').read_text().replace('/var/local/sentence-assistant', str(target)).replace('/mnt/us/extensions/sentence-assistant/install-state', str(state)).replace('/usr/java/bin/cvm', str(vm))
        (base / 'settings.sh').write_text(worker)
        (base / 'SHA256SUMS').write_text(hashlib.sha256(worker.encode()).hexdigest() + '  settings.sh\n')
        scripts = {'id': 'if [ "$#" = 1 ]; then echo 0; elif [ "$1" = -u ]; then echo ' + str(os.getuid()) + '; else echo ' + str(os.getgid()) + '; fi', 'chown': 'if [ "$#" = 3 ] && [ "$3" = "$2/input" ]; then test -f "$3" || exit 1; touch "$2/ownership-ready"; fi', 'eips': 'exit 0', 'sync': 'exit 0'}
        if fail_publish:
            scripts['mv'] = 'case "$2" in */private/api.properties) exit 1 ;; esac\nexec /usr/bin/mv "$@"'
        for name, body in scripts.items():
            path = bindir / name; path.write_text('#!/bin/sh\n' + body + '\n');path.chmod(0o755)
        result = subprocess.run(['sh', str(base / 'settings.sh'), 'import'], env={**os.environ, 'PATH': str(bindir) + ':' + os.environ['PATH']}, capture_output=True, text=True)
        self.assertNotIn('test-key', result.stdout + result.stderr)
        self.assertEqual((target / 'evren-header').read_text(), 'X-API-Key: separate-test-key\n')
        self.assertFalse((base / 'setup.properties').exists())
        self.assertFalse((state / 'lock').exists())
        self.assertFalse((target / '.setup-lock').exists())
        self.assertFalse(list(target.glob('.import.*')))
        return target, result

    def test_import_rotates_only_selected_provider(self):
        target, result = self.run_import('provider=openai\nmodel=test-model\napi_key=new-test-key\ninstruction=Use short words.\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'openai-header').read_text(), 'Authorization: Bearer new-test-key\n')
        self.assertIn('instruction=Use short words.', (target / 'api.properties').read_text())
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        for name in ['openai-header', 'api.properties']:
            self.assertEqual((target / name).stat().st_mode & 0o777, 0o600)

    def test_keep_existing_key(self):
        target, result = self.run_import('provider=openai\nmodel=test-model\napi_key=\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'openai-header').read_text(), 'Authorization: Bearer previous-test-key\n')

    def test_missing_key_and_invalid_input_preserve_settings(self):
        for content in ['provider=openai\nmodel=test-model\n', 'provider=unknown\nmodel=test-model\napi_key=new-test-key\n', 'provider=openai\nmodel=test-model\napi_key=bad\\nheader\n', 'provider=openai\nmodel=test-model\nendpoint=https://example.com\n']:
            with self.subTest(content=content):
                target, result = self.run_import(content, existing=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((target / 'api.properties').read_text(), 'provider=evren\nmodel=qwen3.8-flash-next\n')
                self.assertFalse((target / 'openai-header').exists())

    def test_publish_failure_restores_key(self):
        for existing in (True, False):
            with self.subTest(existing=existing):
                target, result = self.run_import('provider=openai\nmodel=test-model\napi_key=new-test-key\n', existing=existing, fail_publish=True)
                self.assertNotEqual(result.returncode, 0)
                if existing:
                    self.assertEqual((target / 'openai-header').read_text(), 'Authorization: Bearer previous-test-key\n')
                else:
                    self.assertFalse((target / 'openai-header').exists())
                self.assertEqual((target / 'api.properties').read_text(), 'provider=evren\nmodel=qwen3.8-flash-next\n')
