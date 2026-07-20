import tempfile
import unittest
from pathlib import Path

from buzzbot.credentials import CredentialStore


class CredentialStoreTests(unittest.TestCase):
    def test_password_is_encrypted_and_can_be_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "credentials.json"

            def protect(payload):
                return b"protected:" + payload[::-1]

            def unprotect(payload):
                self.assertTrue(payload.startswith(b"protected:"))
                return payload[len(b"protected:"):][::-1]

            store = CredentialStore(path, protector=protect, unprotector=unprotect)
            store.set_password("main", "not-in-plain-text")

            self.assertTrue(store.has_password("main"))
            self.assertEqual(store.get_password("main"), "not-in-plain-text")
            self.assertNotIn("not-in-plain-text", path.read_text(encoding="utf-8"))
            self.assertTrue(store.delete_password("main"))
            self.assertFalse(store.has_password("main"))
            self.assertIsNone(store.get_password("main"))


if __name__ == "__main__":
    unittest.main()
