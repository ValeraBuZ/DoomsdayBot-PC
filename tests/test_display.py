import unittest

from doomsdaybot.display import make_display_profile, matching_scales


class PlayerDisplayProfileTests(unittest.TestCase):
    def test_reference_resolution_needs_no_scaling(self):
        profile = make_display_profile(1280, 720)
        self.assertTrue(profile.is_reference)
        self.assertEqual(matching_scales(profile), ((1.0, 1.0),))

    def test_full_hd_resolution_scales_templates_and_clicks(self):
        profile = make_display_profile(1920, 1080)
        self.assertEqual(profile.scale_x, 1.5)
        self.assertEqual(profile.scale_y, 1.5)
        self.assertEqual(profile.percent_label, "150%")
        self.assertEqual(matching_scales(profile), ((1.5, 1.5),))

    def test_non_reference_aspect_ratio_keeps_independent_axes(self):
        profile = make_display_profile(1600, 1000)
        self.assertFalse(profile.aspect_ratio_matches)
        self.assertEqual(matching_scales(profile), ((1.25, 1.38889),))

    def test_optional_search_range_is_applied_around_player_scale(self):
        profile = make_display_profile(1920, 1080)
        scales = matching_scales(profile, True, 0.9, 1.1, 3)
        self.assertEqual(scales, ((1.35, 1.35), (1.5, 1.5), (1.65, 1.65)))

    def test_invalid_resolution_is_rejected(self):
        with self.assertRaises(ValueError):
            make_display_profile(0, 720)


if __name__ == "__main__":
    unittest.main()
