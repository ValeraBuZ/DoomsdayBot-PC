import unittest

import numpy as np

from buzzbot_app import AutoClicker


class FakeAdbClient:
    def __init__(self, package="com.google.android.gms", ui_xml='<node text="Verify it\'s you" />'):
        self.package = package
        self._ui_xml = ui_xml

    def current_foreground_package(self):
        return self.package

    def ui_xml(self):
        return self._ui_xml


class GoogleCredentialTests(unittest.TestCase):
    def make_switch_bot(self, *, auto_login=False, has_password=False, package="com.google.android.gms"):
        bot = AutoClicker.__new__(AutoClicker)
        bot.account_switch_selected_at = 1.0
        bot.account_switch_auto_login_attempted = False
        bot.input_backend = "adb"
        bot.adb_client = FakeAdbClient(package)
        bot.account_profiles = [
            {
                "id": "main",
                "name": "Main",
                "auto_login": auto_login,
            }
        ]
        bot.account_switch_error = ""
        bot.account_has_saved_password = lambda _account_id: has_password
        bot.fill_google_credential = lambda _account_id, _stage: True
        bot.set_status_message = lambda *_args, **_kwargs: None
        bot.routine_last_action_time = 0.0
        return bot

    def test_google_page_visual_guard_accepts_expected_layout_only(self):
        frame = np.full((600, 1000, 3), (200, 120, 50), dtype=np.uint8)
        frame[int(600 * 0.08):int(600 * 0.93), 200:800] = 255

        self.assertTrue(AutoClicker._google_signin_frame_is_visible(frame))
        self.assertFalse(AutoClicker._google_signin_frame_is_visible(np.zeros_like(frame)))

    def test_saved_password_is_not_used_when_auto_login_is_disabled(self):
        bot = self.make_switch_bot(auto_login=False, has_password=True)

        handled = bot._try_account_switch_saved_password(
            {"id": "__account_switch__", "settings": {"target_account_id": "main", "login_method": "google"}}
        )

        self.assertTrue(handled)
        self.assertTrue(bot.account_switch_auto_login_attempted)
        self.assertIn("отключено", bot.account_switch_error)

    def test_saved_password_is_not_attempted_in_an_unrelated_app(self):
        bot = self.make_switch_bot(auto_login=True, has_password=True, package="com.igg.android.doomsdaylastsurvivors")

        handled = bot._try_account_switch_saved_password(
            {"id": "__account_switch__", "settings": {"target_account_id": "main", "login_method": "google"}}
        )

        self.assertFalse(handled)
        self.assertFalse(bot.account_switch_auto_login_attempted)

    def test_saved_password_waits_until_reauthentication_page_is_visible(self):
        bot = self.make_switch_bot(auto_login=True, has_password=True)
        bot.adb_client._ui_xml = '<node text="Choose an account" />'

        handled = bot._try_account_switch_saved_password(
            {"id": "__account_switch__", "settings": {"target_account_id": "main", "login_method": "google"}}
        )

        self.assertFalse(handled)
        self.assertFalse(bot.account_switch_auto_login_attempted)

    def test_recaptcha_is_never_filled_automatically(self):
        bot = self.make_switch_bot(auto_login=True, has_password=True)
        bot.adb_client._ui_xml = '<node text="Verify it\'s you" /><node text="reCAPTCHA" />'

        handled = bot._try_account_switch_saved_password(
            {"id": "__account_switch__", "settings": {"target_account_id": "main", "login_method": "google"}}
        )

        self.assertTrue(handled)
        self.assertTrue(bot.account_switch_auto_login_attempted)
        self.assertIn("reCAPTCHA", bot.account_switch_error)


if __name__ == "__main__":
    unittest.main()
