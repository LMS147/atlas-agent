"""Complete transcript persistence, compatibility migration, pagination, and deletion safety."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.repositories.sessions import SessionRepository, ConversationMissing

TOKEN = "conversations-test-" + "x" * 32
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"GH_REPO": ""}, clear=True)
        self.env.start()
        self.settings = Settings(TOKEN, "test-only", self.root)
        self.calls = []

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def runner(self, history, text):
        self.calls.append(list(history))
        return "Reply: " + text, history + [{"role": "user", "content": text}, {"role": "assistant", "content": "Reply: " + text}]

    def client(self, runner=None):
        return TestClient(create_app(self.settings, runner or self.runner))

    def create(self, client, title="New chat"):
        response = client.post("/api/v1/conversations", json={"title": title}, headers=HEADERS)
        self.assertEqual(201, response.status_code, response.text)
        return response.json()

    def send(self, client, identifier, text="Hello", request_id=None):
        body = dict(conversation_id=identifier, message=text, request_id=request_id or str(uuid4()))
        return client.post("/api/v1/chat", json=body, headers=HEADERS)

    def test_all_conversation_routes_require_authentication(self):
        with self.client() as client:
            for method, path, body in [
                ("GET", "", None), ("POST", "", {"title": "New"}),
                ("GET", "/some-chat", None), ("PATCH", "/some-chat", {"title": "Renamed"}),
                ("DELETE", "/some-chat", None), ("GET", "/some-chat/messages", None),
            ]:
                for headers in ({}, {"Authorization": "Bearer wrong"}):
                    response = client.request(method, "/api/v1/conversations" + path, json=body, headers=headers)
                    self.assertEqual(401, response.status_code, response.text)

    def test_create_rename_and_isolated_context_survive_restart(self):
        with self.client() as client:
            a, b = self.create(client), self.create(client, "Personal")
            self.assertNotEqual(a["id"], b["id"])
            self.assertEqual(200, self.send(client, a["id"], "Project Alpha").status_code)
            self.assertEqual(200, self.send(client, b["id"], "Personal task").status_code)
            self.assertEqual([[], []], self.calls)
            response = client.patch(f'/api/v1/conversations/{a["id"]}', json={"title": "  Work   projects  "}, headers=HEADERS)
            self.assertEqual("Work projects", response.json()["title"])
        with self.client() as client:
            saved = client.get("/api/v1/conversations", headers=HEADERS).json()
            self.assertEqual({a["id"], b["id"]}, {x["id"] for x in saved})
            self.assertEqual("Work projects", next(x["title"] for x in saved if x["id"] == a["id"]))
            self.assertEqual(200, self.send(client, a["id"], "Another work task").status_code)
            self.assertEqual("Project Alpha", self.calls[-1][0]["content"])
            self.assertNotIn("Personal task", json.dumps(self.calls[-1]))

    def test_full_transcript_exceeds_prompt_window_without_duplicate_replays(self):
        identifier = None
        repeated = str(uuid4())
        with self.client() as client:
            identifier = self.create(client)["id"]
            for number in range(18):
                response = self.send(client, identifier, f"Turn {number}", repeated if number == 0 else None)
                self.assertEqual(200, response.status_code)
            self.assertEqual(200, self.send(client, identifier, "Turn 0", repeated).status_code)
            self.assertEqual(18, len(self.calls))
            self.assertLessEqual(len(self.calls[-1]), 24)
        with self.client() as client:
            page = client.get(f"/api/v1/conversations/{identifier}/messages", headers=HEADERS).json()
            self.assertEqual(36, len(page["items"]))
            self.assertEqual("Turn 0", page["items"][0]["text"])
            self.assertEqual("Reply: Turn 17", page["items"][-1]["text"])
            self.assertFalse(page["has_more"])
            summary = client.get(f"/api/v1/conversations/{identifier}", headers=HEADERS).json()
            self.assertEqual(36, summary["message_count"])

    def test_cursor_pagination_has_no_missing_or_duplicate_messages(self):
        with self.client() as client:
            identifier = self.create(client)["id"]
            for number in range(61):
                self.assertEqual(200, self.send(client, identifier, f"Message {number}").status_code)
            all_items, before = [], None
            while True:
                params = {"limit": 17}
                if before is not None:
                    params["before"] = before
                page = client.get(f"/api/v1/conversations/{identifier}/messages", params=params, headers=HEADERS).json()
                self.assertLessEqual(len(page["items"]), 17)
                all_items = page["items"] + all_items
                if not page["has_more"]:
                    break
                self.assertLess(page["next_before"], before or 10**20)
                before = page["next_before"]
            self.assertEqual(122, len(all_items))
            self.assertEqual(122, len({x["id"] for x in all_items}))
            self.assertEqual(sorted(x["seq"] for x in all_items), [x["seq"] for x in all_items])
            self.assertEqual(422, client.get(f"/api/v1/conversations/{identifier}/messages?limit=101", headers=HEADERS).status_code)

    def test_legacy_request_log_import_is_idempotent_and_keeps_full_history(self):
        path = self.root / "atlas.sqlite3"
        with sqlite3.connect(path) as db:
            db.executescript("""CREATE TABLE conversations(owner TEXT NOT NULL,id TEXT NOT NULL,history TEXT NOT NULL,PRIMARY KEY(owner,id));
                CREATE TABLE requests(owner TEXT NOT NULL,conversation TEXT NOT NULL,id TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL,reply TEXT,PRIMARY KEY(owner,conversation,id));""")
            db.execute("INSERT INTO conversations VALUES ('owner','android-legacy','[]')")
            for number in range(4):
                db.execute("INSERT INTO requests VALUES ('owner','android-legacy',?,?,'done',?)", (str(uuid4()), f"Old turn {number}", f"Old reply {number}"))
        with self.client() as client:
            first = client.get("/api/v1/conversations/android-legacy/messages", headers=HEADERS).json()["items"]
            self.assertEqual(8, len(first))
            self.assertEqual("Old turn 0", first[0]["text"])
        with self.client() as client:
            second = client.get("/api/v1/conversations/android-legacy/messages", headers=HEADERS).json()["items"]
            self.assertEqual(first, second)
            self.assertEqual(1, len(client.get("/api/v1/conversations", headers=HEADERS).json()))

    def test_delete_clears_context_and_blocks_stale_clients_without_erasing_memory(self):
        with self.client() as client:
            identifier = self.create(client)["id"]
            self.send(client, identifier)
            client.post("/api/v1/memory", json={"section": "Projects", "fact": "Keep this shared memory"}, headers=HEADERS)
            memory_before = client.get("/api/v1/memory", headers=HEADERS).json()
            self.assertEqual(204, client.delete(f"/api/v1/conversations/{identifier}", headers=HEADERS).status_code)
            self.assertEqual([], client.get("/api/v1/conversations", headers=HEADERS).json())
            tombstones = client.get("/api/v1/conversations?include_deleted=true", headers=HEADERS).json()
            self.assertTrue(tombstones[0]["deleted"])
            self.assertEqual("", tombstones[0]["preview"])
            self.assertEqual(410, self.send(client, identifier, "Stale client").status_code)
            self.assertEqual(1, len(self.calls))
            self.assertEqual(410, client.get(f"/api/v1/conversations/{identifier}/messages", headers=HEADERS).status_code)
            self.assertEqual(memory_before, client.get("/api/v1/memory", headers=HEADERS).json())
        with self.client() as client:
            self.assertEqual(410, self.send(client, identifier).status_code)

    def test_delete_while_provider_is_running_returns_conflict(self):
        entered, release = threading.Event(), threading.Event()
        def slow(history, text):
            entered.set()
            release.wait(timeout=5)
            return self.runner(history, text)
        with self.client(slow) as client, ThreadPoolExecutor(max_workers=1) as pool:
            identifier = self.create(client)["id"]
            future = pool.submit(self.send, client, identifier)
            try:
                self.assertTrue(entered.wait(timeout=3))
                self.assertEqual(409, client.delete(f"/api/v1/conversations/{identifier}", headers=HEADERS).status_code)
            finally:
                release.set()
            self.assertEqual(200, future.result(timeout=5).status_code)
            self.assertEqual(204, client.delete(f"/api/v1/conversations/{identifier}", headers=HEADERS).status_code)

    def test_owner_scoping_and_title_validation(self):
        repo = SessionRepository(self.root / "private.sqlite3")
        item = repo.create_conversation("alice", "Private")
        self.assertEqual([], repo.list_conversations("bob", True))
        with self.assertRaises(ConversationMissing):
            repo.messages("bob", item["id"])
        with self.client() as client:
            identifier = self.create(client)["id"]
            for title in (" ", "x" * 81):
                self.assertEqual(422, client.patch(f"/api/v1/conversations/{identifier}", json={"title": title}, headers=HEADERS).status_code)
            self.assertEqual(404, client.get("/api/v1/conversations/not-here/messages", headers=HEADERS).status_code)

if __name__ == "__main__":
    unittest.main()
