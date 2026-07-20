import tempfile
import unittest
from pathlib import Path

from buzzbot.remote_control import (
    RemoteControlClient,
    RemoteControlError,
    RemoteSettings,
    load_remote_settings,
    save_remote_settings,
)
from buzzbot.remote_hub import RemoteHubRunner, RemoteHubStore


TOKEN = "test-token-with-at-least-24-characters"


class RemoteControlTests(unittest.TestCase):
    def test_machine_settings_receive_stable_unique_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            first = load_remote_settings(path)
            second = load_remote_settings(path)

            self.assertTrue(first.device_id)
            self.assertEqual(first.device_id, second.device_id)
            self.assertTrue(first.device_name)

            saved = save_remote_settings(
                RemoteSettings(
                    enabled=True,
                    hub_url="http://127.0.0.1:8765/",
                    device_id=first.device_id,
                    device_name="Farm PC",
                    heartbeat_seconds=1,
                ),
                path,
            )
            self.assertEqual(saved.hub_url, "http://127.0.0.1:8765")
            self.assertEqual(saved.heartbeat_seconds, 5.0)

    def test_hub_tracks_devices_commands_and_persistent_access(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = RemoteHubStore(root / "hub.json")
            runner = RemoteHubRunner("127.0.0.1", 0, TOKEN, store)
            runner.start()
            host, port = runner.address
            settings = RemoteSettings(
                enabled=True,
                hub_url=f"http://{host}:{port}",
                device_id="device-one",
                device_name="Первый ПК",
                heartbeat_seconds=5,
            )
            commands = []
            access_changes = []
            client = RemoteControlClient(
                settings,
                TOKEN,
                lambda: {
                    "app_version": "3.4.0",
                    "state": "running",
                    "account": "Main",
                    "current_task": "Еда",
                    "status": "Сбор ресурсов",
                },
                lambda action: commands.append(action) or True,
                access_changes.append,
                state_path=root / "client.json",
            )
            try:
                client.checkin_once()
                devices = store.list_devices()
                self.assertEqual(len(devices), 1)
                self.assertTrue(devices[0]["online"])
                self.assertEqual(devices[0]["status"]["current_task"], "Еда")

                store.set_command("device-one", "pause")
                client.checkin_once()
                self.assertEqual(commands, ["pause"])
                client.checkin_once()
                self.assertIsNone(store.list_devices()[0]["command"])

                store.set_access("device-one", False)
                client.checkin_once()
                self.assertEqual(access_changes, [False])
                self.assertEqual(commands[-1], "stop")
                self.assertFalse(client.access_allowed)

                restored = RemoteControlClient(
                    settings,
                    TOKEN,
                    lambda: {},
                    lambda _action: True,
                    lambda _allowed: None,
                    state_path=root / "client.json",
                )
                self.assertFalse(restored.access_allowed)

                store.set_access("device-one", True)
                client.checkin_once()
                self.assertEqual(access_changes, [False, True])
                self.assertTrue(client.access_allowed)
            finally:
                runner.stop()

    def test_hub_rejects_wrong_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RemoteHubStore(Path(temp_dir) / "hub.json")
            runner = RemoteHubRunner("127.0.0.1", 0, TOKEN, store)
            runner.start()
            host, port = runner.address
            client = RemoteControlClient(
                RemoteSettings(
                    enabled=True,
                    hub_url=f"http://{host}:{port}",
                    device_id="blocked-device",
                    device_name="Blocked",
                ),
                "wrong-token-that-is-long-enough",
                lambda: {},
                lambda _action: True,
                lambda _allowed: None,
                state_path=Path(temp_dir) / "client.json",
            )
            try:
                with self.assertRaisesRegex(RemoteControlError, "отклонил секрет"):
                    client.checkin_once()
            finally:
                runner.stop()

    def test_multiple_cities_are_independent_devices(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = RemoteHubStore(root / "hub.json")
            store.checkin(
                {
                    "device_id": "moscow",
                    "device_name": "Москва",
                    "status": {"state": "running"},
                }
            )
            store.checkin(
                {
                    "device_id": "kazan",
                    "device_name": "Казань",
                    "status": {"state": "paused"},
                }
            )
            store.set_command("kazan", "stop")
            devices = {item["device_id"]: item for item in store.list_devices()}

            self.assertIsNone(devices["moscow"]["command"])
            self.assertEqual(devices["kazan"]["command"]["action"], "stop")


if __name__ == "__main__":
    unittest.main()
