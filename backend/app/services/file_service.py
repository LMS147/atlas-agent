"""Expose only approved workspace files, never secrets, logs, or SQLite data."""
from backend.app.services import memory_service as memory


def list_files() -> list[dict]:
    if memory.USE_GITHUB:
        return [dict(name=name, path=name, directory=False, size_bytes=len(content.encode("utf-8")))
                for name, content in (("agent.md", memory.load_agent()), ("memory.md", memory.load_memory()))]
    root = memory.DATA_DIR.resolve()
    files = []
    for name in ("agent.md", "memory.md", "backups"):
        path = root / name
        if path.is_symlink() or not path.exists() or path.resolve().parent != root:
            continue
        files.append(dict(name=name, path=name, directory=path.is_dir(), size_bytes=0 if path.is_dir() else path.stat().st_size))
    return files
