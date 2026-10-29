"""Android contract integration tests; no real provider requests or credentials."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from backend.app.config import Settings, load_settings
from backend.app.main import create_app
from backend.app.repositories.sessions import SessionRepository, RequestConflict
from backend.app.services import memory_service as memory

TOKEN = "atlas-test-token-" + "x" * 32
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"GH_REPO": ""}, clear=True)
        self.env.start()
        self.settings = Settings(api_token=TOKEN, groq_api_key="test-not-real", data_dir=self.root)
        self.calls = []

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def runner(self, history, text):
        self.calls.append((list(history), text))
        return f"Reply: {text}", history + [{"role": "user", "content": text}, {"role": "assistant", "content": f"Reply: {text}"}]

    @contextmanager
    def client(self, runner=None):
        with TestClient(create_app(self.settings, runner or self.runner), raise_server_exceptions=False) as client:
            yield client

    def payload(self, text="Hello", conversation="android-test", request_id=None):
        return dict(message=text, conversation_id=conversation, request_id=request_id or str(uuid4()))

    def test_all_android_endpoints_require_a_valid_bearer_token(self):
        with self.client() as client:
            for method, path, body in [
                ("GET", "health", None), ("POST", "chat", self.payload()),
                ("GET", "memory", None), ("POST", "memory", {"section": "Projects", "fact": "A fact"}),
                ("GET", "agent", None), ("GET", "files", None),
            ]:
                for auth in ({}, {"Authorization": "Bearer incorrect"}, {"Authorization": "Basic incorrect"}):
                    response = client.request(method, f"/api/v1/{path}", headers=auth, json=body)
                    self.assertEqual(401, response.status_code, response.text)
                    self.assertEqual("Bearer", response.headers["www-authenticate"])
            self.assertEqual([], self.calls)
            self.assertEqual(200, client.get("/docs").status_code)
            self.assertIn("HTTPBearer", client.get("/openapi.json").json()["components"]["securitySchemes"])

    def test_health_profile_and_allowlisted_files_match_android(self):
        with self.client() as client:
            self.assertTrue((self.root / "agent.md").is_file())
            self.assertTrue((self.root / "memory.md").is_file())
            health = client.get("/api/v1/health", headers=HEADERS)
            self.assertEqual(200, health.status_code)
            self.assertEqual("ok", health.json()["status"])
            self.assertGreaterEqual(health.json()["uptime_seconds"], 0)
            profile = client.get("/api/v1/agent", headers=HEADERS).json()
            self.assertEqual("Atlas", profile["name"])
            self.assertTrue(profile["content"])
            (self.root / ".env").write_text("SHOULD_NOT_BE_LISTED=secret")
            (self.root / "private.log").write_text("private")
            listing = client.get("/api/v1/files", headers=HEADERS).json()
            self.assertEqual({"agent.md", "memory.md", "backups"}, {item["name"] for item in listing})
            for item in listing:
                self.assertIn("directory", item)
                self.assertIn("size_bytes", item)
            # An allowlisted filename must still not follow a symlink outside the data directory.
            (self.root / "agent.md").unlink()
            (self.root / "agent.md").symlink_to(self.root / ".env")
            listing = client.get("/api/v1/files", headers=HEADERS).json()
            self.assertNotIn("agent.md", {item["name"] for item in listing})

    def test_chat_persists_context_and_replays_duplicate_after_restart(self):
        first = self.payload("First turn")
        with self.client() as client:
            response = client.post("/api/v1/chat", json=first, headers=HEADERS)
            self.assertEqual({"reply": "Reply: First turn"}, response.json())
            self.assertEqual(200, response.status_code)
        with self.client() as client:
            self.assertEqual(response.json(), client.post("/api/v1/chat", json=first, headers=HEADERS).json())
            self.assertEqual(1, len(self.calls))
            second = client.post("/api/v1/chat", json=self.payload("Second turn"), headers=HEADERS)
            self.assertEqual(200, second.status_code)
            self.assertEqual("First turn", self.calls[-1][0][0]["content"])
            client.post("/api/v1/chat", json=self.payload("Separate", conversation="another"), headers=HEADERS)
            self.assertEqual([], self.calls[-1][0])
            conflict = client.post("/api/v1/chat", json={**first, "message": "Changed"}, headers=HEADERS)
            self.assertEqual(409, conflict.status_code)

    def test_concurrent_duplicate_requests_execute_agent_once(self):
        def slow(history, text):
            time.sleep(0.05)
            return self.runner(history, text)
        body = self.payload()
        with self.client(slow) as client, ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: client.post("/api/v1/chat", json=body, headers=HEADERS), range(2)))
            self.assertEqual([200, 200], [r.status_code for r in responses])
            self.assertEqual(1, len(self.calls))

    def test_memory_saves_deduplicates_and_keeps_stable_ids(self):
        body = dict(section="Projects", fact="Build the Atlas app")
        with self.client() as client:
            saved = client.post("/api/v1/memory", json=body, headers=HEADERS)
            self.assertEqual(200, saved.status_code, saved.text)
            self.assertEqual(body, {k: saved.json()[k] for k in body})
            duplicate = client.post("/api/v1/memory", json=body, headers=HEADERS)
            self.assertEqual(saved.json()["id"], duplicate.json()["id"])
            self.assertIn(saved.json(), client.get("/api/v1/memory", headers=HEADERS).json())
            memory.overwrite_memory("## Projects\n- Another fact\n- Build the Atlas app\n")
            refreshed = client.get("/api/v1/memory", headers=HEADERS).json()
            self.assertEqual(saved.json()["id"], next(x["id"] for x in refreshed if x["fact"] == body["fact"]))

    def test_validation_and_memory_cap_do_not_modify_storage(self):
        with self.client() as client:
            for body in [self.payload(" "), self.payload("x" * 8001), {**self.payload(), "request_id": "bad"}, {**self.payload(), "conversation_id": "../other"}]:
                self.assertEqual(422, client.post("/api/v1/chat", json=body, headers=HEADERS).status_code)
            for body in [dict(section="Unknown", fact="A fact"), dict(section="Projects", fact=" "), dict(section="Projects", fact="x" * 301)]:
                self.assertEqual(422, client.post("/api/v1/memory", json=body, headers=HEADERS).status_code)
            original = "## Projects\n" + "x" * (memory.MAX_MEMORY_CHARS - 22)
            memory.overwrite_memory(original)
            full = client.post("/api/v1/memory", json=dict(section="Projects", fact="A sufficiently long fact to exceed the memory cap"), headers=HEADERS)
            self.assertEqual(409, full.status_code)
            self.assertEqual(original, memory.load_memory())
            self.assertEqual([], self.calls)

    def test_provider_errors_are_mapped_and_failed_requests_are_not_reexecuted(self):
        req = httpx.Request("POST", "https://provider.invalid/chat")
        cases = [
            (RateLimitError("private upstream details", response=httpx.Response(429, request=req), body=None), 429),
            (APIStatusError("private upstream details", response=httpx.Response(500, request=req), body=None), 502),
            (APIConnectionError(request=req), 502),
            (APITimeoutError(request=req), 504),
            (RuntimeError("private upstream details"), 500),
        ]
        for error, status in cases:
            calls = []
            def fail(history, text):
                calls.append(1)
                raise error
            with self.client(fail) as client:
                body = self.payload(conversation=str(uuid4()))
                response = client.post("/api/v1/chat", json=body, headers=HEADERS)
                self.assertEqual(status, response.status_code, response.text)
                if status == 429:
                    self.assertEqual("30", response.headers["Retry-After"])
                self.assertNotIn("private upstream", response.text)
                self.assertEqual(409, client.post("/api/v1/chat", json=body, headers=HEADERS).status_code)
                self.assertEqual(1, len(calls))

    def test_default_bridge_calls_real_agent_loop_with_mocked_provider(self):
        from backend.app.agent import agent
        message = SimpleNamespace(tool_calls=None, content="Provider reply")
        completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        with patch.object(agent, "get_client") as provider:
            provider.return_value.chat.completions.create.return_value = completion
            with TestClient(create_app(self.settings)) as client:
                response = client.post("/api/v1/chat", json=self.payload(), headers=HEADERS)
            self.assertEqual({"reply": "Provider reply"}, response.json())
            self.assertEqual(1, provider.return_value.chat.completions.create.call_count)
            kwargs = provider.return_value.chat.completions.create.call_args.kwargs
            self.assertIn("<memory>", kwargs["messages"][0]["content"])

    def test_model_tool_memory_save_is_visible_in_api(self):
        from backend.app.agent import agent
        tool = SimpleNamespace(id="tool-1", function=SimpleNamespace(name="save_memory", arguments='{"section":"Projects","fact":"Use Kotlin for Atlas"}'))
        messages = [SimpleNamespace(tool_calls=[tool], content=None), SimpleNamespace(tool_calls=None, content="Remembered")]
        with patch.object(agent, "get_client") as provider:
            provider.return_value.chat.completions.create.side_effect = [SimpleNamespace(choices=[SimpleNamespace(message=m)]) for m in messages]
            with TestClient(create_app(self.settings)) as client:
                response = client.post("/api/v1/chat", json=self.payload(), headers=HEADERS)
                self.assertEqual(200, response.status_code)
                self.assertTrue(any(x["fact"] == "Use Kotlin for Atlas" for x in client.get("/api/v1/memory", headers=HEADERS).json()))

    def test_interrupted_request_is_not_replayed_and_owners_are_isolated(self):
        repository = SessionRepository(self.root / "sessions.sqlite3")
        def interrupted(history, text):
            raise SystemExit("simulated process loss")
        with self.assertRaises(SystemExit):
            repository.chat("owner", "test", "req", "Message", interrupted)
        restarted = SessionRepository(repository.path)
        with self.assertRaises(RequestConflict):
            restarted.chat("owner", "test", "req", "Message", self.runner)
        restarted.chat("other-owner", "test", "req", "Message", self.runner)
        self.assertEqual([], self.calls[-1][0])

    def test_configuration_loads_dotenv_before_storage_initialization(self):
        config_dir = self.root / "config"
        config_dir.mkdir()
        data = self.root / "configured-data"
        (config_dir / ".env").write_text(f"ATLAS_API_TOKEN={TOKEN}\nGROQ_API_KEY=test-only\nDATA_DIR={data}\n")
        with patch("backend.app.config.BACKEND_DIR", config_dir):
            with TestClient(create_app(agent_runner=self.runner)) as client:
                self.assertEqual(200, client.get("/api/v1/health", headers=HEADERS).status_code)
                self.assertTrue((data / "agent.md").is_file())
        with self.assertRaises(ValueError):
            Settings(api_token="short", groq_api_key="test")
        with self.assertRaises(ValueError):
            Settings(api_token=TOKEN, groq_api_key="")

if __name__ == "__main__":
    unittest.main()
