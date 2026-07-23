import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from buzzbot_app import AutoClicker


class AdbAutoDetectTests(unittest.TestCase):
    @patch("buzzbot_app.AdbClient")
    def test_configured_profile_never_adopts_another_single_device(self, adb_client):
        probe = adb_client.return_value
        probe.list_devices.return_value = ["emulator-5562"]

        target = SimpleNamespace(index=5, adb_serial="emulator-5564")
        other = SimpleNamespace(index=4, adb_serial="emulator-5562")
        bot = AutoClicker.__new__(AutoClicker)
        bot.adb_path = "adb.exe"
        bot.adb_serial = "emulator-5564"
        bot.get_adb_repair_target = Mock(return_value=target)
        bot.get_current_account = Mock(return_value={"ldplayer_index": 5})
        bot._ldplayer_instances = Mock(return_value=("ldconsole.exe", [other, target]))
        bot._adopt_adb_serial = Mock()

        self.assertFalse(bot._auto_detect_adb_connection())
        bot._adopt_adb_serial.assert_not_called()


if __name__ == "__main__":
    unittest.main()
