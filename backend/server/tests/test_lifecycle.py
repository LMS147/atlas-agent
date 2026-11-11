"""Run the real API launcher and Termux helpers against loopback, without Groq calls."""
import os
import http.client
import json
import time
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

def proc_pids_match():
    try:
        actual = next(line.split()[1] for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("Pid:"))
        return int(actual) == os.getpid()
    except (OSError, StopIteration):
        return False

class LifecycleTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux") and proc_pids_match(), "Requires Linux/Termux with a matching /proc PID namespace")
    def test_start_duplicate_health_and_stop(self):
        repo = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "deployment" / "termux"
            shutil.copytree(repo / "deployment" / "termux", scripts)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(repo), "ATLAS_PYTHON": sys.executable,
                   "ATLAS_API_TOKEN": "test-lifecycle-token-" + "x" * 32, "GROQ_API_KEY": "test-only",
                   "DATA_DIR": str(root / "data"), "ATLAS_HOST": "127.0.0.1", "ATLAS_PORT": str(port), "GH_REPO": ""}
            def run(name):
                return subprocess.run(["bash", str(scripts / name)], cwd=root, env=env, capture_output=True, text=True, timeout=35)
            try:
                first = run("start.sh")
                self.assertEqual(0, first.returncode, first.stdout + first.stderr + (root / ".run" / "api.log").read_text())
                pid = (root / ".run" / "api.pid").read_text()
                self.assertEqual(0, run("healthcheck.sh").returncode)
                self.assertEqual(0, run("start.sh").returncode)
                self.assertEqual(pid, (root / ".run" / "api.pid").read_text())
                self.assertEqual(0, run("stop.sh").returncode)
                self.assertNotEqual(0, run("healthcheck.sh").returncode)
                self.assertFalse((root / ".run" / "api.pid").exists())
            finally:
                # If a wrapper failed, still clean up this test's own explicitly recorded child.
                pid_file = root / ".run" / "api.pid"
                recorded = int(pid_file.read_text()) if pid_file.exists() else None
                run("stop.sh")
                if recorded:
                    try:
                        os.kill(recorded, 15)
                    except ProcessLookupError:
                        pass

    def test_real_uvicorn_startup_and_authenticated_http(self):
        repo = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as temporary:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            token = "test-live-api-" + "x" * 32
            env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(repo),
                   "ATLAS_API_TOKEN": token, "GROQ_API_KEY": "test-only", "GH_REPO": "",
                   "DATA_DIR": temporary, "ATLAS_HOST": "127.0.0.1", "ATLAS_PORT": str(port)}
            process = subprocess.Popen([sys.executable, "-m", "backend.atlas.app"], cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            def health(headers):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                try:
                    connection.request("GET", "/api/v1/health", headers=headers)
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()
            try:
                for _ in range(50):
                    try:
                        status, body = health({"Authorization": f"Bearer {token}"})
                        break
                    except OSError:
                        if process.poll() is not None:
                            self.fail("API launcher exited during startup")
                        time.sleep(0.1)
                else:
                    self.fail("API startup timed out")
                self.assertEqual(200, status)
                self.assertEqual("ok", body["status"])
                self.assertEqual(401, health({})[0])
            finally:
                process.terminate()
                process.wait(timeout=10)
