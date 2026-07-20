import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from buzzbot.updater import (
    UpdateError,
    download_and_stage_update,
    fetch_update_manifest,
    is_newer_version,
)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class UpdateTests(unittest.TestCase):
    def test_version_comparison(self):
        self.assertTrue(is_newer_version("3.4.0", "3.3.1"))
        self.assertFalse(is_newer_version("3.3.1", "3.3.1"))
        self.assertFalse(is_newer_version("3.2.9", "3.3.1"))

    def test_manifest_requires_sha256(self):
        payload = json.dumps({"version": "3.4.0", "sha256": "bad"}).encode()
        with self.assertRaisesRegex(UpdateError, "SHA-256"):
            fetch_update_manifest(opener=lambda _request, timeout: FakeResponse(payload))

    def test_verified_portable_archive_is_staged(self):
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w") as archive:
            archive.writestr("BuZzbotPortable/BuZzbot.exe", b"exe")
            archive.writestr("BuZzbotPortable/_internal/module.bin", b"module")
        archive_bytes = archive_buffer.getvalue()
        checksum = hashlib.sha256(archive_bytes).hexdigest()
        manifest_bytes = json.dumps(
            {"version": "3.4.0", "sha256": checksum}
        ).encode()

        def opener(http_request, timeout):
            if str(http_request.full_url).endswith("update-manifest.json"):
                return FakeResponse(manifest_bytes)
            return FakeResponse(archive_bytes)

        with tempfile.TemporaryDirectory() as temp_dir:
            staged = download_and_stage_update(
                "3.3.1",
                update_root=Path(temp_dir),
                opener=opener,
            )

            self.assertEqual(staged.version, "3.4.0")
            self.assertEqual((staged.source_dir / "BuZzbot.exe").read_bytes(), b"exe")

    def test_wrong_archive_checksum_is_rejected(self):
        manifest_bytes = json.dumps(
            {"version": "3.4.0", "sha256": "0" * 64}
        ).encode()

        def opener(http_request, timeout):
            if str(http_request.full_url).endswith("update-manifest.json"):
                return FakeResponse(manifest_bytes)
            return FakeResponse(b"not-the-signed-archive")

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(UpdateError, "SHA-256"):
                download_and_stage_update(
                    "3.3.1",
                    update_root=Path(temp_dir),
                    opener=opener,
                )


if __name__ == "__main__":
    unittest.main()
