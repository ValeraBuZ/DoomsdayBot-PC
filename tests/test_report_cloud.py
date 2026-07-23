import json
from pathlib import Path
import tempfile
import unittest

from buzzbot.report_cloud import (
    ReportCloudSettings,
    delete_report_after_review,
    load_report_cloud_settings,
    report_inbox,
    save_report_cloud_settings,
    sync_folder_provider,
    upload_report_to_sync_folder,
)


class ReportCloudTests(unittest.TestCase):
    def test_recognizes_cloud_root_and_its_subfolders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Google Drive" / "My Drive"
            child = root / "Reports"
            child.mkdir(parents=True)

            self.assertEqual(sync_folder_provider(child, [root]), "Google Drive")
            self.assertIsNone(sync_folder_provider(Path(temp_dir), [root]))

    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            settings = ReportCloudSettings(True, temp_dir, 'Farm/PC:*?')

            saved = save_report_cloud_settings(settings, path)
            loaded = load_report_cloud_settings(path)

            self.assertEqual(saved, loaded)
            self.assertEqual(loaded.device_name, "Farm_PC_")
            self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["enabled"])

    def test_upload_moves_report_atomically_to_device_inbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "report.zip"
            source.write_bytes(b"report")
            cloud = root / "cloud"
            cloud.mkdir()
            settings = ReportCloudSettings(True, str(cloud), "PC-1")

            uploaded = upload_report_to_sync_folder(source, settings)

            self.assertFalse(source.exists())
            self.assertEqual(uploaded.parent, report_inbox(settings))
            self.assertEqual(uploaded.read_bytes(), b"report")
            self.assertFalse(list(uploaded.parent.glob("*.uploading")))

            self.assertTrue(delete_report_after_review(uploaded, settings))
            self.assertFalse(uploaded.exists())

    def test_failed_upload_keeps_local_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "report.zip"
            source.write_bytes(b"report")
            missing = Path(temp_dir) / "missing-cloud"
            settings = ReportCloudSettings(True, str(missing), "PC-1")

            with self.assertRaises(FileNotFoundError):
                upload_report_to_sync_folder(source, settings)

            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
