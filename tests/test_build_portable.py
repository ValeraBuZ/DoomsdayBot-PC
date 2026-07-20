import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_portable


class PortableBuildTests(unittest.TestCase):
    def test_portable_brand_and_windowed_executable_are_stable(self):
        spec = build_portable.build_spec_text()
        self.assertEqual(build_portable.APP_NAME, "BuZzbot")
        self.assertEqual(build_portable.BUNDLE_NAME, "BuZzbotPortable")
        self.assertIn("['buzzbot_app.py']", spec)
        self.assertIn("name='BuZzbot'", spec)
        self.assertIn("name='BuZzbotPortable'", spec)
        self.assertIn("console=False", spec)
        self.assertIn('"buzzbot/assets"', spec)

    def test_stage_templates_places_png_next_to_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source_img"
            stage = root / "stage"
            (source / "heal").mkdir(parents=True)
            (source / "heal" / "template.png").write_bytes(b"png")

            with (
                patch.object(build_portable, "IMG_DIR", source),
                patch.object(build_portable, "STAGE_DIR", stage),
            ):
                build_portable.stage_templates()

            self.assertTrue((stage / "img" / "heal" / "template.png").is_file())

    def test_validate_portable_layout_rejects_missing_configured_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            (stage / "img").mkdir()
            (stage / "img" / "present.png").write_bytes(b"png")
            (stage / "BuZzbot.exe").write_bytes(b"exe")
            (stage / "config.json").write_text(
                json.dumps(
                    {
                        "images": [
                            {
                                "description": "Missing template",
                                "path": "img/missing.png",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(build_portable, "STAGE_DIR", stage):
                with self.assertRaisesRegex(RuntimeError, "Missing template"):
                    build_portable.validate_portable_layout()

    def test_validate_portable_layout_accepts_complete_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            (stage / "img" / "heal").mkdir(parents=True)
            (stage / "img" / "heal" / "template.png").write_bytes(b"png")
            (stage / "BuZzbot.exe").write_bytes(b"exe")
            (stage / "config.json").write_text(
                json.dumps(
                    {
                        "images": [
                            {
                                "description": "Heal",
                                "path": "img/heal/template.png",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(build_portable, "STAGE_DIR", stage):
                build_portable.validate_portable_layout()


if __name__ == "__main__":
    unittest.main()
