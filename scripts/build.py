#!/usr/bin/env python3
"""跨平台一键打包脚本（Windows / macOS）。

用法：
    python scripts/build.py              # 自动识别当前平台打包
    python scripts/build.py --version 1.0.1

输出目录按版本号隔离，避免反复覆盖同名 exe 触发 Windows 图标缓存陷阱。
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

APP_NAME = "MMY-SymLink"
ENTRY = PROJECT_ROOT / "run_silent.pyw"


def run(cmd: list[str], **kwargs) -> None:
    print(f"[build] {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def ensure_assets() -> None:
    ico = ASSETS_DIR / "MMY-SymLink.ico"
    icns = ASSETS_DIR / "MMY-SymLink.icns"
    if sys.platform == "win32" and not ico.exists():
        print("[build] 生成 Windows ICO...")
        run([sys.executable, str(PROJECT_ROOT / "scripts" / "build_assets.py")])
    if sys.platform == "darwin" and not icns.exists():
        print("[build] 生成 macOS ICNS...")
        run([sys.executable, str(PROJECT_ROOT / "scripts" / "build_assets.py")])


def clean_old_outputs(version_dir: Path) -> None:
    """清理该版本目录下的旧产物，避免混合。"""
    if version_dir.exists():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)


def build_windows(version: str) -> Path:
    print("[build] 开始打包 Windows 单文件 exe...")
    ensure_assets()
    version_dir = DIST_DIR / f"v{version}" / "Windows"
    clean_old_outputs(version_dir)

    ico = ASSETS_DIR / "MMY-SymLink.ico"
    # --add-data 把 ico 一并打入 exe，运行时由 sys._MEIPASS 读取，
    # 用于 QApplication.setWindowIcon（窗口左上角 + 任务栏图标）
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--name={APP_NAME}",
        f"--icon={ico}",
        f"--add-data={ico};.",
        f"--distpath={version_dir}",
        f"--workpath={BUILD_DIR}",
        "--specpath", str(PROJECT_ROOT),
        str(ENTRY),
    ]
    run(cmd, cwd=PROJECT_ROOT)

    exe = version_dir / f"{APP_NAME}.exe"
    if not exe.exists():
        raise FileNotFoundError(f"打包未生成预期 exe：{exe}")
    print(f"[build] Windows exe 已生成：{exe}")
    return exe


def build_macos(version: str) -> Path:
    print("[build] 开始打包 macOS .app...")
    ensure_assets()
    version_dir = DIST_DIR / f"v{version}" / "macOS"
    clean_old_outputs(version_dir)

    icns = ASSETS_DIR / "MMY-SymLink.icns"
    ico = ASSETS_DIR / "MMY-SymLink.ico"
    add_data_icns = f"--add-data={icns}:."
    add_data_ico = f"--add-data={ico}:." if ico.exists() else None
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--windowed",
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--name={APP_NAME}",
        f"--icon={icns}",
        add_data_icns,
        f"--distpath={version_dir}",
        f"--workpath={BUILD_DIR}",
        "--specpath", str(PROJECT_ROOT),
        "--osx-bundle-identifier", "com.mmy.mmy-symlink",
        str(ENTRY),
    ]
    if add_data_ico:
        cmd.insert(-1, add_data_ico)
    run(cmd, cwd=PROJECT_ROOT)

    app = version_dir / f"{APP_NAME}.app"
    if not app.exists():
        raise FileNotFoundError(f"打包未生成预期 app：{app}")
    print(f"[build] macOS app 已生成：{app}")
    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="MMY-SymLink 跨平台打包")
    parser.add_argument("--version", default="1.0.0", help="版本号（默认 1.0.0）")
    parser.add_argument("--platform", choices=["auto", "win", "mac", "windows"], default="auto",
                        help="目标平台（默认 auto=当前平台）")
    args = parser.parse_args()

    sys_name = platform.system()
    target = args.platform
    if target == "auto":
        target = "win" if sys_name == "Windows" else "mac" if sys_name == "Darwin" else "win"

    if target in ("win", "windows"):
        build_windows(args.version)
    elif target == "mac":
        build_macos(args.version)
    else:
        print(f"[build] 不支持的平台：{target}")
        return 1

    print("[build] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
