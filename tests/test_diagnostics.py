import json
import threading
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from buzzbot.diagnostics import create_diagnostic_report, redact_config
from buzzbot_app import AutoClicker


class DiagnosticReportTests(unittest.TestCase):
    def test_sensitive_values_are_redacted(self):
        value = redact_config(
            {
                "password": "secret",
                "google_login": "+79990000000",
                "contact": "user@example.com",
            }
        )
        self.assertEqual(value["password"], "<redacted>")
        self.assertEqual(value["google_login"], "<redacted>")
        self.assertEqual(value["contact"], "<email>")

    def test_report_contains_logs_config_and_installation_checklist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "img").mkdir()
            (root / "img" / "ok.png").write_bytes(b"png")
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "images": [{"path": "img/ok.png"}, {"path": "img/missing.png"}],
                        "routine_tasks": [{"id": "food"}],
                        "password": "must-not-leak",
                    }
                ),
                encoding="utf-8",
            )
            (root / "bot.log").write_text(
                "2026 - BuZzbot - ERROR - user@example.com failed\n",
                encoding="utf-8",
            )
            external_log = root / "runtime.log"
            external_log.write_text("runtime action trace\n", encoding="utf-8")
            report = create_diagnostic_report(
                root,
                app_version="test",
                config_path=config_path,
                runtime_state={"adb_serial": "emulator-5560"},
                log_paths=[external_log],
                screenshot_png=b"fake-png",
            )
            self.assertTrue(report.name.startswith("BuZzbot_report_"))
            with zipfile.ZipFile(report) as archive:
                names = set(archive.namelist())
                self.assertIn("report.txt", names)
                self.assertIn("installation_checklist.txt", names)
                self.assertIn("config_sanitized.json", names)
                self.assertIn("logs/bot.log.txt", names)
                self.assertIn("logs/runtime.log.txt", names)
                self.assertIn("current_screen.png", names)
                config = archive.read("config_sanitized.json").decode("utf-8")
                logs = archive.read("logs/bot.log.txt").decode("utf-8")
                missing = archive.read("missing_templates.txt").decode("utf-8")
                screenshot = archive.read("current_screen.png")
            self.assertNotIn("must-not-leak", config)
            self.assertNotIn("user@example.com", logs)
            self.assertIn("img/missing.png", missing)
            self.assertEqual(screenshot, b"fake-png")

    @patch("buzzbot.diagnostics._run_capture")
    def test_supplied_adb_status_avoids_live_adb_command(self, run_capture):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.json"
            config_path.write_text("{}", encoding="utf-8")

            report = create_diagnostic_report(
                root,
                app_version="test",
                config_path=config_path,
                runtime_state={"adb_serial": "127.0.0.1:5561"},
                adb_path="adb.exe",
                adb_devices_text="Живая проверка ADB пропущена",
            )

            run_capture.assert_not_called()
            with zipfile.ZipFile(report) as archive:
                text = archive.read("report.txt").decode("utf-8")
            self.assertIn("Живая проверка ADB пропущена", text)

    def test_cached_screenshot_is_encoded_without_adb_call(self):
        bot = AutoClicker.__new__(AutoClicker)
        bot._adb_capture_lock = threading.RLock()
        bot._adb_frame_cache = np.full((720, 1280, 3), (12, 34, 56), dtype=np.uint8)

        payload = bot._cached_diagnostic_screenshot_png()

        frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(frame.shape, (720, 1280, 3))
        self.assertEqual(tuple(frame[0, 0]), (12, 34, 56))


if __name__ == "__main__":
    unittest.main()
