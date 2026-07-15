from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np


class AdbError(RuntimeError):
    """Raised when an ADB command cannot be completed."""


def find_adb_executable(preferred=None):
    candidates = [preferred, os.environ.get("ADB_PATH")]
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates.extend([
        Path(r"C:\LDPlayer\LDPlayer9\adb.exe"),
        Path(r"C:\LDPlayer\LDPlayer4.0\adb.exe"),
        local_app_data / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        shutil.which("adb"),
    ])
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            return path.resolve()
    return None


class AdbClient:
    def __init__(self, adb_path=None, serial="emulator-5556", runner=None):
        self.adb_path = find_adb_executable(adb_path)
        self.serial = str(serial or "").strip()
        self._runner = runner or subprocess.run

    def _run(self, args, *, binary=False, timeout=10):
        if self.adb_path is None:
            raise AdbError("ADB не найден. Укажите путь к adb.exe.")

        command = [str(self.adb_path)]
        if self.serial:
            command.extend(["-s", self.serial])
        command.extend(str(arg) for arg in args)

        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "timeout": timeout,
            "check": False,
        }
        if not binary:
            kwargs.update({"text": True, "encoding": "utf-8", "errors": "replace"})
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            result = self._runner(command, **kwargs)
        except (OSError, subprocess.SubprocessError) as exc:
            raise AdbError(f"Не удалось запустить ADB: {exc}") from exc

        if result.returncode != 0:
            stderr = result.stderr
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            raise AdbError((stderr or "Команда ADB завершилась с ошибкой.").strip())
        return result.stdout

    def is_available(self):
        if self.adb_path is None or not self.serial:
            return False
        try:
            output = self._run(["get-state"], timeout=4)
        except AdbError:
            return False
        return str(output).strip() == "device"

    def screenshot_bgr(self):
        payload = self._run(["exec-out", "screencap", "-p"], binary=True, timeout=12)
        if not payload:
            raise AdbError("ADB вернул пустой снимок экрана.")
        encoded = np.frombuffer(payload, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            raise AdbError("Не удалось декодировать снимок экрана ADB.")
        return frame

    def tap(self, x, y):
        self._run(["shell", "input", "tap", int(x), int(y)], timeout=5)

    def double_tap(self, x, y, interval=0.12):
        self.tap(x, y)
        import time
        time.sleep(max(0.02, float(interval)))
        self.tap(x, y)

    def long_press(self, x, y, duration_ms=700):
        self._run([
            "shell", "input", "swipe",
            int(x), int(y), int(x), int(y), int(duration_ms),
        ], timeout=5)

    def swipe(self, x1, y1, x2, y2, duration_ms=500):
        self._run([
            "shell", "input", "swipe",
            int(x1), int(y1), int(x2), int(y2), int(duration_ms),
        ], timeout=5)

    def input_text(self, value):
        escaped = str(value).replace("%", "\\%").replace(" ", "%s")
        self._run(["shell", "input", "text", escaped], timeout=5)

    def keyevent(self, key_code):
        self._run(["shell", "input", "keyevent", int(key_code)], timeout=5)

    def list_devices(self):
        original_serial = self.serial
        self.serial = ""
        try:
            output = self._run(["devices", "-l"], timeout=6)
        finally:
            self.serial = original_serial
        devices = []
        for line in str(output or "").splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def restart_server(self):
        original_serial = self.serial
        self.serial = ""
        try:
            self._run(["start-server"], timeout=10)
        finally:
            self.serial = original_serial

    def ui_xml(self):
        """Return the current Android accessibility tree without leaving files behind."""
        remote_path = "/sdcard/doomsdaybot_ui.xml"
        self._run(["shell", "uiautomator", "dump", remote_path], timeout=12)
        try:
            return self._run(["shell", "cat", remote_path], timeout=5)
        finally:
            try:
                self._run(["shell", "rm", "-f", remote_path], timeout=5)
            except AdbError:
                pass
