"""Validate module entrypoints without contacting Telegram or Groq."""
import importlib
import os
import unittest
from unittest.mock import patch

class PackageImportTests(unittest.TestCase):
    def test_telegram_and_agent_package_imports(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-not-a-real-key", "ALLOWED_USER_IDS": "123", "GH_REPO": ""}, clear=True):
            bot = importlib.import_module("backend.telegram.bot")
            self.assertTrue(callable(bot.main))
            self.assertTrue(callable(bot.agent.run))

    def test_api_scaffold_exposes_no_data_routes(self):
        app = importlib.import_module("backend.app.main").app
        self.assertEqual([], app.routes)
