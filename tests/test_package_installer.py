import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import tarfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'tools/package-installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PackageTest(unittest.TestCase):
    def test_package_and_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'original.jar'
            plugin = root / 'plugin.jar'
            with zipfile.ZipFile(original, 'w') as z:
                z.writestr('reader_plugins.xml', '<Plugins>\n</Plugins>')
                z.writestr('unchanged', 'preserve me')
            with zipfile.ZipFile(plugin, 'w') as z:
                z.writestr('org/kindlesentence/nativeui/ExplainPlugin.class', b'test fixture')
            with self.assertRaises(ValueError):
                installer.package(original, plugin, root / 'rejected')
            self.assertFalse((root / 'rejected').exists())
            with patch.object(installer.candidate, 'ORIGINAL_HASH', installer.candidate.digest(original)):
                installer.package(original, plugin, root / 'package', plugin)
                with self.assertRaises(ValueError):
                    installer.package(original, plugin, root / 'package', plugin)
            for script in ('install.sh', 'rollback.sh'):
                path = root / 'package' / script
                self.assertNotIn('@', path.read_text())
                subprocess.run(['sh', '-n', str(path)], check=True)
            with tarfile.open(root / 'package.tar.gz') as tar:
                names = tar.getnames()
                self.assertIn('sentence-assistant-package/previous-plugin.jar', names)
                self.assertFalse(any('header' in name for name in names))
            with zipfile.ZipFile(root / 'package/ReaderSDK-impl.candidate.jar') as z:
                self.assertEqual(z.read('unchanged'), b'preserve me')

    def test_public_output_rejected(self):
        with self.assertRaises(ValueError):
            installer.package(Path('unused'), Path('unused'), ROOT / 'private-package')
