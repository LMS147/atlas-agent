"""Exercise host templates with fake commands and an isolated Termux home."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(shutil.which("bash") and shutil.which("flock"), "Requires Bash and flock")
class HostScriptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.source = Path(__file__).resolve().parents[1] / "termux"
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(self.bin) + os.pathsep + os.environ["PATH"]}
        self.command("pgrep", "exit 1\n")
        self.command("termux-wake-lock", "exit 0\n")
        self.command("sshd", 'touch "$HOME/sshd-started"\n')
        self.command("cloudflared", 'printf "%s\\n" "$@" > "$HOME/tunnel-arguments"\nexec sleep 60\n')

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o700)

    def test_missing_token_fails_without_starting_connector(self):
        result = subprocess.run(["bash", str(self.source / "tunnel.sh")], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(1, result.returncode)
        self.assertIn("token.txt", result.stderr)
        self.assertFalse((self.home / "tunnel-arguments").exists())

    def test_token_is_passed_by_filename_and_duplicate_launcher_exits(self):
        (self.home / "token.txt").write_text("fake-test-token")
        process = subprocess.Popen(["bash", str(self.source / "tunnel.sh")], env=self.env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            arguments_file = self.home / "tunnel-arguments"
            deadline = time.monotonic() + 5
            while not arguments_file.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(arguments_file.exists())
            arguments = arguments_file.read_text().splitlines()
            self.assertEqual(["tunnel", "--no-autoupdate", "run", "--token-file", str(self.home / "token.txt")], arguments)
            self.assertNotIn("fake-test-token", arguments_file.read_text())
            duplicate = subprocess.run(["bash", str(self.source / "tunnel.sh")], env=self.env,
                                       capture_output=True, text=True, timeout=5)
            self.assertEqual(0, duplicate.returncode)
            self.assertIn("already running", duplicate.stdout)
        finally:
            process.terminate()
            process.wait(timeout=5)
        # The trap also terminates the connector, releasing its inherited file lock.
        lock = self.home / "server/.run/cloudflared.lock"
        self.assertEqual(0, subprocess.run(["flock", "-n", str(lock), "true"]).returncode)

    def test_existing_connector_is_left_with_its_current_owner(self):
        self.command("pgrep", "exit 0\n")
        result = subprocess.run(["bash", str(self.source / "tunnel.sh")], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(1, result.returncode)
        self.assertIn("already exists", result.stderr)
        self.assertFalse((self.home / "tunnel-arguments").exists())

    def test_startup_reports_missing_tunnel_configuration_after_starting_ssh(self):
        result = subprocess.run(["bash", str(self.source / "start.sh")], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(1, result.returncode)
        self.assertTrue((self.home / "sshd-started").exists())
        self.assertIn("token.txt", result.stderr)
