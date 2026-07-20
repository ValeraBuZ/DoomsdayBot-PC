import threading
import unittest
from types import SimpleNamespace

from buzzbot.routines import routine_march_context_key
from buzzbot_app import AutoClicker


class FakeAdbClient:
    def __init__(self):
        self.taps = []

    def tap(self, x, y):
        self.taps.append((int(x), int(y)))


class ZombieSearchTests(unittest.TestCase):
    def make_bot(self, fallback_levels=3):
        bot = AutoClicker.__new__(AutoClicker)
        bot.input_backend = "adb"
        bot.adb_serial = "emulator-5564"
        bot.current_account_id = "account-a"
        bot.adb_client = FakeAdbClient()
        bot.stop_event = threading.Event()
        bot.stop_hotkey_pressed = False
        bot.sleep_found = 0.8
        bot.zombie_level_restore = {}
        bot.get_display_profile = lambda: SimpleNamespace(
            width=1280,
            height=720,
            scale_x=1.0,
            scale_y=1.0,
        )
        bot._current_task_settings = lambda: {"fallback_levels": fallback_levels}
        bot._resource_result_level_rejected = lambda _image: False
        bot._interruptible_sleep = lambda _seconds: None
        bot._invalidate_capture = lambda: None
        bot.set_status_message = lambda *_args, **_kwargs: None
        bot.save_config = lambda: None
        return bot

    @staticmethod
    def search_image():
        return {
            "action": "zombie_search",
            "click_offset": (0, 0),
            "numbers": [],
            "delay": 0.0,
            "last_used": 0.0,
        }

    def test_tries_each_lower_level_until_zombie_is_found(self):
        bot = self.make_bot(fallback_levels=3)
        visible = iter((True, True, False))
        bot._locate_image = lambda _image: (
            (SimpleNamespace(x=640, y=620), None, 0.9)
            if next(visible)
            else (None, None, 0.0)
        )

        result = bot._execute_action(self.search_image(), SimpleNamespace(x=640, y=620))

        self.assertTrue(result)
        self.assertEqual(
            bot.adb_client.taps,
            [
                (640, 620),
                (494, 544),
                (640, 620),
                (494, 544),
                (640, 620),
                (640, 353),
            ],
        )
        context = routine_march_context_key("adb", "emulator-5564", "account-a")
        self.assertEqual(bot.zombie_level_restore[context], 2)

    def test_restores_starting_level_when_all_fallbacks_are_empty(self):
        bot = self.make_bot(fallback_levels=3)
        bot._locate_image = lambda _image: (SimpleNamespace(x=640, y=620), None, 0.9)

        result = bot._execute_action(self.search_image(), SimpleNamespace(x=640, y=620))

        self.assertTrue(result)
        self.assertEqual(bot.adb_client.taps.count((494, 544)), 3)
        self.assertEqual(bot.adb_client.taps.count((784, 544)), 3)
        self.assertNotIn((640, 353), bot.adb_client.taps)
        self.assertEqual(bot.zombie_level_restore, {})

    def test_restores_previous_offset_before_the_next_hunt(self):
        bot = self.make_bot(fallback_levels=3)
        context = routine_march_context_key("adb", "emulator-5564", "account-a")
        bot.zombie_level_restore[context] = 2
        bot._locate_image = lambda _image: (None, None, 0.0)

        result = bot._execute_action(self.search_image(), SimpleNamespace(x=640, y=620))

        self.assertTrue(result)
        self.assertEqual(
            bot.adb_client.taps,
            [(784, 544), (784, 544), (640, 620), (640, 353)],
        )
        self.assertEqual(bot.zombie_level_restore, {})


if __name__ == "__main__":
    unittest.main()
