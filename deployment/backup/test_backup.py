import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('atlas_backup', Path(__file__).with_name('atlas_backup.py'))
backup = importlib.util.module_from_spec(spec); spec.loader.exec_module(backup)

class BackupTests(unittest.TestCase):
    def test_roundtrip_with_sqlite_and_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); data = root / 'data'; data.mkdir()
            (data / 'memory.md').write_text('Remember Atlas', encoding='utf8')
            (data / 'files').mkdir(); (data / 'files' / 'a.bin').write_bytes(bytes(range(256)))
            with sqlite3.connect(data / 'sessions.db') as db:
                db.execute('CREATE TABLE chats(text TEXT)'); db.execute("INSERT INTO chats VALUES ('hello')")
            archive = root / 'copy.zip'; backup.create(data, archive)
            backup.restore(archive, root / 'restored')
            self.assertEqual((root/'restored/memory.md').read_text(), 'Remember Atlas')
            self.assertEqual((root/'restored/files/a.bin').read_bytes(), bytes(range(256)))
            with sqlite3.connect(root/'restored/sessions.db') as db:
                self.assertEqual(db.execute('SELECT text FROM chats').fetchone()[0], 'hello')
            with self.assertRaises(ValueError): backup.restore(archive, data)
            with self.assertRaises(ValueError): backup.create(data, archive)

    def test_tamper_and_traversal_rejected_without_destination(self):
        for name, checksum in [('data/a.txt', 'invalid'), ('data/../../outside', 'invalid')]:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp); archive=root/'bad.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    z.writestr('manifest.json', json.dumps({'format':1,'files':{'a.txt':checksum}}))
                    z.writestr(name,'tampered')
                with self.assertRaises(ValueError): backup.restore(archive,root/'restored')
                self.assertFalse((root/'restored').exists())

    def test_symlinks_and_secrets_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); data=root/'data';data.mkdir();(data/'.env').write_text('SECRET')
            with self.assertRaises(ValueError): backup.create(data,root/'copy.zip')
            (data/'.env').unlink();(data/'link').symlink_to(root)
            with self.assertRaises(ValueError): backup.create(data,root/'copy.zip')

if __name__ == '__main__': unittest.main()
