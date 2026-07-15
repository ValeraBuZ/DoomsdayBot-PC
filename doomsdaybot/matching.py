from __future__ import annotations

from dataclasses import dataclass

import cv2


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
            self._color[template_path] = cv2.imread(template_path)
        return self._color[template_path]

    def get_gray(self, template_path):
        if template_path not in self._gray:
            self._gray[template_path] = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
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
