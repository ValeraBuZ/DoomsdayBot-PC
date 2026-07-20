import unittest

from buzzbot.accounts import (
    apply_tasks,
    default_account_profiles,
    extract_android_google_accounts,
    extract_google_accounts,
    mask_google_account,
    next_enabled_account,
    normalize_account_profiles,
    requires_google_reauthentication,
    snapshot_tasks,
)
from buzzbot.routines import default_routine_tasks


class AccountProfileTests(unittest.TestCase):
    def test_extracts_unique_google_accounts_from_android_dump(self):
        account_dump = """
        Account {name=person@example.com, type=com.google}
        Account {name=other@example.com, type=com.google}
        Account {name=person@example.com, type=com.google}
        Account {name=local, type=com.example}
        """
        self.assertEqual(
            extract_android_google_accounts(account_dump),
            ["person@example.com", "other@example.com"],
        )

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
            {
                "id": "a",
                "name": "A",
                "chooser_index": 0,
                "google_login": " person@example.com ",
                "auto_login": True,
            },
            {"id": "b", "name": "B", "chooser_index": 99},
        ])
        self.assertEqual(profiles[0]["chooser_index"], 1)
        self.assertEqual(profiles[1]["chooser_index"], 20)
        self.assertEqual(profiles[0]["google_login"], "person@example.com")
        self.assertTrue(profiles[0]["auto_login"])

    def test_google_reauthentication_is_detected(self):
        self.assertTrue(requires_google_reauthentication('<node text="Подтвердите свою личность" />'))
        self.assertTrue(requires_google_reauthentication('<node text="Verify it\'s you" />'))
        self.assertFalse(requires_google_reauthentication('<node text="Doomsday: Last Survivors" />'))

    def test_google_accounts_are_extracted_in_chooser_order(self):
        xml = (
            '<hierarchy><node text="First" content-desc="first@example.com" />'
            '<node text="second@example.com" />'
            '<node text="FIRST@example.com" /></hierarchy>'
        )
        self.assertEqual(extract_google_accounts(xml), [
            {"chooser_index": 1, "email": "first@example.com"},
            {"chooser_index": 2, "email": "second@example.com"},
        ])

    def test_google_account_mask_hides_local_part(self):
        self.assertEqual(mask_google_account("person@example.com"), "p*****@example.com")


if __name__ == "__main__":
    unittest.main()
