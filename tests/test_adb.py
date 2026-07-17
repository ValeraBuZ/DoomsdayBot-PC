import subprocess
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from doomsdaybot.adb import AdbClient, AdbError


class FakeResult:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class AdbClientTests(unittest.TestCase):
    def make_client(self, runner):
        client = AdbClient.__new__(AdbClient)
        client.adb_path = __import__("pathlib").Path("adb.exe")
        client.serial = "emulator-5556"
        client._runner = runner
        return client

    def test_connection_uses_selected_serial(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeResult(stdout="device\n")

        client = self.make_client(runner)
        self.assertTrue(client.is_available())
        self.assertEqual(calls[0][0], ["adb.exe", "-s", "emulator-5556", "get-state"])

    def test_screenshot_is_decoded_to_bgr(self):
        source = np.zeros((4, 6, 3), dtype=np.uint8)
        source[:, :] = (12, 34, 56)
        ok, encoded = cv2.imencode(".png", source)
        self.assertTrue(ok)

        def runner(_command, **_kwargs):
            return FakeResult(stdout=encoded.tobytes(), stderr=b"")

        frame = self.make_client(runner).screenshot_bgr()
        self.assertEqual(frame.shape, (4, 6, 3))
        self.assertEqual(tuple(frame[0, 0]), (12, 34, 56))

    def test_failed_command_raises_readable_error(self):
        def runner(_command, **_kwargs):
            return FakeResult(stderr="device offline", returncode=1)

        with self.assertRaisesRegex(AdbError, "device offline"):
            self.make_client(runner).tap(10, 20)

    def test_swipe_uses_selected_serial_and_duration(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeResult()

        self.make_client(runner).swipe(10, 20, 30, 40, duration_ms=650)
        self.assertEqual(
            calls[0][0],
            [
                "adb.exe",
                "-s",
                "emulator-5556",
                "shell",
                "input",
                "swipe",
                "10",
                "20",
                "30",
                "40",
                "650",
            ],
        )

    def test_keyevent_uses_selected_serial(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeResult()

        self.make_client(runner).keyevent(67)
        self.assertEqual(
            calls[0][0],
            ["adb.exe", "-s", "emulator-5556", "shell", "input", "keyevent", "67"],
        )

    def test_launch_package_uses_selected_emulator(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeResult(stdout="Events injected: 1\n")

        self.make_client(runner).launch_package("com.igg.android.doomsdaylastsurvivors")
        self.assertEqual(
            calls[0][0],
            [
                "adb.exe",
                "-s",
                "emulator-5556",
                "shell",
                "monkey",
                "-p",
                "com.igg.android.doomsdaylastsurvivors",
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
        )

    def test_list_devices_ignores_configured_serial(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeResult(
                stdout="List of devices attached\nemulator-5560 device product:test model:test\noffline-1 offline\n"
            )

        client = self.make_client(runner)
        self.assertEqual(client.list_devices(), ["emulator-5560"])
        self.assertEqual(calls[0][0], ["adb.exe", "devices", "-l"])
        self.assertEqual(client.serial, "emulator-5556")

    def test_restart_server_clears_stale_daemon_without_serial(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return FakeResult()

        client = self.make_client(runner)
        client.restart_server()

        self.assertEqual(calls[0][0], ["adb.exe", "kill-server"])
        self.assertEqual(calls[1][0], ["adb.exe", "start-server"])
        self.assertEqual(client.serial, "emulator-5556")

    def test_ui_xml_is_read_and_removed(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            stdout = '<hierarchy text="Verify it&apos;s you" />' if "cat" in command else ""
            return FakeResult(stdout=stdout)

        xml = self.make_client(runner).ui_xml()
        self.assertIn("Verify", xml)
        self.assertEqual(
            calls[0][0][-3:],
            ["uiautomator", "dump", "/sdcard/doomsdaybot_ui.xml"],
        )
        self.assertEqual(calls[1][0][-2:], ["cat", "/sdcard/doomsdaybot_ui.xml"])
        self.assertEqual(calls[2][0][-3:], ["rm", "-f", "/sdcard/doomsdaybot_ui.xml"])

    @patch("doomsdaybot.adb.os.name", "nt")
    def test_windows_commands_do_not_open_a_console(self):
        calls = []

        def runner(_command, **kwargs):
            calls.append(kwargs)
            return FakeResult(stdout="device\n")

        self.make_client(runner).is_available()
        self.assertEqual(
            calls[0]["creationflags"],
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


if __name__ == "__main__":
    unittest.main()
