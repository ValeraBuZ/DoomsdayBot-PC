import unittest
from types import SimpleNamespace

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

    def test_rejected_radar_marker_does_not_block_idle_completion(self):
        bot = AutoClicker.__new__(AutoClicker)
        guard = {"uid": "guard"}
        blocker = {
            "uid": "marker",
            "group": "Radar",
            "description": "False radar marker",
            "prevents_idle_completion": True,
        }
        bot.input_backend = "pyautogui"
        bot.search_images = [guard, blocker]
        bot.routine_idle_confirmation_count = 0
        bot.routine_idle_guard_visible = False
        bot.routine_radar_confirmed_marker_keys = set()
        bot._is_active = lambda _image: True
        bot._locate_image = lambda image: (
            SimpleNamespace(x=640, y=360),
            (620, 340, 40, 40),
            0.8,
        )
        bot._validate_detected_match = lambda _image, _bbox: (False, "color")

        task = {
            "id": "radar_rewards",
            "group": "Radar",
            "complete_when_idle": True,
            "idle_completion_guard_uid": "guard",
            "idle_confirmations": 1,
        }

        self.assertTrue(bot._routine_idle_completion_ready(task))
        self.assertTrue(bot.routine_idle_guard_visible)


if __name__ == "__main__":
    unittest.main()
