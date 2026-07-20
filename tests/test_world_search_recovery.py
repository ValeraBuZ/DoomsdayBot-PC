import threading
import unittest
from types import SimpleNamespace

from buzzbot_app import AutoClicker


class FakeAdbClient:
    def __init__(self):
        self.taps = []
        self.keys = []

    def tap(self, x, y):
        self.taps.append((x, y))

    def keyevent(self, keycode):
        self.keys.append(keycode)


class WorldSearchRecoveryTests(unittest.TestCase):
    def make_bot(self):
        bot = AutoClicker.__new__(AutoClicker)
        bot.input_backend = "adb"
        bot.adb_client = FakeAdbClient()
        bot.current_routine_task_id = "food"
        bot.stop_event = threading.Event()
        bot.get_display_profile = lambda: SimpleNamespace(scale_x=1.0, scale_y=1.0)
        bot._is_main_screen_visible = lambda: True
        bot._is_settlement_screen_visible = lambda: False
        bot._return_to_main_screen = lambda **kwargs: True
        bot._interruptible_sleep = lambda _seconds: None
        bot._invalidate_capture = lambda: None
        bot.set_status_message = lambda *args, **kwargs: None
        return bot

    def test_search_is_reported_only_after_panel_confirmation(self):
        bot = self.make_bot()
        checks = iter((False, True))
        bot._world_search_panel_visible = lambda: next(checks, True)

        self.assertTrue(bot._prepare_world_search_screen())
        self.assertEqual(bot.adb_client.taps, [(43, 447)])
        self.assertEqual(bot.adb_client.keys, [])

    def test_unconfirmed_search_is_retried_safely(self):
        bot = self.make_bot()
        checks = iter((False, False, False, False, False, False, True))
        bot._world_search_panel_visible = lambda: next(checks, True)

        self.assertTrue(bot._prepare_world_search_screen())
        self.assertEqual(bot.adb_client.taps, [(43, 447), (43, 447)])
        self.assertEqual(bot.adb_client.keys, [4])

    def test_new_hunt_pass_clears_only_its_stale_coordinate_blocks(self):
        bot = self.make_bot()
        bot.search_images = [
            {"uid": "zombie-search", "path": "zombie.png", "group": "Убийство зомби"},
            {"uid": "food-search", "path": "food.png", "group": "Сбор еды"},
        ]
        bot.blocked_coords = {
            ("zombie-search", 640, 352): 999.0,
            ("food-search", 640, 352): 999.0,
        }

        bot._clear_routine_coordinate_blocks(
            {"id": "zombie_hunt", "group": "Убийство зомби"}
        )

        self.assertNotIn(("zombie-search", 640, 352), bot.blocked_coords)
        self.assertIn(("food-search", 640, 352), bot.blocked_coords)


if __name__ == "__main__":
    unittest.main()
