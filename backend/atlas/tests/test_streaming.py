"""Streaming uses durable request IDs; no real provider credentials."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from backend.atlas.app.config import Settings
from backend.atlas.app.main import create_app
from backend.atlas.app.agent.agent import _stream_message
import time

TOKEN='stream-test-'+'x'*32
HEADERS={'Authorization':'Bearer '+TOKEN}

class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'GH_REPO':''},clear=True);self.env.start()
        self.settings=Settings(TOKEN,'fake',self.root)
        self.calls=0
    def tearDown(self):
        self.env.stop();self.temp.cleanup()
    def runner(self,history,text,emit):
        self.calls+=1
        emit('thinking','');emit('replying','Hel');emit('replying','Hello 世界')
        return 'Hello 世界',history+[{'role':'user','content':text},{'role':'assistant','content':'Hello 世界'}]
    def events(self,response):
        return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    def test_auth_completion_saved_replay_and_conflict(self):
        with TestClient(create_app(self.settings,streaming_runner=self.runner)) as c:
            body=dict(conversation_id=c.post('/api/v1/conversations',headers=HEADERS,json={}).json()['id'],request_id=str(uuid4()),message='Hi',require_existing=True)
            self.assertEqual(401,c.post('/api/v1/chat/stream',json=body).status_code)
            for _ in range(2):
                response=c.post('/api/v1/chat/stream',headers=HEADERS,json=body)
                self.assertEqual('text/event-stream; charset=utf-8',response.headers['content-type'])
                self.assertEqual('Hello 世界',self.events(response)[-1]['reply'])
                status=c.get(f"/api/v1/conversations/{body['conversation_id']}/requests/{body['request_id']}",headers=HEADERS).json()
                self.assertEqual('done',status['status']);self.assertEqual('Hello 世界',status['reply'])
            self.assertEqual(1,self.calls)
            response=c.post('/api/v1/chat/stream',headers=HEADERS,json={**body,'message':'Different'})
            self.assertEqual(409,self.events(response)[-1]['status']);self.assertEqual(1,self.calls)
            messages=c.get(f"/api/v1/conversations/{body['conversation_id']}/messages",headers=HEADERS).json()['items']
            self.assertEqual(2,len(messages))
    def test_failure_is_sanitized_and_partial_not_archived(self):
        def broken(h,t,emit):
            emit('replying','Partial');raise RuntimeError('SECRET provider details')
        with TestClient(create_app(self.settings,streaming_runner=broken)) as c:
            cid=c.post('/api/v1/conversations',headers=HEADERS,json={}).json()['id'];rid=str(uuid4())
            body=dict(conversation_id=cid,request_id=rid,message='Hi',require_existing=True)
            response=c.post('/api/v1/chat/stream',headers=HEADERS,json=body)
            self.assertNotIn('SECRET',response.text);self.assertEqual(500,self.events(response)[-1]['status'])
            self.assertEqual('failed',c.get(f'/api/v1/conversations/{cid}/requests/{rid}',headers=HEADERS).json()['status'])
            self.assertEqual([],c.get(f'/api/v1/conversations/{cid}/messages',headers=HEADERS).json()['items'])
            self.assertEqual(409,self.events(c.post('/api/v1/chat/stream',headers=HEADERS,json=body))[-1]['status'])
    def test_capacity_rejects_before_inference(self):
        with TestClient(create_app(self.settings,streaming_runner=self.runner)) as c:
            for _ in range(4):c.app.state.stream_slots.acquire()
            try:
                response=c.post('/api/v1/chat/stream',headers=HEADERS,json=dict(conversation_id='missing',request_id=str(uuid4()),message='Hi'))
                self.assertEqual(429,response.status_code);self.assertEqual(0,self.calls)
            finally:
                for _ in range(4):c.app.state.stream_slots.release()

class ProviderStreamTests(unittest.TestCase):
    def provider(self,chunks):
        class Stream:
            def __enter__(self):return iter(chunks)
            def __exit__(self,*args):pass
        return NS(chat=NS(completions=NS(create=lambda **kw:Stream())))
    def chunk(self,content=None,tools=None,finish=None):
        return NS(choices=[NS(delta=NS(content=content,tool_calls=tools),finish_reason=finish)])
    def test_fragmented_tool_arguments_private_and_incomplete_stream_rejected(self):
        calls=[NS(index=0,id='call1',function=NS(name='save_memory',arguments='{"fact":')),NS(index=0,id=None,function=NS(name=None,arguments='"secret"}'))]
        events=[]
        message=_stream_message(self.provider([self.chunk(tools=[calls[0]]),self.chunk(tools=[calls[1]]),self.chunk(finish='tool_calls')]),{},lambda *e:events.append(e),time.monotonic()+10)
        self.assertEqual('{"fact":"secret"}',message.tool_calls[0].function.arguments)
        self.assertNotIn('secret',str(events))
        with self.assertRaises(RuntimeError):
            _stream_message(self.provider([self.chunk('partial')]),{},lambda *e:None,time.monotonic()+10)
    def test_content_streams_before_completion(self):
        events=[]
        message=_stream_message(self.provider([self.chunk('Hel'),self.chunk('lo'),self.chunk(finish='stop')]),{},lambda *e:events.append(e),time.monotonic()+10)
        self.assertEqual('Hello',message.content)
        self.assertIn(('replying','Hel'),events);self.assertIn(('replying','Hello'),events)
