"""Run the Atlas API launcher against loopback with disposable data."""
import os
import http.client
import json
import time
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

class LifecycleTests(unittest.TestCase):
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
