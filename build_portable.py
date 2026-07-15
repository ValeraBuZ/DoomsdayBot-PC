from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "DoomsdayBotPortable"
SPEC_PATH = PROJECT_ROOT / "DoomsdayBotPortable.generated.spec"
WORK_ROOT = PROJECT_ROOT / "build" / "_pyinstaller"
STAGE_ROOT = PROJECT_ROOT / "build" / "_portable_dist"
STAGE_DIR = STAGE_ROOT / APP_NAME
LEGACY_WORK_DIR = PROJECT_ROOT / "build" / "DoomsdayBotPortable.generated"
DIST_ROOT = PROJECT_ROOT / "dist"
DIST_DIR = DIST_ROOT / APP_NAME
ARCHIVE_PATH = DIST_ROOT / f"{APP_NAME}.zip"
MANUAL_PATH = PROJECT_ROOT / "DoomsdayBot_Инструкция.pdf"


def build_spec_text() -> str:
    return """# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
img_dir = project_root / "img"
config_file = project_root / "config.json"
datas = []

if img_dir.exists():
    datas.append((str(img_dir), "img"))
if config_file.exists():
    datas.append((str(config_file), "."))


a = Analysis(
    ['doomsday_bot_final.py'],
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
    name='DoomsdayBotPortable',
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
    name='DoomsdayBotPortable',
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


def finalize_portable_layout():
    (STAGE_DIR / "img").mkdir(parents=True, exist_ok=True)
    (STAGE_DIR / "backups" / "config").mkdir(parents=True, exist_ok=True)
    preserve_runtime_data()
    if MANUAL_PATH.exists():
        shutil.copy2(MANUAL_PATH, STAGE_DIR / MANUAL_PATH.name)
    (STAGE_DIR / "START_HERE.txt").write_text(
        "Запустите DoomsdayBotPortable.exe из этой папки.\n"
        "Не отделяйте папку _internal от EXE-файла.\n"
        "Обучение переносится через Настроить задачи -> Экспорт обучения.\n"
        "Не запускайте файлы из папки build.\n",
        encoding="utf-8",
    )
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.move(str(STAGE_DIR), str(DIST_DIR))
    shutil.rmtree(STAGE_ROOT, ignore_errors=True)
    shutil.make_archive(
        str(ARCHIVE_PATH.with_suffix("")),
        "zip",
        root_dir=DIST_ROOT,
        base_dir=APP_NAME,
    )


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
    ensure_clean_target()
    write_spec()
    run_pyinstaller()
    finalize_portable_layout()
    remove_temporary_build_files()
    print(f"Portable folder ready: {DIST_DIR}")
    print(f"Portable archive ready: {ARCHIVE_PATH}")


if __name__ == "__main__":
    main()
