import threading
import unittest

import numpy as np

from buzzbot_app import AutoClicker


class FakeHealingAdbClient:
    def __init__(self, fail_row=None):
        self.fail_row = fail_row
        self.editor_open = False
        self.row_taps = 0
        self.taps = []
        self.inputs = []
        self.clear_calls = 0
        self.unsafe_ok_taps = 0

    def tap(self, x, y):
        self.taps.append((x, y))
        if x == 1085 and y in {173, 263, 353, 443}:
            self.row_taps += 1
            self.editor_open = self.row_taps != self.fail_row
        elif (x, y) == (1198, 669):
            if not self.editor_open:
                self.unsafe_ok_taps += 1
            self.editor_open = False

    def clear_focused_text(self, _max_characters):
        self.clear_calls += 1

    def input_text(self, value):
        self.inputs.append(str(value))

    def keyevent(self, _keycode):
        self.editor_open = False


class HealingWorkflowTests(unittest.TestCase):
    def make_bot(self, fail_row=None):
        bot = AutoClicker.__new__(AutoClicker)
        bot.input_backend = "adb"
        bot.adb_client = FakeHealingAdbClient(fail_row=fail_row)
        bot.stop_event = threading.Event()
        bot.stop_hotkey_pressed = False
        bot._invalidate_capture = lambda: None
        bot._interruptible_sleep = lambda _seconds: None
        bot.set_status_message = lambda *args, **kwargs: None

        def capture_screen_bgr(force=False):
            frame = np.full((720, 1280, 3), (35, 45, 55), dtype=np.uint8)
            if bot.adb_client.editor_open:
                frame[616:720, :] = (250, 250, 250)
            return frame, (0, 0)

        bot._capture_screen_bgr = capture_screen_bgr
        initial_frame, _origin = capture_screen_bgr(force=True)
        return bot, initial_frame

    def test_enters_four_quotas_only_while_editor_is_visible(self):
        bot, frame = self.make_bot()

        self.assertTrue(bot._configure_healing_troop_count(2000, frame))
        self.assertEqual(bot.adb_client.inputs, ["500", "500", "500", "500"])
        self.assertEqual(bot.adb_client.clear_calls, 4)
        self.assertEqual(bot.adb_client.unsafe_ok_taps, 0)

    def test_missing_editor_aborts_without_blind_ok_tap(self):
        bot, frame = self.make_bot(fail_row=2)

        self.assertFalse(bot._configure_healing_troop_count(2000, frame))
        self.assertEqual(bot.adb_client.inputs, ["500"])
        self.assertEqual(bot.adb_client.unsafe_ok_taps, 0)


if __name__ == "__main__":
    unittest.main()
