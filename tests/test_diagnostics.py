import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from doomsdaybot.diagnostics import create_diagnostic_report, redact_config


class DiagnosticReportTests(unittest.TestCase):
    def test_sensitive_values_are_redacted(self):
        value = redact_config({"password": "secret", "contact": "user@example.com"})
        self.assertEqual(value["password"], "<redacted>")
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
                "2026 - DoomsdayBot - ERROR - user@example.com failed\n",
                encoding="utf-8",
            )
            report = create_diagnostic_report(
                root,
                app_version="test",
                config_path=config_path,
                runtime_state={"adb_serial": "emulator-5560"},
            )
            with zipfile.ZipFile(report) as archive:
                names = set(archive.namelist())
                self.assertIn("report.txt", names)
                self.assertIn("installation_checklist.txt", names)
                self.assertIn("config_sanitized.json", names)
                self.assertIn("logs/bot.log.txt", names)
                config = archive.read("config_sanitized.json").decode("utf-8")
                logs = archive.read("logs/bot.log.txt").decode("utf-8")
                missing = archive.read("missing_templates.txt").decode("utf-8")
            self.assertNotIn("must-not-leak", config)
            self.assertNotIn("user@example.com", logs)
            self.assertIn("img/missing.png", missing)


if __name__ == "__main__":
    unittest.main()
