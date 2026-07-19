from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import time
import uuid


PROFILE_NAMESPACE = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
PRIZE_HUNT_SAFE_EXIT_UID = str(
    uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:safe_exit")
)
PRIZE_HUNT_REPEAT_UIDS = {
    str(uuid.uuid5(PROFILE_NAMESPACE, f"prize_hunt:{step_id}"))
    for step_id in ("again", "match", "confirm")
}
RESOURCE_TASK_IDS = ("food", "wood", "metal", "oil")
RESOURCE_RESULT_LEVELS = (6, 7)
RESOURCE_RESULT_SEARCH_REGION = (570, 340, 150, 120)
RESOURCE_STEP_IDS = (
    "region",
    "world_search",
    "resource_icon",
    "search_button",
    "gather",
    "create_squad",
    "march",
)
STRICT_RUNTIME_SEQUENCES = {
    "heal": ("open_wounded", "start_healing"),
    "train_infantry": ("queue", "building", "train"),
    "train_riders": ("queue", "building", "train"),
    "train_shooters": ("queue", "building", "train"),
    "train_vehicles": ("queue", "building", "train"),
    "zombie_hunt": (
        "world_search",
        "zombie_icon",
        "search",
        "attack",
        "create_squad",
        "march",
    ),
    "collective_mind": (
        "world_search",
        "leader_icon",
        "search",
        "rally",
        "confirm_rally",
        "march",
    ),
}
RADAR_STEP_PRIORITIES = {
    "radar_screen_guard": 1,
    "card_guard": 1,
    "forward_guard": 1,
    "open_radar": 2,
    "collect_completed": 3,
    "wait_in_progress": 5,
    "open_any_task": 10,
    "open_supply": 10,
    "open_car": 10,
    "open_zombie": 10,
    "collect_supply": 20,
    "attack_zombie": 20,
    "rescue_survivors": 20,
    "transport_supplies": 21,
    "confirm_transport": 22,
    "create_squad": 30,
    "march": 40,
    "close_region_search": 45,
    "return_shelter": 50,
    "task_person_gold_reward": 57,
    "task_car_generic_shape": 58,
    "task_person_generic_shape": 59,
    "task_special_generic_shape": 61,
    "task_supply_reward_final": 62,
    "task_car_unstarted_final": 63,
    "task_special_reward_followup": 64,
    "task_car_reward_followup": 65,
    "task_person_unstarted_followup": 66,
    "task_supply_unstarted_followup": 67,
    "task_car_unstarted_live": 70,
    "task_special_unstarted_live": 71,
    "task_skull_unstarted_live": 72,
    "task_survivor_current_live": 73,
    "task_skull_reward_current": 74,
    "task_skull_reward": 75,
    "task_car_reward": 76,
    "task_supply_ready": 77,
    "task_car_ready": 78,
    "task_zombie_ready": 79,
    "task_supply": 80,
    "task_car": 81,
    "task_zombie": 82,
    "task_car_current": 83,
    "task_skull_current": 84,
    "task_special_current": 85,
    "task_fist_current": 86,
}

RADAR_CARD_RUNTIME_STEPS = frozenset(
    {
        "radar_forward",
        "radar_action",
        "radar_squad",
        "radar_march",
    }
)


DEFAULT_ROUTINE_TASKS = (
    {
        "id": "game_login",
        "name": "Вход в игру",
        "group": "Вход в игру",
        "category": "startup",
        "enabled": False,
        "uses_march": False,
        "priority": 1,
        "interval_minutes": 1440.0,
        "timeout_seconds": 90.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {},
    },
    {
        "id": "alliance_help",
        "name": "Помощь другим игрокам",
        "group": "Помощь альянсу",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 10,
        "interval_minutes": 1.0,
        "timeout_seconds": 8.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "empty_home_is_success": True,
        "settings": {},
    },
    {
        "id": "fence_survivors",
        "name": "Выжившие у забора",
        "group": "Выжившие у забора",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 12,
        "interval_minutes": 15.0,
        "timeout_seconds": 8.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "empty_home_is_success": True,
        "settings": {},
    },
    {
        "id": "processing_factory",
        "name": "Завод по обработке",
        "group": "Завод по обработке",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 13,
        "interval_minutes": 180.0,
        "timeout_seconds": 25.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "complete_when_idle": True,
        "idle_confirmations": 1,
        "idle_completion_guard_uid": str(
            uuid.uuid5(PROFILE_NAMESPACE, "processing_factory:factory_guard")
        ),
        "settings": {},
    },
    {
        "id": "processing_contest",
        "name": "Конкурс по обработке",
        "group": "Конкурс по обработке",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 14,
        "interval_minutes": 180.0,
        "timeout_seconds": 25.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "complete_when_idle": True,
        "idle_confirmations": 1,
        "idle_completion_guard_uid": str(
            uuid.uuid5(PROFILE_NAMESPACE, "processing_contest:contest_guard")
        ),
        "settings": {},
    },
    {
        "id": "mail_rewards",
        "name": "Награды почты",
        "group": "Награды почты",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 15,
        "interval_minutes": 30.0,
        "timeout_seconds": 10.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "completion_runtime_step": "claim_reports",
        "settings": {},
    },
    {
        "id": "completed_tasks",
        "name": "Выполненные задания",
        "group": "Выполненные задания",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 18,
        "interval_minutes": 30.0,
        "timeout_seconds": 10.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "completion_runtime_step": "scroll_top_4",
        "settings": {},
    },
    {
        "id": "vip_rewards",
        "name": "Награды VIP",
        "group": "Награды VIP",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 20,
        "interval_minutes": 720.0,
        "timeout_seconds": 30.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "empty_home_is_success": True,
        "settings": {},
    },
    {
        "id": "alliance_donations",
        "name": "Пожертвования альянсу",
        "group": "Пожертвования альянсу",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 25,
        # One spent attempt is restored by the game roughly every 20 minutes.
        "interval_minutes": 20.0,
        "timeout_seconds": 30.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        # Completion is driven by the project-check limit. This sentinel prevents
        # merely opening the technology tree from being treated as success.
        "completion_runtime_step": "all_projects_checked",
        "settings": {
            "max_donations": 100,
            "max_project_checks": 5,
            "avoid_gems": True,
        },
    },
    {
        "id": "radar",
        "name": "Задания радарной станции",
        "group": "Радарная станция",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 30,
        "interval_minutes": 720.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "complete_when_idle": True,
        "idle_confirmations": 3,
        "idle_completion_guard_uid": str(
            uuid.uuid5(PROFILE_NAMESPACE, "radar:radar_screen_guard")
        ),
        "settings": {
            "max_tasks": 0,
            "fixed_utc_hours": [0, 12],
            "in_progress_retry_minutes": 5,
        },
    },
    {
        "id": "research",
        "name": "Исследования",
        "group": "Исследования",
        "category": "development",
        "enabled": False,
        "uses_march": False,
        "priority": 35,
        "interval_minutes": 5.0,
        "timeout_seconds": 15.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {
            "branch": "off",
            "use_speedups": False,
            "max_lab_checks": 1,
        },
    },
    {
        "id": "gathering_boost",
        "name": "Усиление сбора ресурсов",
        "group": "Усиление сбора ресурсов",
        "category": "development",
        "enabled": False,
        "uses_march": False,
        "priority": 40,
        "interval_minutes": 480.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {
            "boost_hours": 8,
        },
    },
    {
        "id": "heal",
        "name": "Лечение войск",
        "group": "Лечение войск",
        "category": "army",
        "enabled": False,
        "uses_march": False,
        "priority": 45,
        "interval_minutes": 1.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "empty_home_is_success": True,
        "settings": {
            "troop_count": 10000,
            "collect_finished": True,
            "repeat": True,
        },
    },
    {
        "id": "train_infantry",
        "name": "Производство: пехота",
        "group": "Производство пехоты",
        "category": "training",
        "enabled": False,
        "uses_march": False,
        "priority": 50,
        "interval_minutes": 2.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {"highest_tier": True, "collect_finished": True, "max_queue_checks": 4},
    },
    {
        "id": "train_riders",
        "name": "Производство: райдеры",
        "group": "Производство райдеров",
        "category": "training",
        "enabled": False,
        "uses_march": False,
        "priority": 50,
        "interval_minutes": 2.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {"highest_tier": True, "collect_finished": True, "max_queue_checks": 4},
    },
    {
        "id": "train_shooters",
        "name": "Производство: стрелки",
        "group": "Производство стрелков",
        "category": "training",
        "enabled": False,
        "uses_march": False,
        "priority": 50,
        "interval_minutes": 2.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {"highest_tier": True, "collect_finished": True, "max_queue_checks": 4},
    },
    {
        "id": "train_vehicles",
        "name": "Производство: машинки",
        "group": "Производство машин",
        "category": "training",
        "enabled": False,
        "uses_march": False,
        "priority": 50,
        "interval_minutes": 2.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {"highest_tier": True, "collect_finished": True, "max_queue_checks": 4},
    },
    {
        "id": "prize_hunt",
        "name": "Охота за призом",
        "group": "Охота за призом",
        "category": "marches",
        "enabled": False,
        "standalone": True,
        "uses_march": False,
        "priority": 55,
        "interval_minutes": 1.0,
        "timeout_seconds": 1800.0,
        "march_duration_minutes": 10.0,
        "completion_uid": "",
        "settings": {
            "repeat_until_stopped": True,
            "squad": 1,
        },
    },
    {
        "id": "zombie_hunt",
        "name": "Убийство зомби",
        "group": "Убийство зомби",
        "category": "marches",
        "enabled": False,
        "uses_march": True,
        "priority": 60,
        "interval_minutes": 1.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 10.0,
        "completion_uid": "",
        "settings": {
            "level_min": 1,
            "level_max": 10,
            "stamina_reserve": 0,
            "max_attacks": 0,
        },
    },
    {
        "id": "collective_mind",
        "name": "Коллективный разум",
        "group": "Коллективный разум",
        "category": "marches",
        "enabled": False,
        "uses_march": True,
        "priority": 65,
        "interval_minutes": 5.0,
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {"repeat": True, "level": 6},
    },
    {
        "id": "food",
        "name": "Еда",
        "group": "Еда",
        "category": "resources",
        "enabled": False,
        "uses_march": True,
        "priority": 100,
        "interval_minutes": 0.1,
        "timeout_seconds": 30.0,
        "march_duration_minutes": 240.0,
        "completion_uid": "",
        "settings": {"resource_level": 7},
    },
    {
        "id": "wood",
        "name": "Дерево",
        "group": "Дерево",
        "category": "resources",
        "enabled": False,
        "uses_march": True,
        "priority": 100,
        "interval_minutes": 0.1,
        "timeout_seconds": 30.0,
        "march_duration_minutes": 240.0,
        "completion_uid": "",
        "settings": {"resource_level": 7},
    },
    {
        "id": "metal",
        "name": "Металл",
        "group": "Металл",
        "category": "resources",
        "enabled": False,
        "uses_march": True,
        "priority": 100,
        "interval_minutes": 0.1,
        "timeout_seconds": 30.0,
        "march_duration_minutes": 240.0,
        "completion_uid": "",
        "settings": {"resource_level": 7},
    },
    {
        "id": "oil",
        "name": "Нефть",
        "group": "Нефть",
        "category": "resources",
        "enabled": False,
        "uses_march": True,
        "priority": 100,
        "interval_minutes": 0.1,
        "timeout_seconds": 10.0,
        "march_duration_minutes": 240.0,
        "completion_uid": "",
        "settings": {"resource_level": 7},
    },
)


TASK_SETTING_SPECS = {
    "alliance_donations": (
        {"key": "max_donations", "label": "Максимум пожертвований", "kind": "int", "min": 1, "max": 100},
        {"key": "max_project_checks", "label": "Проектов за цикл", "kind": "int", "min": 1, "max": 20},
        {"key": "avoid_gems", "label": "Не тратить алмазы", "kind": "bool"},
    ),
    "radar": (
        {"key": "max_tasks", "label": "Лимит заданий (0 = до конца)", "kind": "int", "min": 0, "max": 100},
    ),
    "research": (
        {
            "key": "branch",
            "label": "Приоритет",
            "kind": "choice",
            "choices": (("off", "Отключено"), ("economy", "Экономика"), ("war", "Война"), ("any", "Любое")),
        },
        {"key": "use_speedups", "label": "Использовать ускорения", "kind": "bool"},
    ),
    "gathering_boost": (
        {
            "key": "boost_hours",
            "label": "Длительность усиления",
            "kind": "choice",
            "choices": ((8, "8 часов"), (24, "24 часа")),
        },
    ),
    "heal": (
        {"key": "troop_count", "label": "Количество войск", "kind": "int", "min": 1, "max": 1000000},
        {"key": "collect_finished", "label": "Собирать вылеченных", "kind": "bool"},
        {"key": "repeat", "label": "Повторять лечение", "kind": "bool"},
    ),
    "prize_hunt": (
        {"key": "repeat_until_stopped", "label": "Повторять до остановки", "kind": "bool"},
        {"key": "squad", "label": "Номер отряда", "kind": "int", "min": 1, "max": 5},
    ),
    "zombie_hunt": (
        {"key": "stamina_reserve", "label": "Оставлять выносливости", "kind": "int", "min": 0, "max": 10000},
        {"key": "max_attacks", "label": "Максимум атак (0 = без лимита)", "kind": "int", "min": 0, "max": 1000},
    ),
    "collective_mind": (
        {"key": "repeat", "label": "Повторять сбор", "kind": "bool"},
        {
            "key": "level",
            "label": "Уровень",
            "kind": "choice",
            "choices": ((6, "6"), (7, "7")),
        },
    ),
    "food": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 7},),
    "wood": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 7},),
    "metal": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 7},),
    "oil": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 7},),
}


def default_routine_tasks():
    return deepcopy(list(DEFAULT_ROUTINE_TASKS))


def task_setting_specs(task_id):
    return deepcopy(list(TASK_SETTING_SPECS.get(task_id, ())))


def runtime_step_is_ready(image, completed_steps):
    """Return whether an image's prerequisite runtime steps were completed."""
    completed = {str(step) for step in completed_steps}
    own_step = str(image.get("runtime_step") or "")
    if own_step and own_step in completed and not image.get("repeat_runtime_step", False):
        return False
    required = image.get("requires_runtime_steps", ())
    if isinstance(required, str):
        required = (required,)
    required = tuple(str(step) for step in required if str(step))
    if not required:
        return True
    # Strict UI flows may be resumed while the game is already showing a later
    # dialog (for example, the squad screen after a slow map transition).
    if not completed and image.get("allow_runtime_resume", False):
        return True
    if image.get("runtime_step_mode") == "any":
        return any(step in completed for step in required)
    return all(step in completed for step in required)


def setting_requirement_matches(image, settings):
    """Check a template setting, optionally allowing a safer longer duration."""
    key = str(image.get("required_setting_key") or "")
    if not key:
        return True
    required = image.get("required_setting_value")
    current = (settings or {}).get(key)
    if str(current) == str(required):
        return True
    if not image.get("allow_higher_setting_fallback"):
        return False
    try:
        return float(required) > float(current)
    except (TypeError, ValueError):
        return False


def gathering_boost_duration_hours(completed_steps, configured_hours=8.0):
    """Return the duration that was actually selected for a gathering boost."""
    completed = {str(step) for step in (completed_steps or ())}
    if "boost_24h" in completed:
        return 24.0
    if "boost_8h" in completed:
        return 8.0
    try:
        return max(1.0, float(configured_hours))
    except (TypeError, ValueError):
        return 8.0


def gathering_boost_active_until(task, now=None):
    """Return a future persisted boost deadline, or zero when it is inactive."""
    try:
        deadline = float((task or {}).get("settings", {}).get("active_until", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    current = time.time() if now is None else float(now)
    return deadline if deadline > current else 0.0


def completed_runtime_steps_for_image(image):
    """Return the current step and any predecessors implied by its screen."""
    implied = image.get("implied_runtime_steps", ())
    if isinstance(implied, str):
        implied = (implied,)
    completed = {str(step) for step in implied if str(step)}
    own_step = str(image.get("runtime_step") or "")
    if own_step:
        completed.add(own_step)
    return completed


def reset_radar_card_runtime_steps(completed_steps):
    """Forget the previous radar card before opening another marker."""
    completed_steps.difference_update(RADAR_CARD_RUNTIME_STEPS)


def image_is_allowed_for_routine(image, task_id, routine_started=False):
    """Return whether a shared system template may run in this routine."""
    task_id = str(task_id or "")
    only = image.get("only_routine_ids", ())
    if isinstance(only, str):
        only = (only,)
    only_ids = {str(item) for item in only if str(item)}
    if only_ids and task_id not in only_ids:
        return False
    # Startup banners are intentionally handled only by the opt-in login task.
    # Matching them during healing or training can open the rotating event tile.
    if image.get("startup_only", False) and task_id != "game_login":
        return False
    if routine_started and image.get("startup_only", False):
        return False
    disabled = image.get("disabled_routine_ids", ())
    if isinstance(disabled, str):
        disabled = (disabled,)
    disabled_ids = {str(item) for item in disabled if str(item)}
    return task_id not in disabled_ids


def prize_hunt_branch_allows_image(image, repeat_until_stopped):
    """Keep the mutually exclusive Exit and Again result branches separate."""
    uid = str(image.get("uid") or "")
    if uid == PRIZE_HUNT_SAFE_EXIT_UID:
        return not bool(repeat_until_stopped)
    if uid in PRIZE_HUNT_REPEAT_UIDS:
        return bool(repeat_until_stopped)
    return True


def no_action_retry_delay(task):
    """Use a bounded retry delay when a task timed out without any action."""
    interval_seconds = float(task.get("interval_minutes", 1.0)) * 60.0
    return max(30.0, min(300.0, interval_seconds))


def routine_home_recovery_due(task, had_action, attempted, idle_seconds):
    """Recover a newly started task from an unrelated leftover screen."""
    timeout = max(1.0, float(task.get("timeout_seconds", 8.0) or 8.0))
    recovery_delay = min(12.0, timeout)
    can_recover = bool(task.get("uses_march", False)) or task.get("id") in {
        "heal",
        "research",
        "train_infantry",
        "train_riders",
        "train_shooters",
        "train_vehicles",
    }
    return bool(
        can_recover
        and not had_action
        and not attempted
        and float(idle_seconds) >= recovery_delay
    )


def routine_idle_screen_recovery_due(
    task,
    had_action,
    guard_visible,
    attempted,
    outside_seconds,
):
    """Recover an idle-completion task that became stuck on another screen."""
    timeout = max(1.0, float(task.get("timeout_seconds", 8.0) or 8.0))
    recovery_delay = max(45.0, min(90.0, timeout * 3.0))
    return bool(
        task.get("complete_when_idle")
        and had_action
        and not guard_visible
        and not attempted
        and float(outside_seconds) >= recovery_delay
    )


def routine_requires_settlement(task):
    """Return whether a task must run inside the player's settlement."""
    return str(task.get("category") or "") in {
        "daily",
        "development",
        "army",
        "training",
    }


def routine_march_context_key(input_backend, adb_serial, account_id):
    """Build a stable scope for locally estimated march deadlines."""
    backend = "adb" if str(input_backend or "").lower() == "adb" else "screen"
    serial = str(adb_serial or "desktop").strip() or "desktop"
    account = str(account_id or "default").strip() or "default"
    return f"{backend}:{serial}:{account}"


def effective_active_marches(observed, estimated, confirmed_floor, now, grace_until):
    """Keep newly confirmed marches occupied while the game counter catches up."""
    estimated = max(0, int(estimated))
    if observed is None:
        return estimated
    observed = max(0, int(observed))
    if float(now) < float(grace_until):
        return max(observed, estimated, max(0, int(confirmed_floor)))
    return observed


def reconcile_march_deadlines(deadlines, observed, now, grace_until):
    """Drop stale local reservations after the visible game counter disproves them."""
    active = [float(deadline) for deadline in deadlines if float(deadline) > float(now)]
    if observed is None or float(now) < float(grace_until):
        return active
    observed = max(0, int(observed))
    if observed >= len(active):
        return active
    return active[:observed]


def no_available_squad_wait_exceeded(task, completed_steps, idle_seconds, grace_seconds=8.0):
    """Detect a squad screen that never exposes the final march button."""
    completed = {str(step) for step in completed_steps}
    return bool(
        task.get("uses_march", False)
        and "create_squad" in completed
        and "march" not in completed
        and float(idle_seconds) >= float(grace_seconds)
    )


def resource_search_retry_due(task, completed_steps, attempts, max_attempts=3):
    """Retry a resource search when the selected map cell cannot be gathered."""
    completed = {str(step) for step in completed_steps}
    return bool(
        task.get("id") in RESOURCE_TASK_IDS
        and "search_button" in completed
        and "gather" not in completed
        and int(attempts) < int(max_attempts)
    )


def radar_marker_was_confirmed(uid, x, y, confirmed_keys, radius=12):
    """Match an animated radar marker to a previously confirmed deployment."""
    marker_uid = str(uid or "")
    radius_squared = float(radius) ** 2
    for key in confirmed_keys:
        if not isinstance(key, (tuple, list)) or len(key) != 3:
            continue
        key_uid, key_x, key_y = key
        if str(key_uid or "") != marker_uid:
            continue
        if (float(key_x) - float(x)) ** 2 + (float(key_y) - float(y)) ** 2 <= radius_squared:
            return True
    return False


def upgrade_resource_runtime_metadata(images, tasks):
    """Apply the current resource sequence to both fresh and older profiles."""
    images_by_uid = {str(image.get("uid") or ""): image for image in images}
    upgraded = 0
    for level in RESOURCE_RESULT_LEVELS:
        observer_uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"resource_result_level:{level}"))
        observer = images_by_uid.get(observer_uid)
        if observer is not None:
            observer["search_region"] = list(RESOURCE_RESULT_SEARCH_REGION)
            observer["confidence"] = 0.65

    for task_id in RESOURCE_TASK_IDS:
        previous_step = None
        prior_runtime_steps = []
        world_search_uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:world_search"))
        for step_id in RESOURCE_STEP_IDS:
            uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:{step_id}"))
            image = images_by_uid.get(uid)
            if image is None:
                previous_step = "world_search" if step_id == "region" else step_id
                continue
            runtime_step = "world_search" if step_id == "region" else step_id
            image["runtime_step"] = runtime_step
            image["allow_runtime_resume"] = True
            # Every free march reuses the same resource buttons. Keep anti-loop
            # protection within one pass without blocking the next scheduled pass.
            image["allow_repeat"] = True
            image["block_seconds"] = 2.0
            image["implied_runtime_steps"] = list(dict.fromkeys(prior_runtime_steps))
            image.pop("requires_runtime_steps", None)
            if step_id not in {"region", "world_search"} and previous_step:
                image["requires_runtime_steps"] = [previous_step]
            if step_id == "search_button":
                # A selected resource icon has a different appearance, so the
                # visible search button is also a safe resume point.
                image["requires_runtime_steps"] = ["world_search"]
            if step_id == "region":
                image["action"] = "open_world_search"
                image["next_template_uid"] = world_search_uid
                image["delay"] = 0.8
                image["settlement_screen_marker"] = True
            if step_id == "gather":
                image["expected_result_level_setting"] = "resource_level"
                image["result_level_template_uids"] = {
                    str(level): str(
                        uuid.uuid5(PROFILE_NAMESPACE, f"resource_result_level:{level}")
                    )
                    for level in RESOURCE_RESULT_LEVELS
                }
            if step_id == "march":
                image["confirm_disappears"] = True
            previous_step = runtime_step
            prior_runtime_steps.append(runtime_step)
            upgraded += 1

    for task in tasks:
        if task.get("id") in RESOURCE_TASK_IDS:
            settings = task.setdefault("settings", {})
            settings["resource_level"] = min(
                7,
                max(1, int(settings.get("resource_level", 7) or 7)),
            )
            task["timeout_seconds"] = max(30.0, float(task.get("timeout_seconds", 0.0) or 0.0))
    return upgraded


def select_best_resource_result_level(matches):
    """Return the level with the strongest validated template match."""
    candidates = []
    for level, confidence in matches:
        try:
            candidates.append((float(confidence), int(level)))
        except (TypeError, ValueError):
            continue
    if not candidates:
        return None
    return max(candidates)[1]


def upgrade_repeatable_claim_metadata(images, tasks):
    """Keep claim screens open until every available free action is exhausted."""
    images_by_uid = {str(image.get("uid") or ""): image for image in images}
    upgraded = 0

    alliance_donate_uid = str(
        uuid.uuid5(PROFILE_NAMESPACE, "alliance_donations:donate_resources")
    )
    alliance_close_uid = str(
        uuid.uuid5(PROFILE_NAMESPACE, "alliance_donations:close_project")
    )
    alliance_open_uid = str(
        uuid.uuid5(PROFILE_NAMESPACE, "alliance_donations:open_alliance")
    )
    alliance_technology_uid = str(
        uuid.uuid5(PROFILE_NAMESPACE, "alliance_donations:open_technology")
    )
    alliance_marked_uid = str(
        uuid.uuid5(PROFILE_NAMESPACE, "alliance_donations:select_marked_project")
    )
    alliance_project_uids = [
        str(uuid.uuid5(PROFILE_NAMESPACE, f"alliance_donations:{step_id}"))
        for step_id in (
            "select_project_construction",
            "select_project_research",
            "select_project_zombies",
            "select_project_elite",
            "select_project_fire_water",
        )
    ]
    vip_claim_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "vip_rewards:claim_chest"))
    vip_dismiss_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "vip_rewards:dismiss_info"))
    vip_receive_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "vip_rewards:receive_free"))
    vip_close_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "vip_rewards:close_vip"))

    repeatable = {
        alliance_donate_uid: 0.8,
        vip_claim_uid: 1.0,
        vip_dismiss_uid: 0.8,
        vip_receive_uid: 1.0,
    }
    for uid, block_seconds in repeatable.items():
        image = images_by_uid.get(uid)
        if image is None:
            continue
        image["allow_repeat"] = True
        image["block_seconds"] = block_seconds
        if uid == vip_receive_uid:
            image["completes_routine"] = True
        upgraded += 1

    guarded_closers = {
        alliance_close_uid: [alliance_donate_uid],
        vip_close_uid: [vip_claim_uid, vip_dismiss_uid, vip_receive_uid],
    }
    for uid, guard_uids in guarded_closers.items():
        image = images_by_uid.get(uid)
        if image is None:
            continue
        existing = image.get("skip_if_visible_uids") or []
        if isinstance(existing, str):
            existing = [existing]
        image["skip_if_visible_uids"] = list(dict.fromkeys([*existing, *guard_uids]))
        upgraded += 1

    donation_priorities = {
        alliance_open_uid: 5,
        alliance_technology_uid: 10,
        alliance_marked_uid: 15,
        alliance_donate_uid: 30,
        alliance_close_uid: 40,
    }
    donation_priorities.update(
        {uid: 20 + index for index, uid in enumerate(alliance_project_uids)}
    )
    for uid, priority in donation_priorities.items():
        image = images_by_uid.get(uid)
        if image is None:
            continue
        image["routine_priority"] = priority
        if uid == alliance_marked_uid:
            image.update(
                {
                    "action": "alliance_marked_project",
                    "confidence": 0.78,
                    "orb_match_threshold": 3,
                    "delay": 1.5,
                }
            )
            image.pop("allow_repeat", None)
        if uid in alliance_project_uids:
            image["confidence"] = min(
                0.74,
                float(image.get("confidence", 0.88) or 0.88),
            )
            image["orb_match_threshold"] = min(
                3,
                int(image.get("orb_match_threshold", 3) or 3),
            )
        upgraded += 1

    for task in tasks:
        if task.get("id") == "alliance_donations":
            settings = task.setdefault("settings", {})
            settings["max_donations"] = max(
                100,
                int(settings.get("max_donations", 0) or 0),
            )
            settings["max_project_checks"] = max(
                5,
                int(settings.get("max_project_checks", 0) or 0),
            )
            task["timeout_seconds"] = max(
                30.0,
                float(task.get("timeout_seconds", 30.0) or 30.0),
            )
            task["completion_runtime_step"] = "all_projects_checked"
        elif task.get("id") == "collective_mind":
            settings = task.setdefault("settings", {})
            level = int(settings.get("level", 6) or 6)
            settings["level"] = 7 if level == 7 else 6

    return upgraded


def upgrade_strict_runtime_metadata(images, tasks):
    """Apply safe step ordering to healing, training and hunt routines."""
    images_by_uid = {str(image.get("uid") or ""): image for image in images}
    upgraded = 0

    for task_id, sequence in STRICT_RUNTIME_SEQUENCES.items():
        is_hunt = task_id in {"zombie_hunt", "collective_mind"}
        if is_hunt:
            region_uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:region"))
            world_search_uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:world_search"))
            region_image = images_by_uid.get(region_uid)
            if region_image is not None:
                region_image.update(
                    {
                        "action": "open_world_search",
                        "next_template_uid": world_search_uid,
                        "runtime_step": "world_search",
                        "routine_priority": 9,
                    }
                )
                region_image.pop("requires_runtime_steps", None)
                upgraded += 1

        previous_step = None
        for index, step_id in enumerate(sequence):
            uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:{step_id}"))
            image = images_by_uid.get(uid)
            if image is None:
                previous_step = step_id
                continue
            image["runtime_step"] = step_id
            image["routine_priority"] = 10 + index * 10
            image["allow_runtime_resume"] = True
            image["implied_runtime_steps"] = list(sequence[:index])
            if step_id == "march":
                image["confirm_disappears"] = True
            if task_id.startswith("train_") and step_id == "queue":
                image["repeat_runtime_step"] = True
                image["dynamic_building_search"] = True
                image["limit_key"] = "max_queue_checks"
                image["defer_when_limit_reached"] = True
            image.pop("requires_runtime_steps", None)
            selected_training_building = (
                task_id.startswith("train_") and step_id == "building"
            )
            if previous_step and not selected_training_building:
                image["requires_runtime_steps"] = [previous_step]
            previous_step = step_id
            upgraded += 1

    research_queue_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "research:queue"))
    research_queue = images_by_uid.get(research_queue_uid)
    if research_queue is not None:
        research_queue.update(
            {
                "limit_key": "max_lab_checks",
                "defer_when_limit_reached": True,
            }
        )
        upgraded += 1

    active_boost_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "gathering_boost:active"))
    active_boost = images_by_uid.get(active_boost_uid)
    if active_boost is not None:
        active_boost.update(
            {
                "confidence": 0.75,
                "orb_match_threshold": 3,
                "completes_routine": True,
                "routine_priority": 1,
            }
        )
        upgraded += 1

    boost_24h_uid = str(uuid.uuid5(PROFILE_NAMESPACE, "gathering_boost:boost_24h"))
    boost_24h = images_by_uid.get(boost_24h_uid)
    if boost_24h is not None:
        # Never consume a 24-hour item when the user selected 8 hours.
        boost_24h.pop("allow_higher_setting_fallback", None)
        upgraded += 1

    mail_requirements = {
        "open_mail": (),
        "select_system": ("open_mail",),
        "claim_system": ("select_system",),
        # Claim buttons are optional when a mailbox category is already empty.
        "select_alliance": ("select_system",),
        "claim_alliance": ("select_alliance",),
        "select_reports": ("select_alliance",),
        "claim_reports": ("select_reports",),
    }
    for index, (step_id, required_steps) in enumerate(mail_requirements.items()):
        image = images_by_uid.get(
            str(uuid.uuid5(PROFILE_NAMESPACE, f"mail_rewards:{step_id}"))
        )
        if image is None:
            continue
        image["runtime_step"] = step_id
        image["routine_priority"] = 10 + index * 10
        if required_steps:
            image["requires_runtime_steps"] = list(required_steps)
        else:
            image.pop("requires_runtime_steps", None)
        upgraded += 1

    for task in tasks:
        if task.get("id") in STRICT_RUNTIME_SEQUENCES:
            task["timeout_seconds"] = max(
                20.0,
                float(task.get("timeout_seconds", 0.0) or 0.0),
            )
        if task.get("id") == "heal":
            task["empty_home_is_success"] = True
        if str(task.get("id") or "").startswith("train_"):
            task.setdefault("settings", {}).setdefault("max_queue_checks", 4)
        if task.get("id") == "research":
            task.setdefault("settings", {}).setdefault("max_lab_checks", 1)
        if task.get("id") == "mail_rewards":
            task["completion_runtime_step"] = "claim_reports"

    # Claiming a main mission can move the game directly to the daily tab.
    # Allow the first guarded swipe to resume from that screen even when the
    # explicit select_daily click was therefore never observed.
    first_daily_scroll = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "completed_tasks:scroll_daily_1"))
    )
    if first_daily_scroll is not None:
        first_daily_scroll["requires_runtime_steps"] = ["open_tasks"]
        first_daily_scroll["implied_runtime_steps"] = ["select_daily"]
        upgraded += 1
    return upgraded


def upgrade_prize_hunt_metadata(images, tasks):
    """Keep the defeat and repeat buttons on separate safe branches."""
    images_by_uid = {str(image.get("uid") or ""): image for image in images}
    upgraded = 0

    open_squad = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:open_squad"))
    )
    if open_squad is not None:
        open_squad.update(
            {
                "action": "prize_start_or_prepare",
                "description": "Запустить охоту или настроить отряд",
                "grayscale": True,
                "confidence": min(
                    0.84,
                    float(open_squad.get("confidence", 0.88) or 0.88),
                ),
            }
        )
        upgraded += 1

    prepare = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:prepare"))
    )
    if prepare is not None:
        prepare.update(
            {
                "action": "prize_prepare",
                "description": "Заполнить отряд для охоты",
            }
        )
        upgraded += 1

    safe_exit = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:safe_exit"))
    )
    if safe_exit is not None:
        safe_exit.update(
            {
                "required_setting_key": "repeat_until_stopped",
                "required_setting_value": False,
                "complete_if_setting_false": "repeat_until_stopped",
                "routine_priority": 20,
            }
        )
        upgraded += 1

    revive_exit = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:safe_exit_current"))
    )
    if revive_exit is not None:
        revive_exit.pop("required_setting_key", None)
        revive_exit.pop("required_setting_value", None)
        revive_exit.pop("complete_if_setting_false", None)
        revive_exit["routine_priority"] = 10
        upgraded += 1

    for priority, step_id in enumerate(("again", "match", "confirm"), start=20):
        image = images_by_uid.get(
            str(uuid.uuid5(PROFILE_NAMESPACE, f"prize_hunt:{step_id}"))
        )
        if image is None:
            continue
        image.update(
            {
                "required_setting_key": "repeat_until_stopped",
                "required_setting_value": True,
                "routine_priority": priority,
            }
        )
        upgraded += 1

    step_requirements = {
        "campaign": (),
        "event": ("campaign",),
        "enter": ("event",),
        "open_squad": ("enter",),
        "prepare": ("open_squad",),
        "deploy": ("prepare",),
        "safe_exit_current": ("deploy",),
        "safe_exit": ("safe_exit_current",),
        "again": ("safe_exit_current",),
        "match": ("again",),
        "confirm": ("match",),
    }
    repeatable_steps = {"safe_exit_current", "safe_exit", "again", "match", "confirm"}
    for priority, (step_id, required_steps) in enumerate(step_requirements.items(), start=10):
        image = images_by_uid.get(
            str(uuid.uuid5(PROFILE_NAMESPACE, f"prize_hunt:{step_id}"))
        )
        if image is None:
            continue
        image["runtime_step"] = step_id
        image["routine_priority"] = priority
        image["repeat_runtime_step"] = step_id in repeatable_steps
        image.pop("allow_runtime_resume", None)
        image.pop("requires_runtime_steps", None)
        if required_steps:
            image["requires_runtime_steps"] = list(required_steps)

    deploy_image = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:deploy"))
    )
    if deploy_image is not None:
        # A previously saved squad can enter immediately; an empty squad must
        # first pass through prize_prepare. Both states are valid.
        deploy_image["requires_runtime_steps"] = ["prepare", "open_squad"]
        deploy_image["runtime_step_mode"] = "any"

    outcome_steps = ("safe_exit_current", "safe_exit", "again")
    for step_id in outcome_steps:
        image = images_by_uid.get(
            str(uuid.uuid5(PROFILE_NAMESPACE, f"prize_hunt:{step_id}"))
        )
        if image is None:
            continue
        image["allow_runtime_resume"] = True
        image["runtime_step_mode"] = "any"
        if step_id == "safe_exit_current":
            image["requires_runtime_steps"] = ["deploy", "enter"]
        else:
            image["requires_runtime_steps"] = ["safe_exit_current", "deploy", "enter"]

    enter_image = images_by_uid.get(
        str(uuid.uuid5(PROFILE_NAMESPACE, "prize_hunt:enter"))
    )
    if enter_image is not None:
        # The event periodically changes the button caption while retaining
        # the same card and placement. The strict event prerequisite prevents
        # this relaxed threshold from matching outside the hunt screen.
        enter_image["confidence"] = min(
            0.74,
            float(enter_image.get("confidence", 0.8) or 0.8),
        )

    for task in tasks:
        if task.get("id") == "prize_hunt":
            task["timeout_seconds"] = max(
                1800.0,
                float(task.get("timeout_seconds", 0.0) or 0.0),
            )
    return upgraded


def upgrade_radar_runtime_metadata(images, tasks):
    """Prioritize the current radar screen before selecting another map marker."""
    images_by_uid = {str(image.get("uid") or ""): image for image in images}
    upgraded = 0
    for step_id, priority in RADAR_STEP_PRIORITIES.items():
        uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"radar:{step_id}"))
        image = images_by_uid.get(uid)
        if image is None:
            continue
        image["routine_priority"] = priority
        if step_id == "open_radar":
            image["requires_settlement_screen"] = True
        if step_id == "wait_in_progress":
            image["action"] = "radar_defer_in_progress"
            image["delay"] = 0.5
        if step_id == "march":
            image["confirm_disappears"] = True
            image["confirms_radar_marker"] = True
        # Radar is complete only after no actionable templates remain. A positive
        # max_tasks value is retained as a setting for compatibility, not as an
        # early-completion trigger.
        if image.get("limit_key") == "max_tasks":
            image.pop("limit_key", None)
        if step_id.startswith("task_"):
            image["runtime_step"] = "radar_marker"
            image["repeat_runtime_step"] = True
            image["prevents_idle_completion"] = True
            # Marker colors vary slightly between accounts. The red notification
            # dot plus the existing color/ORB checks still guards the click.
            image["confidence"] = min(0.68, float(image.get("confidence", 0.82)))
            image["orb_match_threshold"] = min(
                3,
                int(image.get("orb_match_threshold", 3) or 3),
            )
            # Retry markers that did not open, then extend the block only after
            # the final deployment button confirms a real radar march.
            image["allow_repeat"] = True
            image["block_seconds"] = 8.0
        elif step_id in {"open_any_task", "open_supply", "open_car", "open_zombie"}:
            image["runtime_step"] = "radar_forward"
            image["repeat_runtime_step"] = True
        elif step_id in {
            "collect_completed",
            "collect_supply",
            "attack_zombie",
            "rescue_survivors",
            "transport_supplies",
            "confirm_transport",
        }:
            image["runtime_step"] = "radar_action"
            image["repeat_runtime_step"] = True
            image["requires_runtime_steps"] = ["radar_forward"]
            image["delay"] = max(1.5, float(image.get("delay", 0.0) or 0.0))
        elif step_id == "create_squad":
            image["runtime_step"] = "radar_squad"
            image["requires_runtime_steps"] = ["radar_action"]
            image["allow_runtime_resume"] = True
        elif step_id == "march":
            image["runtime_step"] = "radar_march"
            image["requires_runtime_steps"] = ["radar_squad", "radar_action"]
            image["runtime_step_mode"] = "any"
            image["allow_runtime_resume"] = True
        elif step_id == "close_region_search":
            image["requires_runtime_steps"] = ["radar_action", "radar_march"]
            image["runtime_step_mode"] = "any"
        elif step_id == "return_shelter":
            image["action"] = "radar_return_shelter"
            image["requires_runtime_steps"] = ["radar_action", "radar_march"]
            image["runtime_step_mode"] = "any"
        upgraded += 1

    for task in tasks:
        if task.get("id") == "radar":
            task["timeout_seconds"] = max(12.0, float(task.get("timeout_seconds", 0.0) or 0.0))
            task["interval_minutes"] = 720.0
            task["complete_when_idle"] = True
            task["idle_confirmations"] = max(3, int(task.get("idle_confirmations", 0) or 0))
            task["idle_completion_guard_uid"] = str(
                uuid.uuid5(PROFILE_NAMESPACE, "radar:radar_screen_guard")
            )
            task.setdefault("settings", {})["fixed_utc_hours"] = [0, 12]
            task["settings"].setdefault("in_progress_retry_minutes", 5)
    return upgraded


def _positive_float(value, default, minimum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return max(float(minimum), parsed)


def _normalize_settings(source, default):
    result = deepcopy(default or {})
    supplied = source if isinstance(source, dict) else {}
    result.update(supplied)
    return result


def _normalize_task(source, default):
    task_id = str(source.get("id", default["id"])).strip() or default["id"]
    name = str(source.get("name", default.get("name", task_id))).strip() or task_id
    if task_id == "alliance_help" and name == "Помощь альянсу":
        name = "Помощь другим игрокам"
    group = str(source.get("group", default["group"])).strip() or default["group"]
    uses_march = bool(source.get("uses_march", default.get("uses_march", False)))
    if task_id == "prize_hunt":
        # Prize Hunt uses its own event squad and is available even when all
        # regular world marches are occupied. This also migrates old configs.
        uses_march = False
    return {
        "id": task_id,
        "name": name,
        "group": group,
        "category": str(source.get("category", default.get("category", "custom"))),
        "enabled": bool(source.get("enabled", default.get("enabled", True))),
        "standalone": bool(source.get("standalone", default.get("standalone", False))),
        "uses_march": uses_march,
        "priority": int(_positive_float(source.get("priority"), default.get("priority", 100), 1)),
        "interval_minutes": _positive_float(
            source.get("interval_minutes"),
            default.get("interval_minutes", 1.0),
            0.1,
        ),
        "timeout_seconds": _positive_float(
            source.get("timeout_seconds"),
            default.get("timeout_seconds", 8.0),
            1.0,
        ),
        "march_duration_minutes": _positive_float(
            source.get("march_duration_minutes"),
            default.get("march_duration_minutes", 30.0),
            1.0,
        ),
        "completion_uid": str(source.get("completion_uid", "") or ""),
        "completion_runtime_step": str(
            source.get(
                "completion_runtime_step",
                default.get("completion_runtime_step", ""),
            )
            or ""
        ),
        "complete_when_idle": bool(
            source.get("complete_when_idle", default.get("complete_when_idle", False))
        ),
        "empty_home_is_success": task_id in {"fence_survivors", "vip_rewards"} or bool(
            source.get(
                "empty_home_is_success",
                default.get("empty_home_is_success", False),
            )
        ),
        "idle_confirmations": int(
            _positive_float(
                source.get("idle_confirmations"),
                default.get("idle_confirmations", 1),
                1,
            )
        ),
        "idle_completion_guard_uid": str(
            source.get(
                "idle_completion_guard_uid",
                default.get("idle_completion_guard_uid", ""),
            )
            or ""
        ),
        "settings": _normalize_settings(source.get("settings"), default.get("settings")),
    }


def normalize_routine_tasks(raw_tasks):
    """Return safe built-in settings and preserve user-created scenarios."""
    raw_by_id = {}
    if isinstance(raw_tasks, list):
        raw_by_id = {
            item.get("id"): item
            for item in raw_tasks
            if isinstance(item, dict) and item.get("id")
        }

    normalized = []
    built_in_ids = {item["id"] for item in DEFAULT_ROUTINE_TASKS}
    for default in DEFAULT_ROUTINE_TASKS:
        source = raw_by_id.get(default["id"], {})
        normalized.append(_normalize_task(source, default))

    if isinstance(raw_tasks, list):
        for source in raw_tasks:
            if not isinstance(source, dict) or source.get("id") in built_in_ids:
                continue
            fallback = {
                "id": str(source.get("id") or "custom"),
                "name": "Новая задача",
                "group": "Новая задача",
                "category": "custom",
                "enabled": True,
                "uses_march": False,
                "priority": 100,
                "interval_minutes": 1.0,
                "timeout_seconds": 8.0,
                "march_duration_minutes": 30.0,
                "settings": {},
            }
            normalized.append(_normalize_task(source, fallback))
    return normalized


def effective_task_group(task):
    if task.get("id") == "research":
        return "Исследования"
    return task.get("group", "")


def is_task_effectively_enabled(task):
    if not task.get("enabled", False):
        return False
    if task.get("id") == "research":
        return task.get("settings", {}).get("branch", "off") != "off"
    return True


def pick_due_task_index(tasks, next_run, start_index, now, active_marches=0, max_marches=5):
    """Pick a due task by priority and cyclic order without exceeding marches."""
    if not tasks:
        return None
    start_index = int(start_index or 0) % len(tasks)
    candidates = []
    for offset in range(len(tasks)):
        index = (start_index + offset) % len(tasks)
        task = tasks[index]
        if not is_task_effectively_enabled(task):
            continue
        if task.get("uses_march", False) and int(active_marches) >= int(max_marches):
            continue
        if float(next_run.get(task["id"], 0.0)) <= float(now):
            candidates.append((int(task.get("priority", 100)), offset, index))
    return min(candidates)[2] if candidates else None


def next_due_task(tasks, next_run, now, active_marches=0, max_marches=5):
    enabled = [
        task for task in tasks
        if is_task_effectively_enabled(task)
        and (not task.get("uses_march", False) or int(active_marches) < int(max_marches))
    ]
    if not enabled:
        return None, None
    task = min(enabled, key=lambda item: float(next_run.get(item["id"], 0.0)))
    wait_seconds = max(0.0, float(next_run.get(task["id"], 0.0)) - float(now))
    return task, wait_seconds


def next_run_after_finish(task, now):
    fixed_utc_hours = task.get("settings", {}).get("fixed_utc_hours", ())
    if fixed_utc_hours:
        return next_fixed_utc_run(now, fixed_utc_hours)
    interval_seconds = float(task.get("interval_minutes", 1.0)) * 60.0
    return float(now) + max(6.0, interval_seconds)


def next_run_after_radar_pass(task, now, has_in_progress=False):
    """Retry deferred radar marches soon, otherwise wait for the fixed reset."""
    if task.get("id") == "radar" and has_in_progress:
        retry_minutes = _positive_float(
            task.get("settings", {}).get("in_progress_retry_minutes"),
            5.0,
            1.0,
        )
        return float(now) + retry_minutes * 60.0
    return next_run_after_finish(task, now)


def next_fixed_utc_run(now, hours):
    """Return the next configured UTC hour, never the current occurrence."""
    normalized_hours = sorted({int(hour) % 24 for hour in hours})
    if not normalized_hours:
        return float(now)

    current = datetime.fromtimestamp(float(now), tz=timezone.utc)
    for day_offset in (0, 1):
        day = current.date() + timedelta(days=day_offset)
        for hour in normalized_hours:
            candidate = datetime(
                day.year,
                day.month,
                day.day,
                hour,
                tzinfo=timezone.utc,
            )
            if candidate > current:
                return candidate.timestamp()
    raise RuntimeError("Unable to calculate the next fixed UTC run")
