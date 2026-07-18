from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "BuZzbot"
BUNDLE_NAME = "BuZzbotPortable"
SPEC_PATH = PROJECT_ROOT / "BuZzbotPortable.generated.spec"
WORK_ROOT = PROJECT_ROOT / "build" / "_pyinstaller"
STAGE_ROOT = PROJECT_ROOT / "build" / "_portable_dist"
STAGE_DIR = STAGE_ROOT / BUNDLE_NAME
LEGACY_WORK_DIR = PROJECT_ROOT / "build" / "BuZzbotPortable.generated"
DIST_ROOT = PROJECT_ROOT / "dist"
DIST_DIR = DIST_ROOT / BUNDLE_NAME
ARCHIVE_PATH = DIST_ROOT / f"{BUNDLE_NAME}.zip"
CONFIG_PATH = PROJECT_ROOT / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.example.json"
IMG_DIR = PROJECT_ROOT / "img"
ASSET_DIR = PROJECT_ROOT / "buzzbot" / "assets"


def build_spec_text() -> str:
    return """# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
config_file = project_root / "config.json"
datas = []

if config_file.exists():
    datas.append((str(config_file), "."))

asset_dir = project_root / "buzzbot" / "assets"
if asset_dir.exists():
    datas.append((str(asset_dir), "buzzbot/assets"))


a = Analysis(
    ['buzzbot_app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BuZzbot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BuZzbotPortable',
)
"""


def ensure_clean_target():
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT, ignore_errors=True)
    if LEGACY_WORK_DIR.exists():
        shutil.rmtree(LEGACY_WORK_DIR, ignore_errors=True)
    if STAGE_ROOT.exists():
        shutil.rmtree(STAGE_ROOT, ignore_errors=True)
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()


def write_spec():
    SPEC_PATH.write_text(build_spec_text(), encoding="utf-8")


def run_pyinstaller():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            str(WORK_ROOT),
            "--distpath",
            str(STAGE_ROOT),
            str(SPEC_PATH.name),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def finalize_portable_layout(preserve_runtime=True):
    (STAGE_DIR / "backups" / "config").mkdir(parents=True, exist_ok=True)
    stage_runtime_config()
    stage_templates()
    if preserve_runtime:
        preserve_runtime_data()
    validate_portable_layout()
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.move(str(STAGE_DIR), str(DIST_DIR))
    shutil.rmtree(STAGE_ROOT, ignore_errors=True)
    shutil.make_archive(
        str(ARCHIVE_PATH.with_suffix("")),
        "zip",
        root_dir=DIST_ROOT,
        base_dir=BUNDLE_NAME,
    )


def stage_runtime_config():
    source = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    if source.exists():
        shutil.copy2(source, STAGE_DIR / "config.json")


def stage_templates():
    if not IMG_DIR.exists():
        raise FileNotFoundError(f"Template directory is missing: {IMG_DIR}")
    shutil.copytree(IMG_DIR, STAGE_DIR / "img", dirs_exist_ok=True)


def validate_portable_layout():
    image_dir = STAGE_DIR / "img"
    png_count = sum(1 for _path in image_dir.rglob("*.png"))
    if png_count == 0:
        raise RuntimeError(f"Portable build contains no PNG templates: {image_dir}")

    config_path = STAGE_DIR / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Portable config is missing: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    missing = []
    for image in config.get("images", []):
        configured_path = Path(str(image.get("path") or ""))
        resolved_path = configured_path if configured_path.is_absolute() else STAGE_DIR / configured_path
        if not resolved_path.is_file():
            missing.append(str(image.get("description") or configured_path))

    if missing:
        preview = ", ".join(missing[:10])
        suffix = f" and {len(missing) - 10} more" if len(missing) > 10 else ""
        raise RuntimeError(
            f"Portable build is missing {len(missing)} configured templates: {preview}{suffix}"
        )

    print(f"Portable templates verified: {png_count} PNG files")


def preserve_runtime_data():
    if not DIST_DIR.exists():
        return

    old_config = DIST_DIR / "config.json"
    if old_config.exists():
        shutil.copy2(old_config, STAGE_DIR / "config.json")

    for directory_name in ("img", "backups", "reports"):
        source = DIST_DIR / directory_name
        if source.exists():
            shutil.copytree(source, STAGE_DIR / directory_name, dirs_exist_ok=True)

    for log_path in DIST_DIR.glob("bot.log*"):
        if log_path.is_file():
            shutil.copy2(log_path, STAGE_DIR / log_path.name)


def remove_temporary_build_files():
    shutil.rmtree(WORK_ROOT, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean-runtime",
        action="store_true",
        help="Do not copy config, templates, logs or reports from an older dist build.",
    )
    args = parser.parse_args()
    ensure_clean_target()
    write_spec()
    run_pyinstaller()
    finalize_portable_layout(preserve_runtime=not args.clean_runtime)
    remove_temporary_build_files()
    print(f"Portable folder ready: {DIST_DIR}")
    print(f"Portable archive ready: {ARCHIVE_PATH}")


if __name__ == "__main__":
    main()
