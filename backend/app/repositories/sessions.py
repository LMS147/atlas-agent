"""SQLite histories and persistent request deduplication for one API worker."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

class RequestConflict(Exception):
    pass

class SessionRepository:
    def __init__(self, path: Path):
        self.path = path
        self._locks = [threading.Lock() for _ in range(64)]
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    owner TEXT NOT NULL, id TEXT NOT NULL, history TEXT NOT NULL,
                    PRIMARY KEY (owner, id)
                );
                CREATE TABLE IF NOT EXISTS requests (
                    owner TEXT NOT NULL, conversation TEXT NOT NULL, id TEXT NOT NULL,
                    message TEXT NOT NULL, status TEXT NOT NULL, reply TEXT,
                    PRIMARY KEY (owner, conversation, id)
                );
            """)
            # A prior process may have died after a tool ran. Never silently execute it again.
            db.execute("UPDATE requests SET status='interrupted' WHERE status='pending'")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def chat(self, owner: str, conversation: str, request_id: str, message: str, runner) -> str:
        slot = int.from_bytes(hashlib.sha256(f"{owner}\0{conversation}".encode()).digest()[:2], "big") % len(self._locks)
        with self._locks[slot]:
            key = (owner, conversation, request_id)
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                previous = db.execute("SELECT message, status, reply FROM requests WHERE owner=? AND conversation=? AND id=?", key).fetchone()
                if previous:
                    if previous[0] != message:
                        raise RequestConflict("Request ID was already used with a different message")
                    if previous[1] == "done":
                        return previous[2]
                    raise RequestConflict("Previous request did not complete safely; inspect the conversation before sending a new request")
                row = db.execute("SELECT history FROM conversations WHERE owner=? AND id=?", (owner, conversation)).fetchone()
                history = json.loads(row[0]) if row else []
                db.execute("INSERT INTO requests VALUES (?, ?, ?, ?, 'pending', NULL)", (*key, message))
            try:
                reply, history = runner(history, message)
                if not isinstance(reply, str) or not reply.strip() or not isinstance(history, list):
                    raise RuntimeError("Agent returned an invalid result")
                # Bound context without cutting off a tool turn. The complete response is cached.
                history = history[-24:]
                while history and history[0].get("role") != "user":
                    history.pop(0)
                with self._db() as db:
                    db.execute("INSERT INTO conversations VALUES (?, ?, ?) ON CONFLICT(owner,id) DO UPDATE SET history=excluded.history", (owner, conversation, json.dumps(history)))
                    db.execute("UPDATE requests SET status='done', reply=? WHERE owner=? AND conversation=? AND id=?", (reply, *key))
                return reply
            except Exception:
                with self._db() as db:
                    db.execute("UPDATE requests SET status='failed' WHERE owner=? AND conversation=? AND id=?", key)
                raise
