"""Confined workspace storage. Credentials, databases and logs are never exposed."""
import hashlib
import os
from pathlib import Path
import re
import tempfile
from fastapi import HTTPException
from filelock import FileLock
from backend.atlas.app.services import memory_service as memory

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT_BYTES = 256 * 1024
BACKUP_NAME = re.compile(r"^memory-[0-9]{8}-[0-9]{6}-[0-9]{6}\.md$")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}$")


def workspace():
    path = memory.DATA_DIR / "workspace"
    if path.is_symlink():
        raise HTTPException(403, "Workspace must not be a symlink")
    path.mkdir(exist_ok=True)
    return path


def target(identifier, writing=False):
    parts = identifier.split("/")
    if len(parts) == 1 and identifier in ("agent.md", "memory.md"):
        if writing:
            raise HTTPException(403, "Use memory controls; agent profile is read-only")
        path = memory.DATA_DIR / identifier
    elif len(parts) == 2 and parts[0] in ("workspace", "backups") and NAME.fullmatch(parts[1]):
        if parts[1] in (".", "..") or (parts[0] == "backups" and writing):
            raise HTTPException(403, "Read-only directory")
        if parts[0] == "backups" and not BACKUP_NAME.fullmatch(parts[1]):
            raise HTTPException(403, "Only Atlas memory snapshots are exposed")
        parent = workspace() if parts[0] == "workspace" else memory.BACKUP_DIR
        if parent.is_symlink():
            raise HTTPException(403, "Symlinks are not exposed")
        path = parent / parts[1]
    else:
        raise HTTPException(400, "Invalid workspace path")
    if path.is_symlink():
        raise HTTPException(403, "Symlinks are not exposed")
    if path.exists() and not path.is_file():
        raise HTTPException(400, "Choose a file")
    return path


def list_files(directory=""):
    if not directory:
        workspace()
        rows = []
        if memory.USE_GITHUB:
            rows.extend(dict(name=name, path=name, directory=False, size_bytes=len(content.encode()), writable=False)
                        for name, content in (("agent.md", memory.load_agent()), ("memory.md", memory.load_memory())))
        for name in ("agent.md", "memory.md", "backups", "workspace"):
            if memory.USE_GITHUB and name in ("agent.md", "memory.md"):
                continue
            path = memory.DATA_DIR / name
            if not path.is_symlink() and path.exists():
                rows.append(dict(name=name, path=name, directory=path.is_dir(), size_bytes=0 if path.is_dir() else path.stat().st_size, writable=False))
        return rows
    if directory not in ("workspace", "backups"):
        raise HTTPException(400, "Invalid directory")
    parent = workspace() if directory == "workspace" else memory.BACKUP_DIR
    if parent.is_symlink():
        raise HTTPException(403, "Symlinks are not exposed")
    if not parent.is_dir():
        raise HTTPException(404, "Directory not found")
    return [dict(name=p.name, path=f"{directory}/{p.name}", directory=False, size_bytes=p.stat().st_size, writable=directory == "workspace")
            for p in sorted(parent.iterdir()) if not p.is_symlink() and p.is_file() and NAME.fullmatch(p.name) and (directory != "backups" or BACKUP_NAME.fullmatch(p.name))]


def read(identifier):
    # GitHub-backed canonical documents remain supported, workspace is always local.
    if memory.USE_GITHUB and identifier in ("agent.md", "memory.md"):
        data = (memory.load_agent() if identifier == "agent.md" else memory.load_memory()).encode()
    else:
        path = target(identifier)
        try:
            with path.open("rb") as handle:
                data = handle.read(MAX_BYTES + 1)
        except FileNotFoundError:
            raise HTTPException(404, "File not found") from None
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File exceeds the 5 MiB download limit")
    return data, hashlib.sha256(data).hexdigest()


def document(identifier):
    data, revision = read(identifier)
    if len(data) > MAX_TEXT_BYTES:
        raise HTTPException(413, "Text editor supports up to 256 KiB; download this file")
    try:
        text = data.decode("utf-8")
        if "\x00" in text:
            raise ValueError()
    except (UnicodeError, ValueError):
        raise HTTPException(415, "Binary file; use Download") from None
    return dict(path=identifier, content=text, revision=revision, writable=identifier.startswith("workspace/"))


def write(identifier, data, revision):
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Uploads are limited to 5 MiB")
    path = target(identifier, writing=True)
    # Cross-process lock plus exclusive create prevents accidental upload overwrites.
    with FileLock(str(memory.DATA_DIR / ".workspace.lock"), timeout=20):
        if revision is None:
            if path.exists():
                raise HTTPException(409, "File already exists; open it to edit")
        else:
            if not path.exists() or read(identifier)[1] != revision:
                raise HTTPException(409, "File changed; reopen before saving")
        name = None
        try:
            with tempfile.NamedTemporaryFile(dir=workspace(), delete=False) as handle:
                name = handle.name
                os.chmod(name, 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)
    return dict(name=path.name, path=identifier, directory=False, size_bytes=len(data), writable=True)
