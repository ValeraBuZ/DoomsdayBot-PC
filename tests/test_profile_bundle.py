import json
from pathlib import Path
import unittest
import uuid
import zipfile


class ProfileBundleTests(unittest.TestCase):
    def test_portable_profile_contains_startup_and_radar_recovery(self):
        profile_path = Path(__file__).resolve().parents[1] / "profiles" / "BuZzbot_PC_1280x720.zip"
        namespace = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
        expected = {
            str(uuid.uuid5(namespace, "system:beast_taming_close")),
            str(uuid.uuid5(namespace, "system:google_play_cancel")),
            str(uuid.uuid5(namespace, "radar:close_region_search")),
        }

        with zipfile.ZipFile(profile_path) as archive:
            manifest = json.loads(archive.read("profile.json"))
            images = {image["uid"]: image for image in manifest["images"]}
            self.assertTrue(expected.issubset(images))
            for uid in expected:
                self.assertIn(images[uid]["path"], archive.namelist())
            google_uid = str(uuid.uuid5(namespace, "system:google_play_cancel"))
            self.assertGreaterEqual(images[google_uid]["delay"], 8.0)

    def test_march_templates_require_screen_change_confirmation(self):
        profile_path = Path(__file__).resolve().parents[1] / "profiles" / "BuZzbot_PC_1280x720.zip"
        with zipfile.ZipFile(profile_path) as archive:
            manifest = json.loads(archive.read("profile.json"))

        march_images = [
            image for image in manifest["images"]
            if image.get("runtime_step") == "march"
        ]
        self.assertTrue(march_images)
        self.assertTrue(all(image.get("confirm_disappears") for image in march_images))

    def test_collective_no_result_is_observed_but_never_clicked(self):
        profile_path = Path(__file__).resolve().parents[1] / "profiles" / "BuZzbot_PC_1280x720.zip"
        namespace = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
        no_result_uid = str(uuid.uuid5(namespace, "collective_mind:no_result"))
        search_uid = str(uuid.uuid5(namespace, "collective_mind:search"))

        with zipfile.ZipFile(profile_path) as archive:
            manifest = json.loads(archive.read("profile.json"))
        images = {image["uid"]: image for image in manifest["images"]}

        self.assertFalse(images[no_result_uid]["enabled"])
        self.assertTrue(images[no_result_uid]["observer_only"])
        self.assertEqual(images[search_uid]["no_result_template_uid"], no_result_uid)


if __name__ == "__main__":
    unittest.main()
