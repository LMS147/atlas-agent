"""Migration regressions using real seed files and isolated temporary storage."""
import importlib
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

class MemoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATA_DIR": self.temp.name, "GH_REPO": ""})
        self.env.start()
        from backend.app.services import memory_service
        self.memory = importlib.reload(memory_service)
        self.memory.ensure_files()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_seeds_are_found_after_move_and_not_overwritten(self):
        self.assertTrue(self.memory.load_agent().strip())
        self.memory.overwrite_memory("## Projects\n- Keep this fact\n")
        self.memory.ensure_files()
        self.assertIn("Keep this fact", self.memory.load_memory())

    def test_append_persists_deduplicates_and_backs_up(self):
        self.assertEqual("saved", self.memory.append_memory("Projects", "Build the Android companion"))
        self.assertEqual("skipped: already known", self.memory.append_memory("Projects", "Build the Android companion"))
        self.assertIn("Build the Android companion", self.memory.load_memory())
        self.assertTrue(list((Path(self.temp.name) / "backups").glob("memory-*.md")))

    def test_validation_survives_move(self):
        self.assertEqual("rejected: empty", self.memory.append_memory("Projects", " "))
        self.assertIn("too long", self.memory.append_memory("Projects", "x" * 301))
        self.assertEqual("saved", self.memory.append_memory("unknown", "A fact"))
        self.assertIn("## Projects", self.memory.load_memory())

    def test_separate_processes_do_not_lose_memory_writes(self):
        code = (
            "import sys; from backend.app.services import memory_service as memory; "
            "memory.ensure_files(); "
            "assert memory.append_memory('Projects', sys.argv[1]) == 'saved'"
        )
        facts = [f"Concurrent process fact {number}" for number in range(4)]
        processes = [subprocess.Popen([sys.executable, "-c", code, fact]) for fact in facts]
        for process in processes:
            self.assertEqual(0, process.wait(timeout=15))
        text = self.memory.load_memory()
        for fact in facts:
            self.assertEqual(1, text.count(fact))


if __name__ == "__main__":
    unittest.main()
