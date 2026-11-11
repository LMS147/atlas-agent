"""Staging checks plus real runit crash/restart/health tests on Linux CI."""
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from backend.server.termux_service import install_service,control
from unittest.mock import patch
from backend.server.healthcheck import probe


def matching_proc():
    try:
        return int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('Pid:')))==os.getpid()
    except (OSError,StopIteration):return False

class InstallerTests(unittest.TestCase):
    def test_generated_service_is_quoted_idempotent_and_does_not_embed_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/"repo with spaces"; root.mkdir()
            prefix=Path(temporary)/"prefix"; binary=prefix/"bin"; binary.mkdir(parents=True)
            for name in ('sh','sv','svlogd','runsvdir'):(binary/name).symlink_to('/bin/sh')
            boot=Path(temporary)/'boot'; boot.mkdir(); (boot/'start-all').write_text('existing ssh and tunnel')
            with patch.dict(os.environ,{'GROQ_API_KEY':'must-not-copy-key','ATLAS_API_TOKEN':'must-not-copy-token'}):
                service=install_service(root,prefix,sys.executable,boot)
                self.assertTrue((service/'down').exists())
                self.assertIn("'"+str(root)+"'",(service/'run').read_text())
                (service/'down').unlink()
                install_service(root,prefix,sys.executable,boot)
            self.assertFalse((service/'down').exists())
            self.assertEqual('existing ssh and tunnel',(boot/'start-all').read_text())
            self.assertIn('termux-wake-lock',(boot/'50-atlas-api').read_text())
            self.assertIn('service-daemon',(boot/'50-atlas-api').read_text())
            for file in [service/'run',service/'finish',service/'log'/'run',service/'atlas-managed.json',boot/'50-atlas-api']:
                text=file.read_text()
                self.assertNotIn('must-not-copy',text)
                self.assertEqual(0,subprocess.run(['sh','-n',str(file)],capture_output=True).returncode) if file.name!='atlas-managed.json' else None
            self.assertEqual('s1048576\nn5\n',(prefix/'var/log/sv/atlas-api/config').read_text())
            self.assertEqual(0o600,(service/'atlas-managed.json').stat().st_mode & 0o777)

    def test_unmanaged_service_and_foreign_checkout_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'repo'; root.mkdir()
            prefix=Path(temporary)/'prefix'; (prefix/'bin').mkdir(parents=True)
            for name in ('sh','sv','svlogd','runsvdir'):(prefix/'bin'/name).symlink_to('/bin/sh')
            service=prefix/'var/service/atlas-api'; service.mkdir(parents=True)
            (service/'run').write_text('keep me')
            with self.assertRaises(RuntimeError):install_service(root,prefix,sys.executable)
            self.assertEqual('keep me',(service/'run').read_text())
            (service/'atlas-managed.json').write_text(json.dumps({'root':'/another/repo'}))
            with self.assertRaises(RuntimeError):install_service(root,prefix,sys.executable)

@unittest.skipUnless(matching_proc() and all(shutil.which(x) for x in ('runsvdir','sv','svlogd')), 'Requires real runit and matching Linux /proc namespace')
class RunitTests(unittest.TestCase):
    def test_supervised_api_restarts_without_losing_history_and_marks_interrupted_requests(self):
        repo=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); prefix=root/'prefix'; (prefix/'bin').mkdir(parents=True)
            for name in ('sh','sv','svlogd','runsvdir'):
                (prefix/'bin'/name).symlink_to(shutil.which(name))
            service=install_service(repo,prefix,sys.executable)
            with socket.socket() as socket_:
                socket_.bind(('127.0.0.1',0)); port=socket_.getsockname()[1]
            env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':str(repo),'PREFIX':str(prefix),
                 'ATLAS_API_TOKEN':'test-supervised-'+('x'*32),'GROQ_API_KEY':'test-only','GH_REPO':'',
                 'ATLAS_PORT':str(port),'ATLAS_HOST':'127.0.0.1','DATA_DIR':str(root/'data')}
            supervisor=subprocess.Popen([str(prefix/'bin/runsvdir'),str(prefix/'var/service')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            def command(action):
                return subprocess.run([sys.executable,'-m','backend.server.termux_service',action],cwd=repo,env=env,capture_output=True,text=True,timeout=35)
            def wait_healthy(previous=None):
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    with patch.dict(os.environ,env,clear=True):healthy,payload=probe()
                    if healthy and (previous is None or payload['pid']!=previous):return payload['pid']
                    time.sleep(.2)
                self.fail('Supervised API did not become healthy')
            try:
                enabled=command('enable'); self.assertEqual(0,enabled.returncode,enabled.stdout+enabled.stderr)
                first=wait_healthy()
                self.assertEqual(0,command('health').returncode)
                dbpath=root/'data/atlas.sqlite3'
                from backend.atlas.app.repositories.sessions import SessionRepository
                database=SessionRepository(dbpath)
                chat=database.create_conversation('owner','Survives a crash')['id']
                database.chat('owner',chat,'saved-request','Saved message',lambda h,t:('Saved reply',[{'role':'user','content':t},{'role':'assistant','content':'Saved reply'}]))
                with sqlite3.connect(dbpath) as db:
                    db.execute("INSERT INTO requests(owner,conversation,id,message,status,reply,created_at) VALUES ('owner',?,'interrupted-request','Pending','pending',NULL,1)",(chat,))
                os.kill(first,signal.SIGKILL)
                second=wait_healthy(first)
                self.assertNotEqual(first,second)
                with sqlite3.connect(dbpath) as db:
                    self.assertEqual('interrupted',db.execute("SELECT status FROM requests WHERE id='interrupted-request'").fetchone()[0])
                    self.assertEqual(2,db.execute('SELECT COUNT(*) FROM transcript').fetchone()[0])
                self.assertEqual(0,command('restart').returncode)
                self.assertNotEqual(second,wait_healthy(second))
                self.assertEqual(0,command('disable').returncode)
                self.assertTrue((service/'down').exists())
                self.assertNotEqual(0,command('health').returncode)
            finally:
                command('disable')
                subprocess.run([str(prefix/'bin/sv'),'-w','5','down',str(service/'log')],env=env,capture_output=True)
                subprocess.run([str(prefix/'bin/sv'),'exit',str(service)],env=env,capture_output=True)
                supervisor.terminate(); supervisor.wait(timeout=10)
