import unittest

from buzzbot.accounts import (
    apply_tasks,
    default_account_profiles,
    next_enabled_account,
    normalize_account_profiles,
    requires_google_reauthentication,
    snapshot_tasks,
)
from buzzbot.routines import default_routine_tasks


class AccountProfileTests(unittest.TestCase):
    def test_default_profile_targets_phoenix(self):
        profile = default_account_profiles()[0]
        self.assertEqual(profile["name"], "Phoenix675")
        self.assertEqual(profile["ldplayer_index"], 5)
        self.assertEqual(profile["adb_serial"], "emulator-5564")
        self.assertEqual(profile["chooser_index"], 2)

    def test_profile_keeps_task_selection(self):
        tasks = default_routine_tasks()
        next(task for task in tasks if task["id"] == "food")["enabled"] = False
        profile = default_account_profiles()[0]
        snapshot_tasks(profile, tasks)
        next(task for task in tasks if task["id"] == "food")["enabled"] = True
        apply_tasks(profile, tasks)
        self.assertFalse(next(task for task in tasks if task["id"] == "food")["enabled"])

    def test_rotation_uses_one_enabled_profile_at_a_time(self):
        profiles = normalize_account_profiles([
            {"id": "a", "name": "A", "enabled": True},
            {"id": "b", "name": "B", "enabled": True},
        ])
        self.assertEqual(next_enabled_account(profiles, "a")["id"], "b")
        self.assertEqual(next_enabled_account(profiles, "b")["id"], "a")

    def test_google_chooser_index_is_normalized(self):
        profiles = normalize_account_profiles([
            {"id": "a", "name": "A", "chooser_index": 0},
            {"id": "b", "name": "B", "chooser_index": 99},
        ])
        self.assertEqual(profiles[0]["chooser_index"], 1)
        self.assertEqual(profiles[1]["chooser_index"], 20)

    def test_google_reauthentication_is_detected(self):
        self.assertTrue(requires_google_reauthentication('<node text="Подтвердите свою личность" />'))
        self.assertTrue(requires_google_reauthentication('<node text="Verify it\'s you" />'))
        self.assertFalse(requires_google_reauthentication('<node text="Doomsday: Last Survivors" />'))


if __name__ == "__main__":
    unittest.main()
