"""Validate module entrypoints without contacting Telegram or Groq."""
import importlib
import os
import unittest
from unittest.mock import patch

class PackageImportTests(unittest.TestCase):
    def test_telegram_and_agent_package_imports(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-not-a-real-key", "ALLOWED_USER_IDS": "123", "GH_REPO": ""}, clear=True):
            bot = importlib.import_module("backend.atlas.telegram.bot")
            self.assertTrue(callable(bot.main))
            self.assertTrue(callable(bot.agent.run))

    def test_android_api_routes_are_registered(self):
        app = importlib.import_module("backend.atlas.app.main").app
        self.assertTrue({"/api/v1/health", "/api/v1/chat", "/api/v1/memory", "/api/v1/agent", "/api/v1/files"}.issubset({route.path for route in app.routes}))

class BackendSeparationTests(unittest.TestCase):
    def test_configuration_and_seed_paths_survive_move(self):
        from pathlib import Path
        from backend.atlas.app import config
        from backend.atlas.app.services import memory_service
        from backend.server import termux_service

        root = Path(__file__).resolve().parents[3]
        self.assertEqual(root / "backend", config.BACKEND_DIR)
        self.assertEqual(root / "backend/atlas/seed", config.SEED_DIR)
        self.assertEqual(config.SEED_DIR, memory_service.SEED_DIR)
        self.assertTrue((config.SEED_DIR / "agent.md").is_file())
        self.assertEqual(root, termux_service.ROOT)

    def test_service_entrypoint(self):
        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        result = subprocess.run(
            [sys.executable, "-m", "backend.server.termux_service", "--help"],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("install", result.stdout)
