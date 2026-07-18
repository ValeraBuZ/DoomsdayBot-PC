from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from buzzbot_app import AutoClicker
from buzzbot.routines import effective_task_group


def run(serial: str, timeout_seconds: float, task_id: str = "radar", settings=None) -> int:
    bot = AutoClicker(root=None)
    settled = False
    try:
        bot.minimize_on_start = False
        bot.input_backend = "adb"
        bot.adb_serial = serial
        bot._refresh_adb_client()
        for task in bot.routine_tasks:
            enabled = task.get("id") == task_id
            task["enabled"] = enabled
            bot.groups[effective_task_group(task)] = enabled
            if enabled:
                task["timeout_seconds"] = max(20.0, float(task.get("timeout_seconds", 0.0)))

        selected_task = bot.get_routine_task(task_id)
        if selected_task is None:
            print(f"Unknown task: {task_id}", flush=True)
            return 2
        selected_task.setdefault("settings", {}).update(settings or {})
        task_group = effective_task_group(selected_task)
        task_paths = {
            image["path"]
            for image in bot.search_images
            if image.get("group") == task_group
        }
        initial_task_stats = {
            path: int(bot.stats.get(path, 0))
            for path in task_paths
        }
        bot.routine_next_run[task_id] = 0.0
        print(f"ADB connected={bot.check_adb_connection(notify=False)} serial={serial}", flush=True)
        if not bot.start_task_only(task_id):
            print("START failed", flush=True)
            return 2

        deadline = time.time() + timeout_seconds
        previous = None
        while time.time() < deadline and bot.is_running:
            next_run = float(bot.routine_next_run.get(task_id, 0.0) or 0.0)
            state = (
                bot.current_routine_task_id,
                bot.click_count,
                bot.status_message,
                int(max(0.0, next_run - time.time())),
            )
            if state != previous:
                print(f"STATE {state}", flush=True)
                previous = state
            if (
                bot.current_routine_task_id is None
                and next_run > time.time() + 1.0
            ):
                settled = True
                break
            time.sleep(1.0)

        task_actions = sum(
            max(0, int(bot.stats.get(path, 0)) - initial_task_stats[path])
            for path in task_paths
        )
        print(
            f"RESULT settled={settled} task_actions={task_actions} "
            f"total_actions={bot.click_count} status={bot.status_message!r}",
            flush=True,
        )
        return 0 if settled else 3
    finally:
        bot.stop()
        if bot._thread:
            bot._thread.join(timeout=5.0)
        bot.stop_schedule_thread()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", required=True)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--task", default="radar")
    parser.add_argument("--setting", action="append", default=[])
    args = parser.parse_args()
    settings = {}
    for item in args.setting:
        key, separator, value = item.partition("=")
        if not separator or not key:
            parser.error(f"Invalid --setting value: {item!r}; expected key=value")
        try:
            settings[key] = json.loads(value)
        except json.JSONDecodeError:
            settings[key] = value
    return run(args.serial, max(30.0, args.timeout), args.task, settings)


if __name__ == "__main__":
    raise SystemExit(main())
