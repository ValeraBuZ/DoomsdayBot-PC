from __future__ import annotations

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from buzzbot.accounts import mask_google_account
from buzzbot.adb import AdbClient
from buzzbot.ldplayer import find_ldconsole, list_instances
from buzzbot_app import AutoClicker, logger
from tools.run_all_accounts_matrix import _wait_for_adb


def _run_hidden(command, timeout=30):
    kwargs = {
        "cwd": PROJECT_ROOT,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
        "check": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run([str(part) for part in command], **kwargs)


def _capture(client, path):
    frame = client.screenshot_bgr()
    if not cv2.imwrite(str(path), frame):
        raise OSError(f"Не удалось сохранить снимок: {path}")


def _wait_for_main_screen(bot, timeout_seconds):
    if bot._is_main_screen_visible():
        return True
    if not bot.start_task_only("game_login"):
        return False
    deadline = time.time() + float(timeout_seconds)
    while time.time() < deadline and bot.is_running:
        if bot._is_main_screen_visible():
            break
        time.sleep(1.0)
    bot.stop()
    if bot._thread:
        bot._thread.join(timeout=5.0)
    return bot._is_main_screen_visible()


def main():
    parser = argparse.ArgumentParser(description="Безопасная проверка списка Google в LDPlayer")
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--startup-settle-seconds", type=float, default=12.0)
    parser.add_argument("--login-timeout", type=float, default=700.0)
    parser.add_argument("--keep-running", action="store_true")
    args = parser.parse_args()

    output_dir = args.output or (
        PROJECT_ROOT / "test_runs" / f"account_switch_probe_{datetime.now():%Y%m%d_%H%M%S}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "index": args.index,
        "instance": "",
        "main_screen": False,
        "probe_started": False,
        "accounts": [],
        "last_result": "",
        "status": "",
        "passed": False,
        "error": "",
    }

    ldconsole = find_ldconsole()
    if ldconsole is None:
        raise SystemExit("LDPlayer console not found")
    instances = {instance.index: instance for instance in list_instances(ldconsole)}
    instance = instances.get(args.index)
    if instance is None:
        raise SystemExit(f"LDPlayer instance not found: {args.index}")
    result["instance"] = instance.name

    handler = logging.FileHandler(output_dir / "probe.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    bot = None
    try:
        launch = _run_hidden([ldconsole, "launch", "--index", args.index])
        if launch.returncode != 0:
            raise RuntimeError(launch.stderr.strip() or "LDPlayer launch failed")
        client = AdbClient(serial=instance.adb_serial)
        serial = _wait_for_adb(client, instance_index=args.index, timeout_seconds=150.0)
        if not serial:
            raise RuntimeError("ADB did not become ready")
        time.sleep(max(0.0, args.startup_settle_seconds))

        bot = AutoClicker(root=None)
        bot.stop_schedule_thread()
        bot.save_config = lambda: None
        bot.minimize_on_start = False
        bot.input_backend = "adb"
        bot.adb_serial = serial
        bot.account_rotation_enabled = False
        bot._refresh_adb_client()

        result["main_screen"] = _wait_for_main_screen(bot, args.login_timeout)
        _capture(client, output_dir / "before_probe.png")
        if not result["main_screen"]:
            raise RuntimeError("Main screen was not detected")

        probe_profile = {
            "id": "__probe__",
            "name": "Проверка списка",
            "chooser_index": 1,
            "switch_completion_uid": "",
        }
        bot.account_profiles.append(probe_profile)
        result["probe_started"] = bool(bot.start_account_probe(probe_profile["id"]))
        if not result["probe_started"]:
            raise RuntimeError(f"Account probe did not start: {bot.status_message}")

        deadline = time.time() + 150.0
        while time.time() < deadline and bot.is_running:
            time.sleep(0.5)
        _capture(client, output_dir / "google_chooser.png")
        result["accounts"] = [
            {
                "chooser_index": item["chooser_index"],
                "account": mask_google_account(item["email"]),
            }
            for item in bot.account_switch_candidates
        ]
        result["last_result"] = bot.account_switch_last_result
        result["status"] = bot.status_message
        result["passed"] = bool(result["accounts"] and bot.account_switch_last_result)
        if not result["passed"]:
            result["error"] = "Google account list was not detected"
    except Exception as exc:
        logger.exception("Account switch probe failed")
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if bot is not None:
            result["status"] = result["status"] or bot.status_message
            bot.stop()
            if bot._thread:
                bot._thread.join(timeout=5.0)
            bot.stop_schedule_thread()
        if not args.keep_running:
            _run_hidden([ldconsole, "quit", "--index", args.index])
        logger.removeHandler(handler)
        handler.close()
        result["finished_at"] = datetime.now().isoformat(timespec="seconds")
        (output_dir / "summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
