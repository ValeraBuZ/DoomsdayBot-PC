from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from buzzbot_app import AutoClicker, CONFIG_FILE, GAME_PACKAGE
from buzzbot.adb import AdbClient
from buzzbot.ldplayer import find_ldconsole, list_instances
from tools.run_all_accounts_matrix import (
    DEFAULT_INDEXES,
    _game_is_foreground,
    _run_hidden,
    _safe_name,
    _wait_for_adb,
    _write_json,
    run_task,
)


RADAR_TASKS = ("radar_rewards", "radar_quick", "radar_marches")
RADAR_SOURCE = PROJECT_ROOT / "build" / "training" / "donation_run_start.png"
RADAR_SOURCE_BOX = (88, 426, 132, 471)
RADAR_MATCH_ROI = (50, 350, 190, 520)
RADAR_MIN_SCORE = 0.78


def _radar_guard_visible(bot):
    for task_id in RADAR_TASKS:
        task = bot.get_routine_task(task_id)
        guard_uid = str((task or {}).get("idle_completion_guard_uid") or "")
        if guard_uid and bot._template_uid_is_visible(guard_uid):
            return True
    return False


def _radar_template():
    source = cv2.imread(str(RADAR_SOURCE), cv2.IMREAD_GRAYSCALE)
    if source is None:
        raise FileNotFoundError(f"Radar source screenshot is missing: {RADAR_SOURCE}")
    left, top, right, bottom = RADAR_SOURCE_BOX
    template = source[top:bottom, left:right]
    # The left/lower body is stable while the notification badge changes.
    return template[10:44, 0:30]


def open_radar(serial, output_path, timeout_seconds=20.0):
    bot = AutoClicker(root=None)
    bot.stop_schedule_thread()
    bot.save_config = lambda: None
    try:
        bot.input_backend = "adb"
        bot.adb_serial = serial
        bot._refresh_adb_client()
        if _radar_guard_visible(bot):
            frame = bot.adb_client.screenshot_bgr()
            cv2.imwrite(str(output_path), frame)
            return {"opened": True, "already_open": True, "score": 1.0}

        frame = bot.adb_client.screenshot_bgr()
        x1, y1, x2, y2 = RADAR_MATCH_ROI
        roi = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(roi, _radar_template(), cv2.TM_CCOEFF_NORMED)
        _min_value, score, _min_location, location = cv2.minMaxLoc(result)
        if score < RADAR_MIN_SCORE:
            cv2.imwrite(str(output_path), frame)
            return {"opened": False, "already_open": False, "score": round(float(score), 3)}

        match_x = x1 + location[0]
        match_y = y1 + location[1]
        tap_x = match_x + 23
        tap_y = match_y + 10
        bot.adb_client.tap(tap_x, tap_y)

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(1.0)
            bot._invalidate_capture()
            if _radar_guard_visible(bot):
                opened_frame = bot.adb_client.screenshot_bgr()
                cv2.imwrite(str(output_path), opened_frame)
                return {
                    "opened": True,
                    "already_open": False,
                    "score": round(float(score), 3),
                    "tap": [tap_x, tap_y],
                }

        frame = bot.adb_client.screenshot_bgr()
        cv2.imwrite(str(output_path), frame)
        return {
            "opened": False,
            "already_open": False,
            "score": round(float(score), 3),
            "tap": [tap_x, tap_y],
        }
    finally:
        bot.stop()
        bot.stop_schedule_thread()


def ensure_main_screen(serial, output_path):
    bot = AutoClicker(root=None)
    bot.stop_schedule_thread()
    bot.save_config = lambda: None
    try:
        bot.input_backend = "adb"
        bot.adb_serial = serial
        bot._refresh_adb_client()
        bot.stop_event.clear()
        reached = bot._return_to_main_screen(
            max_back_steps=6,
            require_settlement=True,
        )
        frame = bot.adb_client.screenshot_bgr()
        cv2.imwrite(str(output_path), frame)
        return bool(reached)
    finally:
        bot.stop_event.set()
        bot.stop()
        bot.stop_schedule_thread()


def _login(serial, account_key, output_dir):
    return run_task(
        serial,
        account_key,
        "game_login",
        output_dir,
        "economy",
        7,
        6,
    )


def _run_radar_pass(serial, account_key, account_dir, task_id, pass_number):
    pass_dir = account_dir / f"{task_id}_{pass_number:02d}"
    pass_dir.mkdir(parents=True, exist_ok=True)
    if not ensure_main_screen(serial, pass_dir / "main_screen.png"):
        return {
            "task": task_id,
            "pass": pass_number,
            "settled": False,
            "actions": 0,
            "error": "main screen recovery failed",
        }

    open_result = open_radar(serial, pass_dir / "radar_open.png")
    if not open_result.get("opened"):
        return {
            "task": task_id,
            "pass": pass_number,
            "settled": False,
            "actions": 0,
            "error": "radar entry was not confirmed",
            "radar_open": open_result,
        }

    task_result = run_task(
        serial,
        account_key,
        task_id,
        pass_dir,
        "economy",
        7,
        6,
    )
    task_result["pass"] = pass_number
    task_result["radar_open"] = open_result
    return task_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indexes", default=",".join(map(str, DEFAULT_INDEXES)))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-passes", type=int, default=12)
    parser.add_argument("--startup-settle-seconds", type=float, default=15.0)
    parser.add_argument("--keep-running", action="store_true")
    args = parser.parse_args()

    indexes = [int(value.strip()) for value in args.indexes.split(",") if value.strip()]
    output_root = args.output or (
        PROJECT_ROOT / "test_runs" / f"all_accounts_radar_{datetime.now():%Y%m%d_%H%M%S}"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    ldconsole = find_ldconsole()
    if ldconsole is None:
        raise SystemExit("LDPlayer console not found")
    instances = {instance.index: instance for instance in list_instances(ldconsole)}
    original_config = CONFIG_FILE.read_bytes()
    (output_root / "config.before.json").write_bytes(original_config)
    summary = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "game_package": GAME_PACKAGE,
        "indexes": indexes,
        "radar_tasks": list(RADAR_TASKS),
        "accounts": [],
    }

    try:
        for index in indexes:
            instance = instances.get(index)
            if instance is None:
                summary["accounts"].append({"index": index, "error": "LDPlayer instance not found"})
                _write_json(output_root / "summary.json", summary)
                continue

            account_key = f"ld{index}_{_safe_name(instance.name)}"
            account_dir = output_root / account_key
            account_dir.mkdir(parents=True, exist_ok=True)
            account_result = {
                "index": index,
                "name": instance.name,
                "configured_serial": instance.adb_serial,
                "serial": instance.adb_serial,
                "resolution": f"{instance.width}x{instance.height}",
                "tasks": [],
                "error": "",
            }
            summary["accounts"].append(account_result)
            _write_json(output_root / "summary.json", summary)

            try:
                launch = _run_hidden([ldconsole, "launch", "--index", index], timeout=30)
                if launch.returncode != 0:
                    raise RuntimeError(launch.stderr.strip() or "LDPlayer launch failed")
                client = AdbClient(serial=instance.adb_serial)
                connected_serial = _wait_for_adb(client, instance.index)
                if not connected_serial:
                    raise RuntimeError(f"ADB did not become ready: {instance.adb_serial}")
                account_result["serial"] = connected_serial
                time.sleep(max(0.0, args.startup_settle_seconds))

                for task_id in RADAR_TASKS:
                    task_summary = {
                        "task": task_id,
                        "passes": [],
                        "empty_pass_reached": False,
                        "error": "",
                    }
                    account_result["tasks"].append(task_summary)
                    for pass_number in range(1, max(1, args.max_passes) + 1):
                        if not _game_is_foreground(client):
                            recovery = _login(connected_serial, account_key, account_dir)
                            if not recovery.get("settled"):
                                task_summary["error"] = "foreground recovery failed"
                                break

                        result = _run_radar_pass(
                            connected_serial,
                            account_key,
                            account_dir,
                            task_id,
                            pass_number,
                        )
                        task_summary["passes"].append(result)
                        _write_json(output_root / "summary.json", summary)
                        if not result.get("settled"):
                            task_summary["error"] = str(result.get("error") or "radar pass failed")
                            break
                        if int(result.get("actions", 0) or 0) == 0:
                            task_summary["empty_pass_reached"] = True
                            break
                    else:
                        task_summary["error"] = "maximum pass count reached"
                    _write_json(output_root / "summary.json", summary)
            except Exception as exc:
                account_result["error"] = f"{type(exc).__name__}: {exc}"
                _write_json(output_root / "summary.json", summary)
            finally:
                if not args.keep_running:
                    _run_hidden([ldconsole, "quit", "--index", index], timeout=30)
                    time.sleep(3.0)
    finally:
        CONFIG_FILE.write_bytes(original_config)
        summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
        _write_json(output_root / "summary.json", summary)

    print(output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
