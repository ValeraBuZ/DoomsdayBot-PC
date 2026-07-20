from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
import socket
import threading
import time
from urllib import error, request
import uuid


LOGGER = logging.getLogger("BuZzbot.Remote")
REMOTE_CREDENTIAL_KEY = "remote-control-token"


def remote_data_dir():
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return base / "BuZzbot"


def default_remote_settings_path():
    return remote_data_dir() / "remote_settings.json"


def default_remote_state_path():
    return remote_data_dir() / "remote_device_state.json"


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def _read_json(path, default):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return dict(default)
    return payload if isinstance(payload, dict) else dict(default)


@dataclass
class RemoteSettings:
    enabled: bool = False
    hub_url: str = ""
    device_id: str = ""
    device_name: str = ""
    heartbeat_seconds: float = 10.0

    def normalized(self):
        device_id = str(self.device_id or "").strip() or str(uuid.uuid4())
        device_name = str(self.device_name or "").strip() or socket.gethostname() or "BuZzbot PC"
        hub_url = str(self.hub_url or "").strip().rstrip("/")
        heartbeat = min(60.0, max(5.0, float(self.heartbeat_seconds or 10.0)))
        return RemoteSettings(
            enabled=bool(self.enabled),
            hub_url=hub_url,
            device_id=device_id,
            device_name=device_name[:80],
            heartbeat_seconds=heartbeat,
        )


def load_remote_settings(path=None):
    path = Path(path) if path else default_remote_settings_path()
    payload = _read_json(path, {})
    settings = RemoteSettings(
        enabled=bool(payload.get("enabled", False)),
        hub_url=str(payload.get("hub_url") or ""),
        device_id=str(payload.get("device_id") or ""),
        device_name=str(payload.get("device_name") or ""),
        heartbeat_seconds=payload.get("heartbeat_seconds", 10.0),
    ).normalized()
    if payload != asdict(settings):
        save_remote_settings(settings, path)
    return settings


def save_remote_settings(settings, path=None):
    path = Path(path) if path else default_remote_settings_path()
    normalized = settings.normalized()
    _atomic_write_json(path, asdict(normalized))
    return normalized


class RemoteControlError(RuntimeError):
    pass


class RemoteControlClient:
    def __init__(
        self,
        settings,
        token,
        status_provider,
        command_handler,
        access_handler,
        *,
        state_path=None,
        urlopen=None,
        logger=None,
    ):
        self.settings = settings.normalized()
        self.token = str(token or "").strip()
        self.status_provider = status_provider
        self.command_handler = command_handler
        self.access_handler = access_handler
        self.state_path = Path(state_path) if state_path else default_remote_state_path()
        self._urlopen = urlopen or request.urlopen
        self.logger = logger or LOGGER
        state = _read_json(
            self.state_path,
            {"access_allowed": True, "last_command_id": 0},
        )
        self.access_allowed = bool(state.get("access_allowed", True))
        self.last_command_id = max(0, int(state.get("last_command_id", 0) or 0))
        self.connected = False
        self.last_error = ""
        self.last_checkin_at = 0.0
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread = None
        self._lock = threading.RLock()

    @property
    def configured(self):
        return bool(
            self.settings.enabled
            and self.settings.hub_url
            and self.token
        )

    def _save_state(self):
        _atomic_write_json(
            self.state_path,
            {
                "access_allowed": bool(self.access_allowed),
                "last_command_id": int(self.last_command_id),
            },
        )

    def start(self):
        if not self.configured:
            return False
        if self._thread is not None and self._thread.is_alive():
            self._wake_event.set()
            return True
        self._stop_event.clear()
        self._wake_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="BuZzbotRemoteControl",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self, timeout=3.0):
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=max(0.0, float(timeout)))
        self._thread = None
        self.connected = False

    def wake(self):
        self._wake_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self.checkin_once()
            except Exception as exc:
                with self._lock:
                    self.connected = False
                    self.last_error = str(exc)
                self.logger.warning("Remote check-in failed: %s", exc)
            self._wake_event.wait(self.settings.heartbeat_seconds)
            self._wake_event.clear()

    def _build_payload(self):
        status = self.status_provider() or {}
        if not isinstance(status, dict):
            status = {"status": str(status)}
        return {
            "device_id": self.settings.device_id,
            "device_name": self.settings.device_name,
            "ack_command_id": self.last_command_id,
            "status": status,
        }

    def checkin_once(self, timeout=7.0):
        if not self.configured:
            raise RemoteControlError("Удалённое управление не настроено.")
        endpoint = f"{self.settings.hub_url}/api/v1/checkin"
        payload = json.dumps(self._build_payload(), ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "BuZzbot-Remote/1",
            },
        )
        try:
            with self._urlopen(http_request, timeout=timeout) as response:
                response_data = response.read(128 * 1024)
        except error.HTTPError as exc:
            status_code = exc.code
            exc.close()
            if status_code in {401, 403}:
                raise RemoteControlError("Hub отклонил секрет доступа.") from exc
            raise RemoteControlError(f"Hub вернул HTTP {status_code}.") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise RemoteControlError(f"Hub недоступен: {reason}") from exc
        try:
            result = json.loads(response_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RemoteControlError("Hub вернул некорректный ответ.") from exc
        if not isinstance(result, dict) or not result.get("ok"):
            raise RemoteControlError(str(result.get("error") or "Hub отклонил запрос."))

        access_allowed = bool(result.get("access_allowed", True))
        if access_allowed != self.access_allowed:
            self.access_allowed = access_allowed
            self._save_state()
            self.access_handler(access_allowed)

        command = result.get("command")
        if isinstance(command, dict):
            command_id = max(0, int(command.get("id", 0) or 0))
            action = str(command.get("action") or "").strip().lower()
            if command_id > self.last_command_id and action:
                handled = self.command_handler(action)
                if handled is not False:
                    self.last_command_id = command_id
                    self._save_state()

        with self._lock:
            self.connected = True
            self.last_error = ""
            self.last_checkin_at = time.time()
        return result

    def snapshot(self):
        with self._lock:
            return {
                "configured": self.configured,
                "connected": bool(self.connected),
                "last_error": self.last_error,
                "last_checkin_at": float(self.last_checkin_at),
                "access_allowed": bool(self.access_allowed),
                "device_id": self.settings.device_id,
                "device_name": self.settings.device_name,
                "hub_url": self.settings.hub_url,
            }
