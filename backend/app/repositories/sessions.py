"""Durable conversations, complete transcripts, and request deduplication (one API worker)."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
from uuid import uuid4

class RequestConflict(Exception):
    pass

class ConversationMissing(Exception):
    pass

class ConversationGone(Exception):
    pass


def now_ms():
    return time.time_ns() // 1_000_000


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
                CREATE TABLE IF NOT EXISTS transcript (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner TEXT NOT NULL, conversation TEXT NOT NULL, id TEXT NOT NULL,
                    request_id TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE (owner, conversation, request_id, role)
                );
                CREATE INDEX IF NOT EXISTS transcript_conversation ON transcript(owner, conversation, seq);
                CREATE TABLE IF NOT EXISTS atlas_schema (name TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(conversations)")}
            for name, definition in (("title", "TEXT NOT NULL DEFAULT 'New chat'"), ("created_at", "INTEGER NOT NULL DEFAULT 0"),
                                     ("updated_at", "INTEGER NOT NULL DEFAULT 0"), ("deleted", "INTEGER NOT NULL DEFAULT 0")):
                if name not in columns:
                    db.execute(f"ALTER TABLE conversations ADD COLUMN {name} {definition}")
            if "created_at" not in {row[1] for row in db.execute("PRAGMA table_info(requests)")}:
                db.execute("ALTER TABLE requests ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0")
            if not db.execute("SELECT 1 FROM atlas_schema WHERE name='transcript_imported'").fetchone():
                self._import_legacy(db)
                db.execute("INSERT INTO atlas_schema VALUES ('transcript_imported','1')")
            # A previous process may have died after a tool ran. Never silently run it again.
            db.execute("UPDATE requests SET status='interrupted' WHERE status='pending'")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _import_legacy(self, db):
        imported_at = now_ms()
        db.execute("INSERT OR IGNORE INTO conversations(owner,id,history) SELECT owner,conversation,'[]' FROM requests GROUP BY owner,conversation")
        rows = db.execute("SELECT * FROM requests WHERE status='done' ORDER BY rowid").fetchall()
        for index, row in enumerate(rows):
            if isinstance(row["reply"], str):
                created = row["created_at"] or imported_at + index * 2
                self._archive(db, row["owner"], row["conversation"], row["id"], row["message"], row["reply"], created)
        db.execute("UPDATE conversations SET created_at=? WHERE created_at=0", (imported_at,))
        db.execute("UPDATE conversations SET updated_at=created_at WHERE updated_at=0")

    def _ensure(self, db, owner, conversation):
        row = db.execute("SELECT * FROM conversations WHERE owner=? AND id=?", (owner, conversation)).fetchone()
        if row and row["deleted"]:
            raise ConversationGone("This conversation was deleted. Choose or create another chat.")
        if not row:
            timestamp = now_ms()
            db.execute("INSERT INTO conversations(owner,id,history,title,created_at,updated_at) VALUES (?,?,'[]','New chat',?,?)",
                       (owner, conversation, timestamp, timestamp))
            row = db.execute("SELECT * FROM conversations WHERE owner=? AND id=?", (owner, conversation)).fetchone()
        return row

    def _existing(self, db, owner, conversation):
        row = db.execute("SELECT * FROM conversations WHERE owner=? AND id=?", (owner, conversation)).fetchone()
        if not row:
            raise ConversationMissing("Conversation not found")
        if row["deleted"]:
            raise ConversationGone("This conversation was deleted. Choose or create another chat.")
        return row

    def _archive(self, db, owner, conversation, request_id, message, reply, created):
        last = db.execute("SELECT MAX(created_at) FROM transcript WHERE owner=? AND conversation=?", (owner, conversation)).fetchone()[0]
        created = max(created, (last or 0) + 1)
        for role, text, timestamp in (("user", message, created), ("assistant", reply, max(now_ms(), created + 1))):
            identifier = hashlib.sha256(f"{owner}\0{conversation}\0{request_id}\0{role}".encode()).hexdigest()
            db.execute("INSERT OR IGNORE INTO transcript(owner,conversation,id,request_id,role,text,created_at) VALUES (?,?,?,?,?,?,?)",
                       (owner, conversation, identifier, request_id, role, text, timestamp))
        title = " ".join(message.split())[:60] or "New chat"
        db.execute("""UPDATE conversations SET
                    title=CASE WHEN title='New chat' AND (SELECT COUNT(*) FROM transcript WHERE owner=? AND conversation=?)=2 THEN ? ELSE title END,
                    created_at=CASE WHEN created_at=0 THEN ? ELSE created_at END,
                    updated_at=MAX(updated_at,?) WHERE owner=? AND id=?""",
                   (owner, conversation, title, created, max(now_ms(), created + 1), owner, conversation))

    def _summary(self, db, row):
        owner, identifier = row["owner"], row["id"]
        count = db.execute("SELECT COUNT(*) FROM transcript WHERE owner=? AND conversation=?", (owner, identifier)).fetchone()[0]
        preview = db.execute("SELECT text FROM transcript WHERE owner=? AND conversation=? ORDER BY seq DESC LIMIT 1", (owner, identifier)).fetchone()
        return dict(id=identifier, title=row["title"], created_at=row["created_at"], updated_at=row["updated_at"],
                    message_count=count, preview=preview[0][:160] if preview else "", deleted=bool(row["deleted"]))

    def list_conversations(self, owner, include_deleted=False):
        with self._db() as db:
            return [self._summary(db, row) for row in db.execute("SELECT * FROM conversations WHERE owner=? AND (deleted=0 OR ?=1) ORDER BY updated_at DESC,id", (owner, int(include_deleted))).fetchall()]

    def get_conversation(self, owner, identifier):
        with self._db() as db:
            return self._summary(db, self._existing(db, owner, identifier))

    def create_conversation(self, owner, title="New chat"):
        identifier = f"chat-{uuid4()}"
        with self._db() as db:
            self._ensure(db, owner, identifier)
            db.execute("UPDATE conversations SET title=? WHERE owner=? AND id=?", (title, owner, identifier))
            return self._summary(db, self._existing(db, owner, identifier))

    def rename_conversation(self, owner, identifier, title):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._existing(db, owner, identifier)
            db.execute("UPDATE conversations SET title=?,updated_at=? WHERE owner=? AND id=?", (title, now_ms(), owner, identifier))
            return self._summary(db, self._existing(db, owner, identifier))

    def delete_conversation(self, owner, identifier):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._existing(db, owner, identifier)
            if db.execute("SELECT 1 FROM requests WHERE owner=? AND conversation=? AND status='pending'", (owner, identifier)).fetchone():
                raise RequestConflict("A reply is still being generated. Wait before deleting this chat.")
            db.execute("DELETE FROM transcript WHERE owner=? AND conversation=?", (owner, identifier))
            db.execute("DELETE FROM requests WHERE owner=? AND conversation=?", (owner, identifier))
            db.execute("UPDATE conversations SET deleted=1,history='[]',title='Deleted chat',updated_at=? WHERE owner=? AND id=?", (now_ms(), owner, identifier))

    def messages(self, owner, identifier, before=None, limit=50):
        with self._db() as db:
            self._existing(db, owner, identifier)
            rows = db.execute("SELECT seq,id,request_id,role,text,created_at FROM transcript WHERE owner=? AND conversation=? AND (? IS NULL OR seq<?) ORDER BY seq DESC LIMIT ?",
                              (owner, identifier, before, before, limit + 1)).fetchall()
            more = len(rows) > limit
            items = [dict(row) for row in rows[:limit]][::-1]
            return dict(items=items, has_more=more, next_before=items[0]["seq"] if more and items else None)

    def chat(self, owner: str, conversation: str, request_id: str, message: str, runner) -> str:
        slot = int.from_bytes(hashlib.sha256(f"{owner}\0{conversation}".encode()).digest()[:2], "big") % len(self._locks)
        with self._locks[slot]:
            key = (owner, conversation, request_id)
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                row = self._ensure(db, owner, conversation)
                previous = db.execute("SELECT message,status,reply FROM requests WHERE owner=? AND conversation=? AND id=?", key).fetchone()
                if previous:
                    if previous[0] != message:
                        raise RequestConflict("Request ID was already used with a different message")
                    if previous[1] == "done":
                        return previous[2]
                    raise RequestConflict("Previous request did not complete safely; inspect the conversation before sending a new request")
                history = json.loads(row["history"])
                created = now_ms()
                db.execute("INSERT INTO requests(owner,conversation,id,message,status,reply,created_at) VALUES (?,?,?,?,'pending',NULL,?)", (*key, message, created))
            try:
                reply, history = runner(history, message)
                if not isinstance(reply, str) or not reply.strip() or not isinstance(history, list):
                    raise RuntimeError("Agent returned an invalid result")
                history = history[-24:]
                while history and history[0].get("role") != "user":
                    history.pop(0)
                with self._db() as db:
                    db.execute("UPDATE conversations SET history=? WHERE owner=? AND id=?", (json.dumps(history), owner, conversation))
                    self._archive(db, owner, conversation, request_id, message, reply, created)
                    db.execute("UPDATE requests SET status='done',reply=? WHERE owner=? AND conversation=? AND id=?", (reply, *key))
                return reply
            except Exception:
                with self._db() as db:
                    db.execute("UPDATE requests SET status='failed' WHERE owner=? AND conversation=? AND id=?", key)
                raise
