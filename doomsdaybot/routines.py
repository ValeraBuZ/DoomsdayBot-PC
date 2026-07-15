from __future__ import annotations

from copy import deepcopy
import uuid


PROFILE_NAMESPACE = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
RESOURCE_TASK_IDS = ("food", "wood", "metal", "oil")
RESOURCE_STEP_IDS = (
    "region",
    "world_search",
    "resource_icon",
    "search_button",
    "gather",
    "create_squad",
    "march",
)


DEFAULT_ROUTINE_TASKS = (
    {
        "id": "alliance_help",
        "name": "Помощь альянсу",
        "group": "Помощь альянсу",
        "category": "daily",
        "enabled": False,
        "uses_march": False,
        "priority": 10,
        "interval_minutes": 1.0,
        "timeout_seconds": 8.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
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
        "timeout_seconds": 12.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {
            "max_donations": 30,
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
        "interval_minutes": 15.0,
        "timeout_seconds": 15.0,
        "march_duration_minutes": 30.0,
        "completion_uid": "",
        "settings": {
            "max_tasks": 10,
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
        "settings": {"highest_tier": True, "collect_finished": True},
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
        "settings": {"highest_tier": True, "collect_finished": True},
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
        "settings": {"highest_tier": True, "collect_finished": True},
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
        "settings": {"highest_tier": True, "collect_finished": True},
    },
    {
        "id": "prize_hunt",
        "name": "Охота за призом",
        "group": "Охота за призом",
        "category": "marches",
        "enabled": False,
        "standalone": True,
        "uses_march": True,
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
        "settings": {"repeat": True, "level": 5},
    },
    {
        "id": "food",
        "name": "Еда",
        "group": "Еда",
        "category": "resources",
        "enabled": True,
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
        "enabled": True,
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
        "enabled": True,
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
        "enabled": True,
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
        {"key": "max_tasks", "label": "Заданий за цикл", "kind": "int", "min": 1, "max": 50},
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
        {"key": "level_min", "label": "Минимальный уровень", "kind": "int", "min": 1, "max": 50},
        {"key": "level_max", "label": "Максимальный уровень", "kind": "int", "min": 1, "max": 50},
        {"key": "stamina_reserve", "label": "Оставлять выносливости", "kind": "int", "min": 0, "max": 10000},
        {"key": "max_attacks", "label": "Максимум атак (0 = без лимита)", "kind": "int", "min": 0, "max": 1000},
    ),
    "collective_mind": (
        {"key": "level", "label": "Уровень коллективного разума", "kind": "int", "min": 1, "max": 5},
        {"key": "repeat", "label": "Повторять сбор", "kind": "bool"},
    ),
    "food": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 8},),
    "wood": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 8},),
    "metal": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 8},),
    "oil": ({"key": "resource_level", "label": "Уровень клетки", "kind": "int", "min": 1, "max": 8},),
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
    if image.get("runtime_step_mode") == "any":
        return any(step in completed for step in required)
    return all(step in completed for step in required)


def upgrade_resource_runtime_metadata(images, tasks):
    """Apply the current resource sequence to both fresh and older profiles."""
    images_by_uid = {str(image.get("uid") or ""): image for image in images}
    upgraded = 0
    for task_id in RESOURCE_TASK_IDS:
        previous_step = None
        world_search_uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:world_search"))
        for step_id in RESOURCE_STEP_IDS:
            uid = str(uuid.uuid5(PROFILE_NAMESPACE, f"{task_id}:{step_id}"))
            image = images_by_uid.get(uid)
            if image is None:
                previous_step = "world_search" if step_id == "region" else step_id
                continue
            runtime_step = "world_search" if step_id == "region" else step_id
            image["runtime_step"] = runtime_step
            image.pop("requires_runtime_steps", None)
            if step_id not in {"region", "world_search"} and previous_step:
                image["requires_runtime_steps"] = [previous_step]
            if step_id == "region":
                image["action"] = "open_world_search"
                image["next_template_uid"] = world_search_uid
                image["delay"] = 0.8
            previous_step = runtime_step
            upgraded += 1

    for task in tasks:
        if task.get("id") in RESOURCE_TASK_IDS:
            task["timeout_seconds"] = max(30.0, float(task.get("timeout_seconds", 0.0) or 0.0))
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
    group = str(source.get("group", default["group"])).strip() or default["group"]
    return {
        "id": task_id,
        "name": name,
        "group": group,
        "category": str(source.get("category", default.get("category", "custom"))),
        "enabled": bool(source.get("enabled", default.get("enabled", True))),
        "standalone": bool(source.get("standalone", default.get("standalone", False))),
        "uses_march": bool(source.get("uses_march", default.get("uses_march", False))),
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
    interval_seconds = float(task.get("interval_minutes", 1.0)) * 60.0
    return float(now) + max(6.0, interval_seconds)
