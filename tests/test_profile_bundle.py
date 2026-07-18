import json
from pathlib import Path
import unittest
import uuid
import zipfile

import cv2
import numpy as np


class ProfileBundleTests(unittest.TestCase):
    def test_gathering_boost_templates_exclude_inventory_counts(self):
        profile_path = Path(__file__).resolve().parents[1] / "profiles" / "BuZzbot_PC_1280x720.zip"
        namespace = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
        boost_uids = {
            str(uuid.uuid5(namespace, "gathering_boost:boost_8h")),
            str(uuid.uuid5(namespace, "gathering_boost:boost_24h")),
        }

        with zipfile.ZipFile(profile_path) as archive:
            manifest = json.loads(archive.read("profile.json"))
            images = {image["uid"]: image for image in manifest["images"]}
            for uid in boost_uids:
                encoded = np.frombuffer(archive.read(images[uid]["path"]), dtype=np.uint8)
                template = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                self.assertIsNotNone(template)
                self.assertLessEqual(template.shape[0], 82)

            boost_24h_uid = str(uuid.uuid5(namespace, "gathering_boost:boost_24h"))
            self.assertTrue(images[boost_24h_uid]["allow_higher_setting_fallback"])

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

    def test_reported_routines_have_safe_runtime_metadata(self):
        profile_path = Path(__file__).resolve().parents[1] / "profiles" / "BuZzbot_PC_1280x720.zip"
        namespace = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
        with zipfile.ZipFile(profile_path) as archive:
            manifest = json.loads(archive.read("profile.json"))

        self.assertEqual(manifest["app_version"], "3.2.3")
        tasks = {task["id"]: task for task in manifest["routine_tasks"]}
        images = {image["uid"]: image for image in manifest["images"]}
        donation = tasks["alliance_donations"]
        self.assertGreaterEqual(donation["timeout_seconds"], 30.0)
        self.assertEqual(donation["completion_runtime_step"], "all_projects_checked")

        project_uid = str(
            uuid.uuid5(namespace, "alliance_donations:select_project_research")
        )
        hospital_uid = str(uuid.uuid5(namespace, "heal:open_wounded"))
        zombie_attack_uid = str(uuid.uuid5(namespace, "zombie_hunt:attack"))
        radar_attack_uid = str(uuid.uuid5(namespace, "radar:attack_zombie"))
        self.assertLessEqual(images[project_uid]["confidence"], 0.74)
        self.assertTrue(images[hospital_uid]["grayscale"])
        self.assertLessEqual(images[hospital_uid]["confidence"], 0.74)
        self.assertEqual(images[zombie_attack_uid]["action"], "zombie_attack")
        self.assertEqual(images[radar_attack_uid]["action"], "zombie_attack")


if __name__ == "__main__":
    unittest.main()
