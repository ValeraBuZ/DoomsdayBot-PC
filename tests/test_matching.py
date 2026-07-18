import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from buzzbot.matching import (
    TemplateCache,
    detect_radar_card_action_target,
    detect_radar_notification_targets,
    detect_radar_world_action_target,
    healing_auto_fill_is_checked,
    imread_unicode,
    zombie_camp_checkbox_is_checked,
)


class UnicodeImageReadTests(unittest.TestCase):
    def test_reads_png_from_non_ascii_windows_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "Русские шаблоны"
            image_dir.mkdir()
            image_path = image_dir / "кнопка.png"
            source = np.full((12, 18, 3), (15, 80, 220), dtype=np.uint8)
            success, encoded = cv2.imencode(".png", source)
            self.assertTrue(success)
            encoded.tofile(image_path)

            color = imread_unicode(image_path)
            gray = TemplateCache().get_gray(str(image_path))

            self.assertEqual(color.shape, source.shape)
            self.assertEqual(gray.shape, source.shape[:2])

    def test_missing_image_returns_none(self):
        self.assertIsNone(imread_unicode("missing-template.png"))


class DynamicGameControlTests(unittest.TestCase):
    def test_detects_radar_notification_dots_and_targets_the_markers(self):
        frame = np.full((720, 1280, 3), (55, 70, 75), dtype=np.uint8)
        cv2.circle(frame, (700, 200), 8, (10, 20, 200), thickness=-1)
        cv2.circle(frame, (720, 325), 8, (10, 20, 200), thickness=-1)

        self.assertEqual(
            detect_radar_notification_targets(frame),
            [(676, 230), (696, 356)],
        )

    def test_detects_enabled_radar_card_and_world_buttons(self):
        frame = np.full((720, 1280, 3), (45, 55, 65), dtype=np.uint8)
        self.assertIsNone(detect_radar_card_action_target(frame))
        self.assertIsNone(detect_radar_world_action_target(frame))

        cv2.rectangle(frame, (112, 597), (376, 645), (25, 185, 245), thickness=-1)
        cv2.rectangle(frame, (855, 496), (1081, 543), (25, 185, 245), thickness=-1)
        self.assertEqual(detect_radar_card_action_target(frame), (244, 621))
        world_target = detect_radar_world_action_target(frame)
        self.assertIsNotNone(world_target)
        self.assertTrue(940 <= world_target[0] <= 990)
        self.assertTrue(510 <= world_target[1] <= 535)

    def test_detects_only_checked_game_options(self):
        frame = np.full((720, 1280, 3), (35, 45, 55), dtype=np.uint8)
        self.assertFalse(zombie_camp_checkbox_is_checked(frame))
        self.assertFalse(healing_auto_fill_is_checked(frame))

        cv2.line(frame, (812, 514), (818, 523), (20, 210, 80), thickness=3)
        cv2.line(frame, (818, 523), (828, 509), (20, 210, 80), thickness=3)
        cv2.line(frame, (805, 676), (810, 683), (220, 220, 220), thickness=3)
        cv2.line(frame, (810, 683), (820, 670), (220, 220, 220), thickness=3)
        self.assertTrue(zombie_camp_checkbox_is_checked(frame))
        self.assertTrue(healing_auto_fill_is_checked(frame))


if __name__ == "__main__":
    unittest.main()
