"""Real HTTP streaming and disconnect durability (fake inference)."""
import http.client
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import uvicorn
from backend.atlas.app.config import Settings
from backend.atlas.app.main import create_app

class DisconnectTests(unittest.TestCase):
    def test_progress_is_live_and_disconnect_does_not_cancel_persistence(self):
        release=threading.Event();calls=[];token='fake-stream-token-'+'x'*32
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
        def runner(history,text,emit):
            calls.append(text);emit('replying','Live prefix')
            if not release.wait(5):raise TimeoutError()
            return 'Saved final',[{'role':'user','content':text},{'role':'assistant','content':'Saved final'}]
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'GH_REPO':''},clear=True):
            app=create_app(Settings(token,'fake',Path(root)),streaming_runner=runner)
            sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
            thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]});thread.start()
            def call(method,path,body=None):
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                try:
                    c.request(method,path,json.dumps(body) if body is not None else None,headers)
                    return json.loads(c.getresponse().read())
                finally:c.close()
            connection=None
            try:
                for _ in range(100):
                    if server.started:break
                    time.sleep(.02)
                self.assertTrue(server.started)
                cid=call('POST','/api/v1/conversations',{})['id'];rid=str(uuid4())
                connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                connection.request('POST','/api/v1/chat/stream',json.dumps(dict(conversation_id=cid,request_id=rid,message='Hello',require_existing=True)),headers)
                response=connection.getresponse();self.assertEqual(200,response.status)
                while True:
                    line=response.readline();self.assertTrue(line)
                    if b'Live prefix' in line:break
                self.assertFalse(release.is_set())
                response.close();connection.close();release.set()
                for _ in range(100):
                    status=call('GET',f'/api/v1/conversations/{cid}/requests/{rid}')
                    if status['status']=='done':break
                    time.sleep(.02)
                self.assertEqual('Saved final',status['reply']);self.assertEqual(['Hello'],calls)
            finally:
                release.set()
                if connection:connection.close()
                server.should_exit=True;thread.join(10);sock.close()
                self.assertFalse(thread.is_alive())
