import subprocess
import tempfile
import unittest
from pathlib import Path
from android_smoke_diagnostics import collect_diagnostics


class DiagnosticsTests(unittest.TestCase):
    def test_closed_webview_still_captures_device_and_host_evidence(self):
        class Closed:
            events = [{'method': 'disconnected'}]
            def evaluate(self, expression):
                raise RuntimeError('socket is already closed')
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, b'evidence', b'')
        with tempfile.TemporaryDirectory() as folder:
            errors = collect_diagnostics(folder, Closed(), run)
            self.assertEqual(4, len(errors))
            for name in ['webview-events.json', 'adb-devices.txt', 'logcat.txt', 'screen.png', 'host-memory.txt', 'diagnostic-errors.json']:
                self.assertTrue((Path(folder) / name).exists(), name)
            self.assertIn(['adb', 'logcat', '-d'], calls)

    def test_dead_emulator_does_not_prevent_host_diagnostics_or_raise(self):
        def run(args, **kwargs):
            if args[0] == 'adb':
                raise subprocess.TimeoutExpired(args, 15)
            return subprocess.CompletedProcess(args, 0, b'host evidence', b'')
        with tempfile.TemporaryDirectory() as folder:
            errors = collect_diagnostics(folder, run=run)
            self.assertEqual(4, len(errors))
            self.assertEqual('host evidence', (Path(folder) / 'host-memory.txt').read_text())
            self.assertFalse((Path(folder) / 'screen.png').exists())

    def test_unwritable_destination_does_not_replace_original_failure(self):
        with tempfile.NamedTemporaryFile() as destination:
            self.assertEqual([], collect_diagnostics(destination.name))


if __name__ == '__main__':
    unittest.main()
