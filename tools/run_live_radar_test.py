from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from doomsday_bot_final import AutoClicker
from doomsdaybot.routines import effective_task_group


def run(serial: str, timeout_seconds: float, task_id: str = "radar") -> int:
    bot = AutoClicker(root=None)
    completed = False
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

        if bot.get_routine_task(task_id) is None:
            print(f"Unknown task: {task_id}", flush=True)
            return 2
        bot.routine_next_run[task_id] = 0.0
        print(f"ADB connected={bot.check_adb_connection(notify=False)} serial={serial}", flush=True)
        if not bot.start_task_only(task_id):
            print("START failed", flush=True)
            return 2

        deadline = time.time() + timeout_seconds
        task_interval = float(bot.get_routine_task(task_id).get("interval_minutes", 1.0)) * 60.0
        completion_wait_threshold = max(60.0, task_interval * 0.75)
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
                and next_run > time.time() + completion_wait_threshold
            ):
                completed = True
                break
            time.sleep(1.0)

        print(
            f"RESULT completed={completed} clicks={bot.click_count} status={bot.status_message!r}",
            flush=True,
        )
        return 0 if completed else 3
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
    args = parser.parse_args()
    return run(args.serial, max(30.0, args.timeout), args.task)


if __name__ == "__main__":
    raise SystemExit(main())
