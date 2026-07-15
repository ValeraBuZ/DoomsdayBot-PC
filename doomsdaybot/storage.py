from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def ensure_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _trim_old_files(directory, pattern, keep_last):
    files = sorted(Path(directory).glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    for old_file in files[keep_last:]:
        if old_file.is_file():
            old_file.unlink(missing_ok=True)


def save_json_with_backup(path, data, backup_dir=None, keep_backups=10):
    path = Path(path)
    ensure_directory(path.parent)

    if backup_dir is None:
        backup_dir = path.parent / "backups" / path.stem
    backup_dir = ensure_directory(backup_dir)

    if path.exists():
        backup_path = backup_dir / f"{path.stem}_{_timestamp()}{path.suffix}"
        shutil.copy2(path, backup_path)
        _trim_old_files(backup_dir, f"{path.stem}_*{path.suffix}", keep_backups)

    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)
    try:
        temp_path.replace(path)
    except PermissionError:
        with path.open("w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=2)
        temp_path.unlink(missing_ok=True)
    except OSError:
        with path.open("w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=2)
        temp_path.unlink(missing_ok=True)
    return path


def move_file_to_trash(source_path, trash_root):
    source_path = Path(source_path)
    if not source_path.exists():
        return None

    trash_root = ensure_directory(trash_root)
    source_parent = source_path.parent.name
    destination_name = f"{source_parent}__{source_path.stem}__{_timestamp()}{source_path.suffix}"
    destination = trash_root / destination_name
    shutil.move(str(source_path), str(destination))
    _trim_old_files(trash_root, "*", 500)
    return destination
