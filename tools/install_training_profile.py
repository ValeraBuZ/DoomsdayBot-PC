from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from buzzbot.routines import LEGACY_RADAR_TEMPLATE_UIDS


def install_profile(profile_path, install_root):
    install_root = Path(install_root)
    config_path = install_root / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    with zipfile.ZipFile(profile_path, "r") as archive:
        manifest = json.loads(archive.read("profile.json").decode("utf-8"))
        routine_groups = set(manifest["groups"])
        managed_root = (install_root / "img").resolve()
        for image in config.get("images", []):
            if str(image.get("uid") or "") not in LEGACY_RADAR_TEMPLATE_UIDS:
                continue
            try:
                source = Path(image.get("path", ""))
                source = source if source.is_absolute() else install_root / source
                source = source.resolve()
                if source.is_relative_to(managed_root) and source.exists():
                    source.unlink()
            except OSError:
                pass
        config["images"] = [
            image for image in config.get("images", [])
            if (
                image.get("group") not in routine_groups
                and str(image.get("uid") or "") not in LEGACY_RADAR_TEMPLATE_UIDS
            )
        ]
        for image in manifest["images"]:
            task_id = next(
                (
                    task["id"] for task in manifest["routine_tasks"]
                    if task["group"] == image["group"]
                ),
                "system",
            )
            target_dir = install_root / "img" / task_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{image['uid']}.png"
            target_path.write_bytes(archive.read(image["path"]))
            installed = deepcopy(image)
            installed["path"] = str(target_path.relative_to(install_root))
            config["images"].append(installed)

    config["routine_tasks"] = manifest["routine_tasks"]
    config["routine_max_marches"] = manifest["routine_max_marches"]
    config["routine_march_deadlines"] = []
    config["routine_next_run"] = {}
    config.setdefault("groups", {}).update(manifest["groups"])
    config["groups"].pop("Радарная станция", None)
    config.setdefault("group_schedules", {}).pop("Радарная станция", None)
    config.setdefault("group_execution", {}).pop("Радарная станция", None)
    config["scale_enabled"] = False
    config["input_backend"] = "adb"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--install-root", type=Path, required=True)
    args = parser.parse_args()
    install_profile(args.profile, args.install_root)
    print(f"Installed profile: {args.profile}")


if __name__ == "__main__":
    main()
