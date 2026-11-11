"""Readiness and the actual Render entrypoint, with no inference or real secrets."""
import http.client
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.atlas.app.config import Settings
from backend.atlas.app.main import create_app

class RenderTests(unittest.TestCase):
    def test_platform_readiness_has_no_workspace_or_configuration_data(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'GH_REPO':''}):
            app=create_app(Settings(api_token='test-render-token-'+'x'*32,groq_api_key='fake',data_dir=Path(directory)))
            self.assertFalse(app.state.ready)
            with TestClient(app) as client:
                response=client.get('/healthz')
                self.assertEqual(204,response.status_code)
                self.assertEqual(b'',response.content)
                self.assertEqual(401,client.get('/api/v1/health').status_code)
                self.assertEqual(401,client.get('/api/v1/files').status_code)
            self.assertFalse(app.state.ready)

    def test_render_script_obeys_platform_port_and_overrides_loopback_defaults(self):
        repo=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0))
                port=sock.getsockname()[1]
            env={'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''),
                 'PYTHONPATH':str(repo),'PORT':str(port),'ATLAS_HOST':'invalid-render-bind',
                 'ATLAS_PORT':'1','DATA_DIR':directory,'GH_REPO':'',
                 'ATLAS_API_TOKEN':'test-render-token-'+'x'*32,'GROQ_API_KEY':'fake'}
            process=subprocess.Popen(['bash','deployment/render/start.sh'],cwd=repo,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=1)
                    try:
                        connection.request('GET','/healthz')
                        response=connection.getresponse()
                        self.assertEqual(204,response.status)
                        self.assertEqual(b'',response.read())
                        break
                    except OSError:
                        if process.poll() is not None:
                            self.fail('Render launcher exited during startup')
                        time.sleep(0.1)
                    finally:
                        connection.close()
                else:
                    self.fail('Render startup timed out')
                self.assertTrue((Path(directory)/'atlas.sqlite3').is_file())
            finally:
                process.terminate()
                process.wait(timeout=10)
