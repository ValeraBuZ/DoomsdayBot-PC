from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from buzzbot.credentials import CredentialError, CredentialStore
from buzzbot.remote_control import remote_data_dir
from buzzbot.remote_hub import RemoteHubRunner, RemoteHubStore
from buzzbot.version import APP_VERSION


HUB_CREDENTIAL_KEY = "remote-hub-token"
HUB_CONFIG_PATH = remote_data_dir() / "remote_hub_config.json"
DEFAULT_HUB_PORT = 18765
LEGACY_HUB_PORT = 8765


def _center(window, width, height):
    window.update_idletasks()
    x = max(0, (window.winfo_screenwidth() - width) // 2)
    y = max(0, (window.winfo_screenheight() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def _load_config():
    try:
        payload = json.loads(HUB_CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        payload = {}
    port = int(payload.get("port", DEFAULT_HUB_PORT) or DEFAULT_HUB_PORT)
    if port == LEGACY_HUB_PORT:
        port = DEFAULT_HUB_PORT
    return {
        "host": str(payload.get("host") or "0.0.0.0"),
        "port": min(65535, max(1024, port)),
    }


def _save_config(config):
    HUB_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = HUB_CONFIG_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, HUB_CONFIG_PATH)


def _tailscale_ip():
    candidates = [
        shutil.which("tailscale"),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tailscale" / "tailscale.exe",
    ]
    executable = next((str(path) for path in candidates if path and Path(path).is_file()), None)
    if not executable:
        return ""
    kwargs = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 5,
        "check": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run([executable, "ip", "-4"], **kwargs)
    except (OSError, subprocess.SubprocessError):
        return ""
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")


class HubWindow:
    def __init__(self, root):
        self.root = root
        self.config = _load_config()
        self.credentials = CredentialStore()
        self.runner = None
        self.token = self._load_or_create_token()
        self.store = RemoteHubStore()
        self.status_var = tk.StringVar(value="Hub остановлен")
        self.address_var = tk.StringVar()
        self.device_var = tk.StringVar(value="Устройств: 0 · онлайн: 0")
        self.show_token_var = tk.BooleanVar(value=False)
        self._build()
        self.start()

    def _load_or_create_token(self):
        try:
            token = self.credentials.get_password(HUB_CREDENTIAL_KEY)
            if token:
                return token
            token = secrets.token_urlsafe(36)
            self.credentials.set_password(HUB_CREDENTIAL_KEY, token)
            return token
        except CredentialError as exc:
            messagebox.showerror("BuZzbot Hub", str(exc), parent=self.root)
            raise

    def _build(self):
        colors = {
            "shell": "#14232B",
            "surface": "#F2F7F9",
            "line": "#C5D2D8",
            "text": "#26343C",
            "muted": "#71818A",
            "accent": "#E46922",
            "green": "#477B57",
        }
        self.root.title(f"BuZzbot Remote Hub v{APP_VERSION}")
        self.root.configure(bg=colors["shell"])
        self.root.resizable(False, False)
        _center(self.root, 650, 430)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TButton", font=("Bahnschrift SemiBold", 9), padding=(10, 8))

        panel = tk.Frame(
            self.root,
            bg=colors["surface"],
            highlightthickness=1,
            highlightbackground="#314650",
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        header = tk.Frame(panel, bg=colors["shell"], height=64)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="B",
            bg=colors["accent"],
            fg=colors["shell"],
            font=("Bahnschrift", 16, "bold"),
            width=2,
        ).pack(side=tk.LEFT, padx=(20, 12), pady=12)
        title = tk.Frame(header, bg=colors["shell"])
        title.pack(side=tk.LEFT, pady=12)
        tk.Label(
            title,
            text="BuZzbot Remote Hub",
            bg=colors["shell"],
            fg="white",
            font=("Bahnschrift", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="Центр удалённого управления",
            bg=colors["shell"],
            fg="#8EA0A8",
            font=("Segoe UI", 8),
        ).pack(anchor="w")

        body = tk.Frame(panel, bg=colors["surface"], padx=22, pady=20)
        body.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            body,
            textvariable=self.status_var,
            bg=colors["surface"],
            fg=colors["green"],
            font=("Bahnschrift", 12, "bold"),
        ).pack(anchor="w")
        tk.Label(
            body,
            textvariable=self.device_var,
            bg=colors["surface"],
            fg=colors["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 18))

        form = tk.Frame(body, bg=colors["surface"])
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)
        tk.Label(form, text="Адрес Hub", bg=colors["surface"], fg=colors["text"]).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        address = ttk.Entry(form, textvariable=self.address_var, state="readonly")
        address.grid(row=0, column=1, sticky="ew", pady=6)
        tk.Label(form, text="Секрет", bg=colors["surface"], fg=colors["text"]).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        self.token_entry = ttk.Entry(form, show="●")
        self.token_entry.grid(row=1, column=1, sticky="ew", pady=6)
        self.token_entry.insert(0, self.token)
        ttk.Button(form, text="Копировать", command=self.copy_token).grid(row=1, column=2, padx=(8, 0), pady=6)
        ttk.Checkbutton(
            form,
            text="Показать секрет",
            variable=self.show_token_var,
            command=lambda: self.token_entry.configure(show="" if self.show_token_var.get() else "●"),
        ).grid(row=2, column=1, sticky="w", pady=(2, 10))

        hint = (
            "Установите Tailscale на обеих машинах. В настройках удалённого BuZzbot "
            "укажите этот адрес и секрет. Порты роутера открывать не нужно."
        )
        tk.Label(
            body,
            text=hint,
            bg=colors["surface"],
            fg=colors["muted"],
            justify=tk.LEFT,
            wraplength=565,
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(8, 10))

        actions = tk.Frame(body, bg=colors["surface"])
        actions.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(actions, text="Открыть панель", command=self.open_dashboard).pack(side=tk.LEFT)
        ttk.Button(actions, text="Перезапустить Hub", command=self.restart).pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="Закрыть", command=self.close).pack(side=tk.RIGHT)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._update_counts()

    def copy_token(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.token)
        self.status_var.set("Секрет скопирован")

    def _public_address(self):
        host = _tailscale_ip() or socket.gethostname()
        return f"http://{host}:{self.config['port']}"

    def start(self):
        if self.runner is not None:
            return
        try:
            self.runner = RemoteHubRunner(
                self.config["host"],
                self.config["port"],
                self.token,
                self.store,
            )
            self.runner.start()
            _save_config(self.config)
        except Exception as exc:
            self.runner = None
            self.status_var.set("Hub не запущен")
            messagebox.showerror("BuZzbot Hub", str(exc), parent=self.root)
            return
        self.address_var.set(self._public_address())
        self.status_var.set(f"Hub работает · порт {self.config['port']}")

    def stop(self):
        if self.runner is not None:
            self.runner.stop()
            self.runner = None
        self.status_var.set("Hub остановлен")

    def restart(self):
        self.stop()
        self.start()

    def open_dashboard(self):
        local_url = f"http://127.0.0.1:{self.config['port']}/#token={self.token}"
        webbrowser.open(local_url)

    def _update_counts(self):
        devices = self.store.list_devices()
        online = sum(bool(device.get("online")) for device in devices)
        self.device_var.set(f"Устройств: {len(devices)} · онлайн: {online}")
        self.root.after(3000, self._update_counts)

    def close(self):
        self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        HubWindow(root)
    except Exception:
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
