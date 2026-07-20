from __future__ import annotations

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path
import random
import re
import secrets
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from buzzbot_app import AutoClicker, CONFIG_FILE, SYSTEM_TEMPLATE_GROUP, logger
from buzzbot.adb import AdbClient
from buzzbot.ldplayer import find_ldconsole, list_instances
from buzzbot.routines import effective_task_group
from tools.run_all_accounts_matrix import _capture, _run_hidden, _safe_name, _wait_for_adb


NON_MARCH_TASKS = (
    "vip_rewards",
    "alliance_donations",
    "alliance_help",
    "fence_survivors",
    "processing_factory",
    "processing_contest",
    "mail_rewards",
    "completed_tasks",
    "research",
    "gathering_boost",
    "train_infantry",
    "train_riders",
    "train_shooters",
    "train_vehicles",
)
MARCH_TASKS = (
    "food",
    "wood",
    "metal",
    "oil",
    "zombie_hunt",
    "collective_mind",
)
ZOMBIE_TEST_ACCOUNT = "Phoenix675"
TASK_FAILURE_PATTERNS = (
    r"Routine ([a-z0-9_]+) timed out without actions",
    r"Routine ([a-z0-9_]+) is temporarily unavailable \((?!max_queue_checks\)|max_lab_checks\)|boost_item_unavailable\))",
)
BUSY_SQUAD_PATTERNS = (
    r"Routine ([a-z0-9_]+) reached the squad screen while every squad is busy",
    r"Routine ([a-z0-9_]+) reached the squad screen without an available squad",
    r"Routine ([a-z0-9_]+) is temporarily unavailable \((?:max_queue_checks|max_lab_checks)\)",
    r"Routine ([a-z0-9_]+) is temporarily unavailable \(boost_item_unavailable\)",
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _march_tasks_for_account(account_name):
    if str(account_name or "").strip().casefold() == ZOMBIE_TEST_ACCOUNT.casefold():
        return MARCH_TASKS
    return tuple(task_id for task_id in MARCH_TASKS if task_id != "zombie_hunt")


def _random_program(rng, count, march_tasks=MARCH_TASKS):
    count = max(2, min(int(count), len(NON_MARCH_TASKS) + 1))
    selected = rng.sample(NON_MARCH_TASKS, count - 1)
    selected.append(rng.choice(tuple(march_tasks)))
    rng.shuffle(selected)
    return selected


def _task_failures_from_log(log_text):
    failures = set()
    for pattern in TASK_FAILURE_PATTERNS:
        failures.update(re.findall(pattern, log_text))
    return sorted(failures)


def _busy_tasks_from_log(log_text):
    busy = set()
    for pattern in BUSY_SQUAD_PATTERNS:
        busy.update(re.findall(pattern, log_text))
    return sorted(busy)


def _capacity_blocked_march_tasks(selected_ids, routine_tasks, active_marches, max_marches):
    if int(active_marches) < max(1, int(max_marches)):
        return set()
    selected = set(selected_ids)
    return {
        str(task.get("id"))
        for task in routine_tasks
        if task.get("id") in selected and task.get("uses_march", False)
    }


def _configure_program(bot, selected_ids, rng):
    settings = {}
    enabled_ids = {"game_login", *selected_ids}
    for task in bot.routine_tasks:
        enabled = task.get("id") in enabled_ids
        task["enabled"] = enabled
        bot.groups[effective_task_group(task)] = enabled
        if enabled:
            bot.routine_next_run[task["id"]] = 0.0

    research = bot.get_routine_task("research")
    if research and "research" in enabled_ids:
        branch = rng.choice(("economy", "war"))
        research.setdefault("settings", {})["branch"] = branch
        settings["research_branch"] = branch

    for task_id in set(selected_ids).intersection({"food", "wood", "metal", "oil"}):
        level = 7
        bot.get_routine_task(task_id).setdefault("settings", {})["resource_level"] = level
        settings[f"{task_id}_level"] = level

    if "collective_mind" in enabled_ids:
        level = rng.choice((6, 7))
        bot.get_routine_task("collective_mind").setdefault("settings", {})["level"] = level
        settings["collective_mind_level"] = level
    return settings


def _launch_with_adb(ldconsole, instance, settle_seconds):
    for attempt in range(2):
        AdbClient(serial="").restart_server()
        launch = _run_hidden([ldconsole, "launch", "--index", instance.index], timeout=30)
        if launch.returncode != 0:
            error = launch.stderr.strip() or "LDPlayer launch failed"
        else:
            client = AdbClient(serial=instance.adb_serial)
            if _wait_for_adb(client, instance.index, timeout_seconds=150.0):
                time.sleep(max(0.0, settle_seconds))
                return client, attempt + 1
            error = f"ADB did not become ready: {instance.adb_serial}"
        _run_hidden([ldconsole, "quit", "--index", instance.index], timeout=30)
        time.sleep(8.0)
    raise RuntimeError(error)


def run_program(instance, selected_ids, seed, output_dir, timeout_seconds, settle_seconds):
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    result = {
        "seed": seed,
        "account": {
            "index": instance.index,
            "name": instance.name,
            "serial": instance.adb_serial,
            "resolution": f"{instance.width}x{instance.height}",
        },
        "selected_tasks": selected_ids,
        "settings": {},
        "visited_tasks": [],
        "task_screenshots": [],
        "step_screenshots": [],
        "actions_by_group": {},
        "unexpected_groups": [],
        "missing_tasks": [],
        "task_failures": [],
        "capacity_blocked_tasks": [],
        "adb_launch_attempts": 0,
        "passed": False,
        "error": "",
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    if (
        "zombie_hunt" in selected_ids
        and "zombie_hunt" not in _march_tasks_for_account(instance.name)
    ):
        result["error"] = (
            f"Zombie hunt live tests are restricted to {ZOMBIE_TEST_ACCOUNT}; "
            f"selected account: {instance.name}"
        )
        result["finished_at"] = datetime.now().isoformat(timespec="seconds")
        return result
    ldconsole = find_ldconsole()
    if ldconsole is None:
        result["error"] = "LDPlayer console not found"
        return result

    log_path = output_dir / "random_program.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    bot = None
    try:
        client, attempts = _launch_with_adb(ldconsole, instance, settle_seconds)
        result["adb_launch_attempts"] = attempts

        bot = AutoClicker(root=None)
        bot.stop_schedule_thread()
        bot.save_config = lambda: None
        bot.minimize_on_start = False
        bot.input_backend = "adb"
        bot.adb_serial = instance.adb_serial
        bot.current_account_id = f"ld{instance.index}_{_safe_name(instance.name)}"
        bot.routine_march_context = f"adb:{instance.adb_serial}:{bot.current_account_id}"
        bot.routine_march_deadlines = []
        bot.account_rotation_enabled = False
        bot._refresh_adb_client()
        result["settings"] = _configure_program(bot, selected_ids, rng)

        selected_with_login = {"game_login", *selected_ids}
        selected_groups = {
            effective_task_group(task)
            for task in bot.routine_tasks
            if task.get("id") in selected_with_login
        }
        tracked_images = {
            image["path"]: (image.get("group") or "")
            for image in bot.search_images
        }
        initial_stats = {
            path: int(bot.stats.get(path, 0))
            for path in tracked_images
        }
        started_at = time.time()
        if not bot.start_routines():
            raise RuntimeError(f"Bot did not start: {bot.status_message}")

        current_task = None
        current_steps = ()
        capacity_blocked_tasks = set()
        deadline = time.time() + float(timeout_seconds)
        while time.time() < deadline and bot.is_running:
            observed = bot.current_routine_task_id
            if current_task and observed != current_task:
                screenshot = f"{len(result['task_screenshots']) + 1:02d}_{current_task}_end.png"
                if _capture(client, output_dir / screenshot):
                    result["task_screenshots"].append(screenshot)
            if observed and observed != current_task:
                current_task = observed
                current_steps = ()
                if observed not in result["visited_tasks"]:
                    result["visited_tasks"].append(observed)
                screenshot = f"{len(result['task_screenshots']) + 1:02d}_{observed}.png"
                if _capture(client, output_dir / screenshot):
                    result["task_screenshots"].append(screenshot)
            elif observed is None:
                current_task = None
                current_steps = ()

            observed_steps = tuple(sorted(bot.routine_completed_steps))
            if current_task and observed_steps and observed_steps != current_steps:
                current_steps = observed_steps
                step_label = "-".join(observed_steps)
                step_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", step_label)[:80]
                screenshot = (
                    f"step_{len(result['step_screenshots']) + 1:02d}_"
                    f"{current_task}_{step_label}.png"
                )
                if _capture(client, output_dir / screenshot):
                    result["step_screenshots"].append(screenshot)

            processed = {
                task_id
                for task_id in selected_with_login
                if float(bot.routine_next_run.get(task_id, 0.0) or 0.0) > started_at + 1.0
            }
            newly_blocked = _capacity_blocked_march_tasks(
                selected_ids,
                bot.routine_tasks,
                bot.get_active_marches(),
                bot.routine_max_marches,
            ).difference(result["visited_tasks"])
            capacity_blocked_tasks.update(newly_blocked)
            processed.update(capacity_blocked_tasks)
            if processed == selected_with_login and bot.current_routine_task_id is None:
                break
            time.sleep(0.5)
        else:
            if bot.is_running:
                result["error"] = "program timeout"

        result["capacity_blocked_tasks"] = sorted(capacity_blocked_tasks)
        result["missing_tasks"] = sorted(
            selected_with_login
            .difference(result["visited_tasks"])
            .difference(capacity_blocked_tasks)
        )
        for path, group in tracked_images.items():
            actions = max(0, int(bot.stats.get(path, 0)) - initial_stats[path])
            if actions:
                result["actions_by_group"][group] = result["actions_by_group"].get(group, 0) + actions
        result["unexpected_groups"] = sorted(
            group
            for group in result["actions_by_group"]
            if group not in selected_groups and group != SYSTEM_TEMPLATE_GROUP
        )
        handler.flush()
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        result["task_failures"] = _task_failures_from_log(log_text)
        result["busy_squad_tasks"] = sorted(
            set(_busy_tasks_from_log(log_text)).union(capacity_blocked_tasks)
        )
        if (
            not result["missing_tasks"]
            and not result["unexpected_groups"]
            and not result["task_failures"]
            and not result["error"]
        ):
            result["passed"] = True
    except Exception as exc:
        logger.exception("Random live program failed")
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if bot is not None:
            if bot.adb_client:
                _capture(bot.adb_client, output_dir / "final.png")
            bot.stop()
            if bot._thread:
                bot._thread.join(timeout=5.0)
            bot.stop_schedule_thread()
        _run_hidden([ldconsole, "quit", "--index", instance.index], timeout=30)
        result["finished_at"] = datetime.now().isoformat(timespec="seconds")
        logger.removeHandler(handler)
        handler.close()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timeout", type=float, default=720.0)
    parser.add_argument("--startup-settle-seconds", type=float, default=12.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    ldconsole = find_ldconsole()
    if ldconsole is None:
        raise SystemExit("LDPlayer console not found")
    instances = {instance.index: instance for instance in list_instances(ldconsole)}
    instance = instances.get(args.index)
    if instance is None:
        raise SystemExit(f"LDPlayer instance not found: {args.index}")

    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)
    selected = _random_program(
        random.Random(seed),
        args.count,
        _march_tasks_for_account(instance.name),
    )
    output = args.output or PROJECT_ROOT / "test_runs" / f"random_{datetime.now():%Y%m%d_%H%M%S}"
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "program.json", {"seed": seed, "selected_tasks": selected})
    print(json.dumps({"seed": seed, "selected_tasks": selected}, ensure_ascii=False), flush=True)
    original_config = CONFIG_FILE.read_bytes()
    try:
        result = run_program(
            instance,
            selected,
            seed,
            output,
            args.timeout,
            args.startup_settle_seconds,
        )
    finally:
        CONFIG_FILE.write_bytes(original_config)
    _write_json(output / "report.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(output)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
