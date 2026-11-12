"""Authenticated file and memory contract tests."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.atlas.app.config import Settings
from backend.atlas.app.main import create_app
from backend.atlas.app.services import memory_service as memory
from backend.atlas.app.services import file_service as files

TOKEN = 'management-test-token-' + 'x' * 32
AUTH = {'Authorization': f'Bearer {TOKEN}'}

class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'GH_REPO': ''})
        self.env.start()
        self.client = TestClient(create_app(Settings(api_token=TOKEN, groq_api_key='fake', data_dir=self.root)), raise_server_exceptions=False)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.temp.cleanup()

    def test_new_endpoints_authenticate_before_access(self):
        for method, path, kwargs in [
            ('GET','files/content?path=agent.md',{}),('GET','files/text?path=memory.md',{}),
            ('POST','files/upload?name=test.txt',{'content': b'private'}),
            ('PUT','files/text?path=workspace/test.txt',{'json':dict(content='x',revision='a'*64)}),
            ('PATCH','memory/'+'a'*64,{'json':dict(section='Projects',fact='x')}),
            ('DELETE','memory/'+'a'*64,{}),('GET','memory/compact',{}),
            ('POST','memory/compact',{'json':dict(revision='a'*64)})]:
            self.assertEqual(401,self.client.request(method,'/api/v1/'+path,**kwargs).status_code,path)
        self.assertFalse((self.root/'workspace/test.txt').exists())

    def test_file_roundtrip_conflicts_and_utf8_edit(self):
        self.assertEqual(201,self.client.post('/api/v1/files/upload?name=notes.txt',content='héllo'.encode(),headers=AUTH).status_code)
        listing=self.client.get('/api/v1/files?directory=workspace',headers=AUTH).json()
        self.assertEqual(['notes.txt'],[x['name'] for x in listing])
        doc=self.client.get('/api/v1/files/text?path=workspace/notes.txt',headers=AUTH).json()
        self.assertEqual('héllo',doc['content']);self.assertTrue(doc['writable'])
        self.assertEqual(409,self.client.post('/api/v1/files/upload?name=notes.txt',content=b'overwrite',headers=AUTH).status_code)
        edit=dict(content='edited',revision=doc['revision'])
        self.assertEqual(200,self.client.put('/api/v1/files/text?path=workspace/notes.txt',json=edit,headers=AUTH).status_code)
        self.assertEqual(409,self.client.put('/api/v1/files/text?path=workspace/notes.txt',json=edit,headers=AUTH).status_code)
        response=self.client.get('/api/v1/files/content?path=workspace/notes.txt',headers=AUTH)
        self.assertEqual(b'edited',response.content)
        self.assertEqual('"'+hashlib.sha256(b'edited').hexdigest()+'"',response.headers['etag'])

    def test_confinement_binary_limits_and_reserved_files(self):
        (self.root/'.env').write_text('secret')
        for path in ('../.env','workspace/../.env','/etc/passwd','backups/../.env','workspace/.env'):
            self.assertEqual(400,self.client.get('/api/v1/files/content',params={'path':path},headers=AUTH).status_code,path)
        (self.root/'workspace').mkdir(exist_ok=True)
        (self.root/'workspace/link.txt').symlink_to(self.root/'.env')
        self.assertEqual(403,self.client.get('/api/v1/files/content?path=workspace/link.txt',headers=AUTH).status_code)
        self.assertEqual([],self.client.get('/api/v1/files?directory=workspace',headers=AUTH).json())
        self.assertEqual(403,self.client.put('/api/v1/files/text?path=memory.md',json=dict(content='erase',revision='a'*64),headers=AUTH).status_code)
        self.assertEqual(201,self.client.post('/api/v1/files/upload?name=image.bin',content=b'\x00\xff',headers=AUTH).status_code)
        self.assertEqual(415,self.client.get('/api/v1/files/text?path=workspace/image.bin',headers=AUTH).status_code)
        self.assertEqual(b'\x00\xff',self.client.get('/api/v1/files/content?path=workspace/image.bin',headers=AUTH).content)
        with patch.object(files,'MAX_BYTES',4):
            self.assertEqual(413,self.client.post('/api/v1/files/upload?name=huge.bin',content=b'12345',headers=AUTH).status_code)
        self.assertFalse((self.root/'workspace/huge.bin').exists())
        (self.root/'backups/private.log').write_text('private')
        (self.root/'backups/atlas.sqlite3').write_text('database')
        self.assertEqual([],self.client.get('/api/v1/files?directory=backups',headers=AUTH).json())
        self.assertEqual(403,self.client.get('/api/v1/files/content?path=backups/private.log',headers=AUTH).status_code)
        self.client.post('/api/v1/memory',json=dict(section='Projects',fact='Create a snapshot'),headers=AUTH)
        snapshots=self.client.get('/api/v1/files?directory=backups',headers=AUTH).json()
        self.assertEqual(1,len(snapshots))
        self.assertEqual(200,self.client.get('/api/v1/files/content',params={'path':snapshots[0]['path']},headers=AUTH).status_code)

    def test_memory_edit_delete_and_stale_ids(self):
        item=self.client.post('/api/v1/memory',json=dict(section='Projects',fact='Original'),headers=AUTH).json()
        edit=dict(section='People',fact='Updated')
        path='/api/v1/memory/'+item['id']
        self.assertEqual(204,self.client.patch(path,json=edit,headers=AUTH).status_code)
        self.assertEqual(409,self.client.patch(path,json=edit,headers=AUTH).status_code)
        rows=self.client.get('/api/v1/memory',headers=AUTH).json()
        updated=next(x for x in rows if x['fact']=='Updated')
        self.assertEqual('People',updated['section'])
        self.assertEqual(204,self.client.delete('/api/v1/memory/'+updated['id'],headers=AUTH).status_code)
        self.assertFalse(any(x['fact']=='Updated' for x in self.client.get('/api/v1/memory',headers=AUTH).json()))
        self.assertGreaterEqual(len(list((self.root/'backups').glob('memory-*.md'))),3)

    def test_compaction_is_conservative_and_revision_checked(self):
        text='# Memory\n\nCustom prose stays.\n\n\n## Projects\n- Keep this  _2026-01-01_\n- Keep this  _2026-02-01_\n\n## Unknown\n- Never discard me\n'
        memory.overwrite_memory(text)
        plan=self.client.get('/api/v1/memory/compact',headers=AUTH).json()
        self.assertEqual(1,plan['removed_entries'])
        self.assertEqual(text,memory.load_memory())
        self.assertEqual(200,self.client.post('/api/v1/memory/compact',json={'revision':plan['revision']},headers=AUTH).status_code)
        self.assertIn('Custom prose stays.',memory.load_memory());self.assertIn('- Never discard me',memory.load_memory())
        self.assertEqual(1,memory.load_memory().count('Keep this'))
        self.assertEqual(409,self.client.post('/api/v1/memory/compact',json={'revision':plan['revision']},headers=AUTH).status_code)
