from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import cv2
import numpy as np


REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720


def _reference_frame(frame_bgr):
    if frame_bgr is None or not isinstance(frame_bgr, np.ndarray) or frame_bgr.ndim != 3:
        return None, 1.0, 1.0
    height, width = frame_bgr.shape[:2]
    if width <= 0 or height <= 0:
        return None, 1.0, 1.0
    if (width, height) == (REFERENCE_WIDTH, REFERENCE_HEIGHT):
        return frame_bgr, 1.0, 1.0
    resized = cv2.resize(frame_bgr, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
    return resized, width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT


def detect_radar_notification_targets(frame_bgr):
    """Find actionable radar markers by their compact red notification dot."""
    frame, scale_x, scale_y = _reference_frame(frame_bgr)
    if frame is None:
        return []

    blue, green, red = cv2.split(frame)
    blue = blue.astype(np.float32)
    green = green.astype(np.float32)
    red = red.astype(np.float32)
    mask = (
        (red > 120)
        & (red > 2.2 * (green + 1.0))
        & (red > 2.2 * (blue + 1.0))
    ).astype(np.uint8) * 255

    # Exclude the HUD and the right-side squad list. Only map markers live here.
    mask[:130, :] = 0
    mask[590:, :] = 0
    mask[:, :250] = 0
    mask[:, 1080:] = 0
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones((3, 3), dtype=np.uint8),
    )

    targets = []
    contours, _hierarchy = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = float(cv2.contourArea(contour))
        perimeter = float(cv2.arcLength(contour, True))
        circularity = 4.0 * math.pi * area / (perimeter * perimeter) if perimeter else 0.0
        extent = area / float(width * height) if width and height else 0.0
        if not (
            100.0 <= area <= 320.0
            and 12 <= width <= 23
            and 12 <= height <= 23
            and 0.7 <= width / float(height) <= 1.4
            and circularity >= 0.55
            and extent >= 0.5
        ):
            continue

        # The notification dot is attached to the marker's upper-right edge.
        target_x = (x + width / 2.0 - 24.0) * scale_x
        target_y = (y + height / 2.0 + 30.0) * scale_y
        targets.append((int(round(target_x)), int(round(target_y))))

    return sorted(set(targets), key=lambda point: (point[1], point[0]))


def radar_marker_has_notification(frame_bgr, bbox, padding=24):
    """Return whether a radar marker match contains a nearby red notification dot."""
    if not bbox or len(bbox) != 4:
        return False
    left, top, width, height = map(int, bbox)
    margin = max(0, int(padding))
    right = left + width
    bottom = top + height
    return any(
        left - margin <= target_x <= right + margin
        and top - margin <= target_y <= bottom + margin
        for target_x, target_y in detect_radar_notification_targets(frame_bgr)
    )


def detect_radar_card_action_target(frame_bgr):
    """Return the center of an enabled yellow action button on a radar card."""
    frame, scale_x, scale_y = _reference_frame(frame_bgr)
    if frame is None:
        return None
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    button = hsv[592:649, 108:380]
    enabled_mask = cv2.inRange(
        button,
        np.array([12, 120, 160], dtype=np.uint8),
        np.array([42, 255, 255], dtype=np.uint8),
    )
    if float(np.count_nonzero(enabled_mask)) / float(enabled_mask.size) < 0.20:
        return None
    return int(round(244 * scale_x)), int(round(621 * scale_y))


def detect_radar_world_action_target(frame_bgr):
    """Find a yellow action button shown after a radar card sends us to the map."""
    frame, scale_x, scale_y = _reference_frame(frame_bgr)
    if frame is None:
        return None
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    roi = hsv[440:620, 800:1160]
    mask = cv2.inRange(
        roi,
        np.array([8, 100, 130], dtype=np.uint8),
        np.array([45, 255, 255], dtype=np.uint8),
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((5, 5), dtype=np.uint8),
    )

    candidates = []
    contours, _hierarchy = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = float(cv2.contourArea(contour))
        if 150 <= width <= 290 and 30 <= height <= 70 and area >= 3500.0:
            candidates.append((area, x + width / 2.0 + 800, y + height / 2.0 + 440))
    if not candidates:
        return None
    _area, target_x, target_y = max(candidates)
    return int(round(target_x * scale_x)), int(round(target_y * scale_y))


def zombie_camp_checkbox_is_checked(frame_bgr):
    """Detect the optional 'set up camp after attack' checkmark."""
    frame, _scale_x, _scale_y = _reference_frame(frame_bgr)
    if frame is None:
        return False
    checkbox_inner = frame[506:530, 809:831]
    hsv = cv2.cvtColor(checkbox_inner, cv2.COLOR_BGR2HSV)
    colored_bright = (
        (hsv[:, :, 1] >= 80)
        & (hsv[:, :, 2] >= 135)
    )
    return float(np.count_nonzero(colored_bright)) / float(colored_bright.size) >= 0.08


def healing_auto_fill_is_checked(frame_bgr):
    """Detect the hospital auto-fill tick without relying on its caption."""
    frame, _scale_x, _scale_y = _reference_frame(frame_bgr)
    if frame is None:
        return False
    checkbox_inner = frame[665:689, 801:824]
    hsv = cv2.cvtColor(checkbox_inner, cv2.COLOR_BGR2HSV)
    bright_mark = hsv[:, :, 2] >= 155
    return float(np.count_nonzero(bright_mark)) / float(bright_mark.size) >= 0.08


def imread_unicode(image_path, flags=cv2.IMREAD_COLOR):
    """Read images reliably from Windows paths containing non-ASCII characters."""
    try:
        encoded = np.fromfile(Path(image_path), dtype=np.uint8)
    except (OSError, ValueError):
        return None
    if encoded.size == 0:
        return None
    return cv2.imdecode(encoded, flags)


@dataclass
class TemplateOrbData:
    keypoints: list
    descriptors: object


class TemplateCache:
    def __init__(self):
        self._color = {}
        self._gray = {}
        self._size = {}
        self._orb = {}
        self._scaled_gray = {}

    def invalidate(self, template_path):
        self._color.pop(template_path, None)
        self._gray.pop(template_path, None)
        self._size.pop(template_path, None)
        self._orb.pop(template_path, None)
        keys_to_remove = [key for key in self._scaled_gray if key[0] == template_path]
        for key in keys_to_remove:
            self._scaled_gray.pop(key, None)

    def get_color(self, template_path):
        if template_path not in self._color:
            self._color[template_path] = imread_unicode(template_path)
        return self._color[template_path]

    def get_gray(self, template_path):
        if template_path not in self._gray:
            self._gray[template_path] = imread_unicode(template_path, cv2.IMREAD_GRAYSCALE)
        return self._gray[template_path]

    def get_size(self, template_path):
        if template_path not in self._size:
            gray = self.get_gray(template_path)
            self._size[template_path] = None if gray is None else (gray.shape[1], gray.shape[0])
        return self._size[template_path]

    def get_scaled_gray(self, template_path, scale):
        scale_key = (template_path, round(float(scale), 4))
        if scale_key not in self._scaled_gray:
            template = self.get_gray(template_path)
            if template is None:
                self._scaled_gray[scale_key] = None
            else:
                new_w = int(template.shape[1] * scale)
                new_h = int(template.shape[0] * scale)
                if new_w < 5 or new_h < 5:
                    self._scaled_gray[scale_key] = None
                else:
                    self._scaled_gray[scale_key] = cv2.resize(
                        template,
                        (new_w, new_h),
                        interpolation=cv2.INTER_LINEAR,
                    )
        return self._scaled_gray[scale_key]

    def get_orb(self, template_path):
        if template_path not in self._orb:
            template = self.get_gray(template_path)
            if template is None:
                self._orb[template_path] = TemplateOrbData([], None)
            else:
                orb = cv2.ORB_create()
                keypoints, descriptors = orb.detectAndCompute(template, None)
                self._orb[template_path] = TemplateOrbData(keypoints or [], descriptors)
        return self._orb[template_path]
