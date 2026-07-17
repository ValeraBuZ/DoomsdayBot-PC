import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_portable


class PortableBuildTests(unittest.TestCase):
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
