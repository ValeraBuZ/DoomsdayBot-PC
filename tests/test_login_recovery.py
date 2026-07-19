import unittest

from buzzbot_app import AutoClicker, GAME_PACKAGE


class FakeAdbClient:
    def __init__(self):
        self.calls = []

    def force_stop_package(self, package):
        self.calls.append(("stop", package))

    def launch_package(self, package):
        self.calls.append(("launch", package))


class LoginRecoveryTests(unittest.TestCase):
    def test_stalled_login_restarts_the_game_at_most_twice(self):
        bot = AutoClicker.__new__(AutoClicker)
        bot.input_backend = "adb"
        bot.adb_client = FakeAdbClient()
        bot.adb_serial = "emulator-5558"
        bot.routine_login_restart_count = 0
        bot._adb_frame_cache = object()
        bot._adb_frame_timestamp = 10.0
        bot.blocked_coords = {(10, 20): 30.0}
        bot.routine_completed_steps = {"banner"}
        bot.routine_idle_confirmation_count = 2
        bot.routine_task_started_at = 0.0
        bot.routine_last_action_time = 0.0
        bot._interruptible_sleep = lambda seconds: None
        bot.set_status_message = lambda *args, **kwargs: None

        self.assertTrue(bot._restart_game_for_login())
        self.assertEqual(
            bot.adb_client.calls,
            [("stop", GAME_PACKAGE), ("launch", GAME_PACKAGE)],
        )
        self.assertIsNone(bot._adb_frame_cache)
        self.assertEqual(bot.blocked_coords, {})
        self.assertEqual(bot.routine_completed_steps, set())
        self.assertEqual(bot.routine_idle_confirmation_count, 0)
        self.assertGreater(bot.routine_task_started_at, 0.0)
        self.assertEqual(bot.routine_task_started_at, bot.routine_last_action_time)
        self.assertTrue(bot._restart_game_for_login())
        self.assertEqual(
            bot.adb_client.calls,
            [
                ("stop", GAME_PACKAGE),
                ("launch", GAME_PACKAGE),
                ("stop", GAME_PACKAGE),
                ("launch", GAME_PACKAGE),
            ],
        )
        self.assertFalse(bot._restart_game_for_login())


if __name__ == "__main__":
    unittest.main()
