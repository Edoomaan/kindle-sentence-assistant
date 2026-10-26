import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("setup_api", Path(__file__).parents[1] / "tools/setup-api.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "settings"

    def run_script(self, provider, data, **options):
        command = setup.write_command(provider, **options)
        command = command.replace(setup.DIRECTORY, str(self.target))
        command = command.replace("$(id -u framework)", str(os.getuid()))
        command = command.replace("$(id -g framework)", str(os.getgid()))
        return subprocess.run(["sh", "-c", command], input=data, capture_output=True)

    def test_key_rotation_is_isolated(self):
        for provider in setup.PROVIDERS:
            data = setup.header_bytes(provider, "dummy-key")
            self.assertEqual(self.run_script(provider, data).returncode, 0)
            path = self.target / (provider + "-header")
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o700)
        original = (self.target / "evren-header").read_bytes()
        self.assertNotEqual(self.run_script("evren", b"replacement").returncode, 0)
        self.assertNotEqual(self.run_script("evren", b"", replace=True).returncode, 0)
        self.assertEqual((self.target / "evren-header").read_bytes(), original)
        self.assertEqual(self.run_script("evren", b"replacement", replace=True).returncode, 0)
        self.assertEqual((self.target / "openai-header").read_bytes(), setup.header_bytes("openai", "dummy-key"))
        self.assertFalse(any(p.name.startswith(".") for p in self.target.iterdir()))

    def test_activation_requires_own_key_and_preserves_previous_settings(self):
        config = b"provider=evren\nmodel=qwen3.8-flash-next\n"
        self.assertNotEqual(self.run_script("evren", config, activate=True).returncode, 0)
        self.assertEqual(self.run_script("evren", b"dummy").returncode, 0)
        self.assertEqual(self.run_script("evren", config, activate=True).returncode, 0)
        self.assertNotEqual(self.run_script("openai", b"provider=openai\nmodel=test\n", activate=True).returncode, 0)
        self.assertEqual((self.target / "api.properties").read_bytes(), config)

    def test_symlinks_are_rejected(self):
        self.target.mkdir(mode=0o700)
        victim = Path(self.temporary.name) / "victim"
        victim.write_bytes(b"unchanged")
        (self.target / "evren-header").symlink_to(victim)
        self.assertNotEqual(self.run_script("evren", b"new", replace=True).returncode, 0)
        self.assertEqual(victim.read_bytes(), b"unchanged")

    def test_headers_and_requests(self):
        self.assertEqual(setup.header_bytes("evren", "dummy"), b"X-API-Key: dummy\n")
        for provider in ("openai", "deepseek"):
            self.assertEqual(setup.header_bytes(provider, "dummy"), b"Authorization: Bearer dummy\n")
        for key in ("", "a\nb", "a\rb", "a b", "ş"):
            with self.assertRaises(ValueError):
                setup.header_bytes("evren", key)
        with self.assertRaises(ValueError):
            setup.validate_model("test\nprovider=openai")
        with self.assertRaises(ValueError):
            setup.write_command("../other")
        self.assertIn("max_completion_tokens", setup.request_body("openai", "test"))
        self.assertEqual(setup.request_body("deepseek", "test")["thinking"], {"type": "disabled"})
        self.assertEqual(setup.request_body("evren", "test")["reasoning_effort"], "low")
        for provider in setup.PROVIDERS:
            result = subprocess.run(["sh", "-n"], input=setup.test_command(provider).encode(), capture_output=True)
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
