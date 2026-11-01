"""Offline, verified Atlas workspace backups. Stop API and Telegram before use."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

MAX_BYTES = 10 * 1024**3

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def safe_name(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or p.is_absolute() or '..' in p.parts or ':' in name or str(p) != name:
        raise ValueError('Unsafe archive path')
    return p

def verify(archive):
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or len(names) > 100000:
            raise ValueError('Duplicate or excessive archive entries')
        if sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError('Backup exceeds 10 GiB limit')
        for i in infos:
            safe_name(i.filename)
            if i.is_dir() or (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unexpected directory or symbolic link')
        if z.getinfo('manifest.json').file_size > 16 * 1024**2:
            raise ValueError('Manifest too large')
        manifest = json.loads(z.read('manifest.json'))
        if manifest.get('format') != 1 or not isinstance(manifest.get('files'), dict):
            raise ValueError('Unsupported backup format')
        expected = manifest['files']
        if set(names) != {'manifest.json'} | {'data/' + n for n in expected}:
            raise ValueError('Unexpected or missing files')
        for name, checksum in expected.items():
            safe_name(name)
            h = hashlib.sha256()
            with z.open('data/' + name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(chunk)
            if h.hexdigest() != checksum:
                raise ValueError('Backup checksum mismatch')
        return manifest

def create(data_dir, archive):
    data_dir, archive = Path(data_dir).resolve(), Path(archive).resolve()
    if not data_dir.is_dir() or archive.is_relative_to(data_dir):
        raise ValueError('Choose an existing workspace and a backup path outside it')
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise ValueError('Refusing to overwrite an existing backup')
    with tempfile.TemporaryDirectory(dir=archive.parent) as temp:
        stage = Path(temp) / 'data'; stage.mkdir()
        files = {}
        for source in sorted(data_dir.rglob('*')):
            if source.is_symlink():
                raise ValueError('Workspace contains symbolic links')
            if not source.is_file():
                continue
            name = source.relative_to(data_dir).as_posix()
            if source.name.endswith(('-wal', '-shm', '.lock')):
                continue
            if source.name == '.env' or source.suffix.lower() in {'.jks', '.keystore', '.pem', '.key'}:
                raise ValueError('Keep credentials and signing keys outside DATA_DIR')
            safe_name(name)
            target = stage / name; target.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as f:
                is_sqlite = f.read(16) == b'SQLite format 3\x00'
            if is_sqlite:
                with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
                    src.backup(dst)
                    if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Invalid SQLite database')
            else:
                shutil.copyfile(source, target)
            files[name] = digest(target)
        pending = Path(temp) / 'backup.zip'
        with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('manifest.json', json.dumps({'format': 1, 'files': files}, sort_keys=True))
            for name in files:
                z.write(stage / name, 'data/' + name)
        verify(pending)
        os.chmod(pending, 0o600)
        # Hard link publishes atomically and refuses concurrent overwrite.
        os.link(pending, archive)
    return len(files)

def restore(archive, destination):
    destination = Path(destination).absolute()
    if destination.exists():
        raise ValueError('Restore requires a NEW destination; existing data is never overwritten')
    manifest = verify(archive)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        stage = Path(temp) / 'restored'; stage.mkdir(mode=0o700)
        with zipfile.ZipFile(archive) as z:
            for name in manifest['files']:
                target = stage / name; target.parent.mkdir(parents=True, exist_ok=True)
                with z.open('data/' + name) as src, target.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
                os.chmod(target, 0o600)
                if digest(target) != manifest['files'][name]:
                    raise ValueError('Archive changed during restore')
                with target.open('rb') as f:
                    is_sqlite = f.read(16) == b'SQLite format 3\x00'
                if is_sqlite:
                    with sqlite3.connect(target) as db:
                        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise ValueError('Invalid restored database')
        # Destination is operator-selected and must remain absent.
        if destination.exists():
            raise ValueError('Destination appeared during restore')
        stage.rename(destination)
    return len(manifest['files'])

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('create'); c.add_argument('--data-dir', required=True); c.add_argument('--archive', required=True); c.add_argument('--services-stopped', action='store_true', required=True)
    v = sub.add_parser('verify'); v.add_argument('--archive', required=True)
    r = sub.add_parser('restore'); r.add_argument('--archive', required=True); r.add_argument('--destination', required=True); r.add_argument('--services-stopped', action='store_true', required=True)
    a = p.parse_args()
    try:
        if a.command == 'create': print(f'Backed up {create(a.data_dir, a.archive)} files')
        elif a.command == 'restore': print(f'Restored {restore(a.archive, a.destination)} files')
        else: verify(a.archive); print('Backup verified')
    except (ValueError, OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, sqlite3.Error) as e:
        p.exit(1, f'Backup operation failed: {type(e).__name__}. No live workspace was replaced.\n')

if __name__ == '__main__': main()
