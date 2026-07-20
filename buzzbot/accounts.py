from __future__ import annotations

from copy import deepcopy
import re
import uuid
import xml.etree.ElementTree as ET


_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def _account_id(name):
    value = str(name or "account").strip().lower()
    safe = "".join(char if char.isalnum() else "_" for char in value).strip("_")
    return safe or uuid.uuid4().hex[:8]


def default_account_profiles(serial="emulator-5564"):
    return [
        {
            "id": "phoenix675",
            "name": "Phoenix675",
            "enabled": True,
            "ldplayer_index": 5,
            "adb_serial": str(serial or "emulator-5564"),
            "session_minutes": 30.0,
            "chooser_index": 2,
            "switch_group": "Аккаунт: Phoenix675",
            "switch_completion_uid": "",
            "task_enabled": {},
            "task_settings": {},
            "routine_next_run": {},
        }
    ]


def _number(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = float(default)
    return min(float(maximum), max(float(minimum), parsed))


def normalize_account_profiles(raw_profiles, serial="emulator-5564"):
    if not isinstance(raw_profiles, list) or not raw_profiles:
        return default_account_profiles(serial)

    normalized = []
    used_ids = set()
    for index, source in enumerate(raw_profiles):
        if not isinstance(source, dict):
            continue
        name = str(source.get("name") or f"Аккаунт {index + 1}").strip()
        account_id = str(source.get("id") or _account_id(name)).strip()
        if account_id in used_ids:
            account_id = f"{account_id}_{index + 1}"
        used_ids.add(account_id)
        task_enabled = source.get("task_enabled")
        task_settings = source.get("task_settings")
        normalized.append(
            {
                "id": account_id,
                "name": name,
                "enabled": bool(source.get("enabled", True)),
                "ldplayer_index": int(_number(source.get("ldplayer_index"), 5, 0, 99)),
                "adb_serial": str(source.get("adb_serial") or serial or "emulator-5564"),
                "session_minutes": _number(source.get("session_minutes"), 30.0, 1.0, 1440.0),
                "chooser_index": int(_number(source.get("chooser_index"), index + 1, 1, 20)),
                "switch_group": str(source.get("switch_group") or f"Аккаунт: {name}"),
                "switch_completion_uid": str(source.get("switch_completion_uid") or ""),
                "task_enabled": deepcopy(task_enabled) if isinstance(task_enabled, dict) else {},
                "task_settings": deepcopy(task_settings) if isinstance(task_settings, dict) else {},
                "routine_next_run": deepcopy(source.get("routine_next_run", {}))
                if isinstance(source.get("routine_next_run"), dict) else {},
            }
        )
    return normalized or default_account_profiles(serial)


def find_account(profiles, account_id):
    return next((profile for profile in profiles if profile.get("id") == account_id), None)


def snapshot_tasks(profile, tasks):
    profile["task_enabled"] = {
        task["id"]: bool(task.get("enabled", False))
        for task in tasks
    }
    profile["task_settings"] = {
        task["id"]: deepcopy(task.get("settings", {}))
        for task in tasks
    }
    return profile


def apply_tasks(profile, tasks):
    enabled = profile.get("task_enabled", {})
    settings = profile.get("task_settings", {})
    for task in tasks:
        task_id = task["id"]
        if task_id in enabled:
            task["enabled"] = bool(enabled[task_id])
        if isinstance(settings.get(task_id), dict):
            task.setdefault("settings", {}).update(deepcopy(settings[task_id]))
    return tasks


def next_enabled_account(profiles, current_id):
    enabled = [profile for profile in profiles if profile.get("enabled", True)]
    if len(enabled) <= 1:
        return None
    current_index = next(
        (index for index, profile in enumerate(enabled) if profile.get("id") == current_id),
        -1,
    )
    return enabled[(current_index + 1) % len(enabled)]


def requires_google_reauthentication(ui_xml):
    text = str(ui_xml or "").casefold()
    markers = (
        "подтвердите свою личность",
        "подтвердите, что это вы",
        "verify it's you",
        "verify it’s you",
        "confirm your identity",
    )
    return any(marker in text for marker in markers)


def extract_google_accounts(ui_xml):
    """Return Google accounts in the same top-to-bottom order as the chooser."""
    try:
        root = ET.fromstring(str(ui_xml or ""))
    except ET.ParseError:
        return []

    accounts = []
    seen = set()
    for node in root.iter():
        values = (node.attrib.get("text", ""), node.attrib.get("content-desc", ""))
        for value in values:
            for email in _EMAIL_RE.findall(str(value or "")):
                normalized = email.casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)
                accounts.append({"chooser_index": len(accounts) + 1, "email": email})
    return accounts


def extract_android_google_accounts(account_dump):
    """Return Google accounts reported by Android AccountManager."""
    accounts = []
    seen = set()
    pattern = re.compile(r"Account \{name=([^,}]+), type=([^}]+)\}")
    for name, account_type in pattern.findall(str(account_dump or "")):
        if account_type.strip() != "com.google":
            continue
        email = name.strip()
        normalized = email.casefold()
        if not email or normalized in seen:
            continue
        seen.add(normalized)
        accounts.append(email)
    return accounts


def mask_google_account(email):
    value = str(email or "").strip()
    if "@" not in value:
        return value
    local, domain = value.split("@", 1)
    visible = local[:1]
    return f"{visible}{'*' * max(3, len(local) - 1)}@{domain}"
