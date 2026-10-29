
import os
import hashlib
import re
import tempfile
from contextlib import contextmanager
from functools import wraps
from filelock import FileLock
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

USE_GITHUB = bool(os.environ.get("GH_REPO"))

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
SEED_DIR = Path(__file__).resolve().parents[2] / "seed"
AGENT_FILE = DATA_DIR / "agent.md"
MEMORY_FILE = DATA_DIR / "memory.md"
BACKUP_DIR = DATA_DIR / "backups"

SECTIONS = ["User Preferences", "Projects", "Decisions", "People"]
MAX_MEMORY_CHARS = 12_000

_lock = threading.RLock()

if USE_GITHUB:
    from backend.app.repositories import github_storage as storage


@contextmanager
def _storage_lock():
    # Telegram and FastAPI can safely share a local DATA_DIR in separate processes.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock, FileLock(str(DATA_DIR / ".memory.lock"), timeout=20):
        yield


def locked(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with _storage_lock():
            return fn(*args, **kwargs)
    return wrapper


def configure(data_dir: Path) -> None:
    """Called once during API startup after environment configuration is loaded."""
    global DATA_DIR, AGENT_FILE, MEMORY_FILE, BACKUP_DIR, USE_GITHUB, storage
    DATA_DIR = Path(data_dir)
    AGENT_FILE = DATA_DIR / "agent.md"
    MEMORY_FILE = DATA_DIR / "memory.md"
    BACKUP_DIR = DATA_DIR / "backups"
    USE_GITHUB = bool(os.getenv("GH_REPO"))
    if USE_GITHUB:
        from backend.app.repositories import github_storage as storage


def list_items() -> list[dict]:
    """Stable content-based IDs survive file reloads and entry reordering."""
    section = "Projects"
    items = []
    seen = set()
    for line in load_memory().splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("- ") and section in SECTIONS:
            fact = re.sub(r"\s+_\d{4}-\d{2}-\d{2}_$", "", line[2:]).strip()
            if not fact:
                continue
            identifier = hashlib.sha256(f"{section}\0{fact.casefold()}".encode()).hexdigest()
            if identifier not in seen:
                items.append(dict(id=identifier, section=section, fact=fact))
                seen.add(identifier)
    return items


# ---------------------------------------------------------------- backends

def _read(name: str) -> str:
    if USE_GITHUB:
        return storage.read(name)
    return (DATA_DIR / name).read_text(encoding="utf-8")


def _write(name: str, text: str, message: str = "update") -> None:
    if USE_GITHUB:
        storage.write(name, text, message)
    else:
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA_DIR, delete=False) as handle:
                temp_name = handle.name
                handle.write(text)
            os.replace(temp_name, DATA_DIR / name)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)


@locked
def ensure_files() -> None:
    """Create the storage layout on first boot; seed files win only once."""
    if USE_GITHUB:
        for name in ("agent.md", "memory.md"):
            if not storage.read(name):
                storage.write(name, (SEED_DIR / name).read_text(encoding="utf-8"),
                              f"seed {name}")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    for name in ("agent.md", "memory.md"):
        target, seed = DATA_DIR / name, SEED_DIR / name
        if not target.exists():
            shutil.copy(seed, target)


@locked
def load_agent() -> str:
    return _read("agent.md")


@locked
def load_memory() -> str:
    return _read("memory.md")


def _backup() -> None:
    """Local mode only — git history covers the GitHub backend."""
    if USE_GITHUB:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy(MEMORY_FILE, BACKUP_DIR / f"memory-{stamp}.md")
    old = sorted(BACKUP_DIR.glob("memory-*.md"))[:-30]
    for f in old:
        f.unlink()


# ---------------------------------------------------------------- writes

@locked
def append_memory(section: str, fact: str) -> str:
    """Append one bullet under a heading. Returns a status string for the model."""
    fact = " ".join(fact.split())

    if not fact:
        return "rejected: empty"
    if len(fact) > 300:
        return "rejected: too long, summarise to one sentence"
    if section not in SECTIONS:
        section = "Projects"

    with _lock:
        text = _read("memory.md")

        if fact.lower() in text.lower():
            return "skipped: already known"
        if len(text) > MAX_MEMORY_CHARS:
            return "rejected: memory full, user must run /compact"

        entry = f"- {fact}  _{datetime.now(timezone.utc):%Y-%m-%d}_"
        heading = f"## {section}"
        lines = text.splitlines()

        if heading in lines:
            i = lines.index(heading) + 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            while i > 0 and not lines[i - 1].strip():
                i -= 1
            lines.insert(i, entry)
            text = "\n".join(lines)
        else:
            text = f"{text.rstrip()}\n\n{heading}\n{entry}\n"

        if len(text) > MAX_MEMORY_CHARS:
            return "rejected: memory full, user must run /compact"
        _backup()
        _write("memory.md", text, f"remember: {fact[:50]}")

    return "saved"


@locked
def overwrite_memory(new_text: str) -> None:
    with _lock:
        _backup()
        _write("memory.md", new_text, "compact memory")



def _line_identity(line, section):
    if not line.startswith("- ") or section not in SECTIONS:
        return None
    fact = re.sub(r"\s+_\d{4}-\d{2}-\d{2}_$", "", line[2:]).strip()
    return hashlib.sha256(f"{section}\0{fact.casefold()}".encode()).hexdigest() if fact else None


@locked
def change_item(identifier, section=None, fact=None):
    """Content IDs act as edit preconditions; unrelated Markdown is preserved."""
    text = _read("memory.md")
    lines, current, found = [], "Projects", False
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
        if _line_identity(line, current) == identifier:
            found = True
        else:
            lines.append(line)
    if not found:
        raise KeyError(identifier)
    if fact is not None:
        if section not in SECTIONS or not fact or len(fact) > 300:
            raise ValueError("Invalid memory fact")
        heading = f"## {section}"
        if heading not in lines:
            lines.extend(["", heading])
        index = lines.index(heading) + 1
        lines.insert(index, f"- {fact}  _{datetime.now(timezone.utc):%Y-%m-%d}_")
    updated = "\n".join(lines) + "\n"
    if len(updated) > MAX_MEMORY_CHARS and len(updated) > len(text):
        raise ValueError("Memory is full; compact or shorten the fact")
    _backup()
    _write("memory.md", updated, "edit memory" if fact else "delete memory")


def _compacted(text):
    # Conservative compaction: exact normalized duplicates and repeated blank lines.
    # No inference, truncation, paraphrasing, or loss of unknown Markdown content.
    current, seen, lines, removed = "Projects", set(), [], 0
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
        identifier = _line_identity(line, current)
        key = (current, " ".join(re.sub(r"\s+_\d{4}-\d{2}-\d{2}_$", "", line[2:]).split()).casefold()) if identifier else None
        if key and key in seen:
            removed += 1
            continue
        if key:
            seen.add(key)
        if not line.strip() and lines and not lines[-1].strip():
            continue
        lines.append(line)
    return "\n".join(lines).rstrip() + "\n", removed


@locked
def compact_plan(revision=None):
    text = _read("memory.md")
    digest = hashlib.sha256(text.encode()).hexdigest()
    updated, removed = _compacted(text)
    plan = dict(revision=digest, before_chars=len(text), after_chars=len(updated), removed_entries=removed)
    if revision is not None:
        if revision != digest:
            raise ValueError("Memory changed; preview compaction again")
        if updated != text:
            _backup()
            _write("memory.md", updated, "compact duplicate memory")
    return plan
