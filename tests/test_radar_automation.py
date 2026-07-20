import unittest

import numpy as np

from buzzbot_app import AutoClicker


class RadarAutomationTests(unittest.TestCase):
    def test_radar_checkbox_opens_radar_from_settlement(self):
        bot = AutoClicker.__new__(AutoClicker)
        bot.routine_completed_steps = set()
        bot._capture_screen_bgr = lambda force=False: (
            np.zeros((720, 1280, 3), dtype=np.uint8),
            (0, 0),
        )
        bot._template_uid_is_visible = lambda _uid: False
        bot._is_settlement_screen_visible = lambda: True
        calls = []

        def tap_radar(target, label, runtime_step, marker=False):
            calls.append((target, label, runtime_step, marker))
            return True

        bot._tap_radar_fallback = tap_radar
        task = {
            "id": "radar_quick",
            "settings": {"visual_fallback": True},
        }

        self.assertTrue(bot._try_radar_visual_fallback(task))
        self.assertEqual(calls[0][0], (110, 448))
        self.assertEqual(calls[0][2], "radar_open")
        self.assertFalse(calls[0][3])


if __name__ == "__main__":
    unittest.main()
