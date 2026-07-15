from __future__ import annotations

from dataclasses import dataclass


REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720


@dataclass(frozen=True)
class PlayerDisplayProfile:
    width: int
    height: int
    scale_x: float
    scale_y: float

    @property
    def is_reference(self):
        return self.width == REFERENCE_WIDTH and self.height == REFERENCE_HEIGHT

    @property
    def aspect_ratio_matches(self):
        return abs(self.scale_x - self.scale_y) <= 0.03

    @property
    def percent_label(self):
        if abs(self.scale_x - self.scale_y) <= 0.005:
            return f"{self.scale_x * 100:.0f}%"
        return f"X {self.scale_x * 100:.0f}% / Y {self.scale_y * 100:.0f}%"


def make_display_profile(width, height):
    width = int(width)
    height = int(height)
    if width < 1 or height < 1:
        raise ValueError("Display dimensions must be positive")
    return PlayerDisplayProfile(
        width=width,
        height=height,
        scale_x=width / REFERENCE_WIDTH,
        scale_y=height / REFERENCE_HEIGHT,
    )


def matching_scales(profile, extra_enabled=False, minimum=0.9, maximum=1.2, steps=5):
    if not extra_enabled:
        factors = (1.0,)
    else:
        steps = max(1, int(steps))
        minimum = float(minimum)
        maximum = float(maximum)
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        if steps == 1:
            factors = ((minimum + maximum) / 2.0,)
        else:
            increment = (maximum - minimum) / (steps - 1)
            factors = tuple(minimum + increment * index for index in range(steps))
    return tuple(
        (round(profile.scale_x * factor, 5), round(profile.scale_y * factor, 5))
        for factor in factors
    )
