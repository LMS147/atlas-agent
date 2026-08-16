
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

USE_GITHUB = bool(os.environ.get("GH_REPO"))

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
SEED_DIR = Path(__file__).parent / "seed"
AGENT_FILE = DATA_DIR / "agent.md"
MEMORY_FILE = DATA_DIR / "memory.md"
BACKUP_DIR = DATA_DIR / "backups"

SECTIONS = ["User Preferences", "Projects", "Decisions", "People"]
MAX_MEMORY_CHARS = 12_000

_lock = threading.Lock()

if USE_GITHUB:
    import storage


# ---------------------------------------------------------------- backends

def _read(name: str) -> str:
    if USE_GITHUB:
        return storage.read(name)
    return (DATA_DIR / name).read_text(encoding="utf-8")


def _write(name: str, text: str, message: str = "update") -> None:
    if USE_GITHUB:
        storage.write(name, text, message)
    else:
        (DATA_DIR / name).write_text(text, encoding="utf-8")


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


def load_agent() -> str:
    return _read("agent.md")


def load_memory() -> str:
    return _read("memory.md")


def _backup() -> None:
    """Local mode only — git history covers the GitHub backend."""
    if USE_GITHUB:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shutil.copy(MEMORY_FILE, BACKUP_DIR / f"memory-{stamp}.md")
    old = sorted(BACKUP_DIR.glob("memory-*.md"))[:-30]
    for f in old:
        f.unlink()


# ---------------------------------------------------------------- writes

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

        _backup()
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

        _write("memory.md", text, f"remember: {fact[:50]}")

    return "saved"


def overwrite_memory(new_text: str) -> None:
    with _lock:
        _backup()
        _write("memory.md", new_text, "compact memory")
