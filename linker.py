"""跨平台软链接核心逻辑：创建 / 删除 / 检测 + 历史持久化。

链接方向约定（与 UI 一致）：
    target（左，链接创建位置）  ──points to──▶  source（右，实际文件）

底层语义：
    os.symlink(src=source, dst=target)  -> target 成为指向 source 的符号链接
    mklink /J  target source            -> target 成为指向 source 的 junction
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".mmy_symlink_history.json"
PRESETS_FILE = Path.home() / ".mmy_symlink_presets.json"


# --------------------------------------------------------------------------- #
# 结果类型
# --------------------------------------------------------------------------- #
@dataclass
class LinkResult:
    ok: bool
    msg: str
    method: str = ""  # "junction" | "symlink" | ""


@dataclass
class LinkInfo:
    """路径检测信息。"""
    path: str
    exists: bool
    is_link: bool
    kind: str = ""      # "symlink" | "junction" | "real" | "none"
    target: str = ""    # 若是链接，指向何处


# --------------------------------------------------------------------------- #
# 创建链接
# --------------------------------------------------------------------------- #
def create_link(target: Path, source: Path, prefer: str = "auto") -> LinkResult:
    """在 target 处创建指向 source 的链接。

    prefer: "auto"（默认，文件夹优先 junction）| "symlink" | "junction"
    """
    if not source.exists():
        return LinkResult(False, f"源不存在：{source}")
    if target.exists() or target.is_symlink():
        return LinkResult(False, f"目标已存在：{target}\n请先删除或换一个目标名。")

    target.parent.mkdir(parents=True, exist_ok=True)
    is_dir = source.is_dir()

    if sys.platform == "win32":
        # 文件只能用 symlink
        if not is_dir or prefer == "symlink":
            return _win_symlink(target, source)
        # 文件夹：auto/junction 优先 junction
        if prefer in ("auto", "junction"):
            r = _win_junction(target, source)
            if r.ok:
                return r
            # junction 失败 -> 回退 symlink
            fb = _win_symlink(target, source)
            fb.msg = f"{fb.msg}（junction 失败已回退：{r.msg}）"
            return fb
        return _win_symlink(target, source)
    else:
        # Mac/Linux：symlink 直接可用，无需管理员
        return _unix_symlink(target, source)


def _win_junction(target: Path, source: Path) -> LinkResult:
    try:
        # mklink /J 不需要管理员权限，但要求绝对路径
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target.resolve()), str(source.resolve())],
            capture_output=True, text=True,
        )
        out = (result.stdout or "") + (result.stderr or "")
        # mklink 在中文 Windows 上常返回 GBK
        try:
            out = out.encode("latin-1").decode("gbk")
        except Exception:
            pass
        if result.returncode == 0:
            return LinkResult(True, f"Junction 创建成功：{target} → {source}", "junction")
        return LinkResult(False, f"mklink /J 失败：{out.strip()}")
    except Exception as e:
        return LinkResult(False, f"Junction 异常：{e}")


def _win_symlink(target: Path, source: Path) -> LinkResult:
    try:
        os.symlink(source, target, target_is_directory=source.is_dir())
        return LinkResult(True, f"Symlink 创建成功：{target} → {source}", "symlink")
    except OSError as e:
        # Windows 权限错误通常放在 winerror；errno 可能映射成其他值
        code = getattr(e, "winerror", None) or getattr(e, "errno", None)
        if code == 1314:
            return LinkResult(
                False,
                "权限不足（WinError 1314）：创建 symlink 需要 Windows 开发者模式，或右键以管理员身份运行本工具。",
            )
        return LinkResult(False, f"Symlink 失败：{e}")
    except Exception as e:
        return LinkResult(False, f"Symlink 异常：{e}")


def _unix_symlink(target: Path, source: Path) -> LinkResult:
    try:
        os.symlink(source, target, target_is_directory=source.is_dir())
        return LinkResult(True, f"Symlink 创建成功：{target} → {source}", "symlink")
    except OSError as e:
        return LinkResult(False, f"Symlink 失败：{e}")
    except Exception as e:
        return LinkResult(False, f"Symlink 异常：{e}")


# --------------------------------------------------------------------------- #
# 备份辅助：当目标已存在真实文件/文件夹时，先重命名备份再创建链接
# --------------------------------------------------------------------------- #
def _find_backup_name(path: Path) -> Path:
    """为 path 找一个不存在的备份名：path.bak -> path.bak_时间戳 -> path.bak_时间戳_序号。"""
    base = path.parent / (path.name + ".bak")
    if not base.exists():
        return base
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.parent / f"{path.name}.bak_{ts}"
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = path.parent / f"{path.name}.bak_{ts}_{i}"
        if not candidate.exists():
            return candidate
        i += 1


def create_link_with_backup(target: Path, source: Path, prefer: str = "auto") -> LinkResult:
    """先备份已存在的真实目标，再创建链接；若创建失败则尝试恢复备份。"""
    if not source.exists():
        return LinkResult(False, f"源不存在：{source}")

    info = inspect_link(target)
    if not info.exists or info.is_link:
        return create_link(target, source, prefer)

    backup = _find_backup_name(target)
    try:
        target.rename(backup)
    except Exception as e:
        return LinkResult(
            False,
            f"目标已存在且无法备份：{target}\n重命名失败：{e}\n"
            f"请手动删除或重命名该路径后再试。",
        )

    r = create_link(target, source, prefer)
    if r.ok:
        r.msg = f"{r.msg}\n原目标已备份至：{backup}"
    else:
        # 创建失败，尽量把备份恢复回去
        try:
            backup.rename(target)
        except Exception:
            pass
        r.msg = (
            f"{r.msg}\n由于创建失败，原目标已尝试恢复。"
            f"若未恢复，请检查备份：{backup}"
        )
    return r
# --------------------------------------------------------------------------- #
def delete_link(path: Path) -> LinkResult:
    if not path.exists() and not path.is_symlink():
        return LinkResult(False, "路径不存在")

    info = inspect_link(path)
    if not info.is_link:
        return LinkResult(
            False,
            f"目标不是软链接/junction（类型：{info.kind}），拒绝删除以保护源文件。\n"
            f"请手动确认后处理。",
        )

    try:
        if path.is_symlink():
            path.unlink()
        else:
            # junction：用 rmdir 删除（只删入口，不动源）
            os.rmdir(path)
        return LinkResult(True, f"已删除链接：{path}", info.kind)
    except Exception as e:
        return LinkResult(False, f"删除失败：{e}")


# --------------------------------------------------------------------------- #
# 检测
# --------------------------------------------------------------------------- #
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_junction(path: Path) -> bool:
    if sys.platform != "win32":
        return False
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == -1:  # INVALID_FILE_ATTRIBUTES
            return False
        return bool(attrs & _FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()
    except Exception:
        return False


def _read_junction_target(path: Path) -> str:
    """读 junction 的真实指向。优先 fsutil，失败回退空串。"""
    try:
        r = subprocess.run(
            ["fsutil", "reparsepoint", "query", str(path)],
            capture_output=True, text=True,
        )
        out = r.stdout or ""
        try:
            out = out.encode("latin-1").decode("gbk")
        except Exception:
            pass
        for line in out.splitlines():
            if "Substitute Name:" in line:
                # 形如 \??\D:\GitWork\MyAddon  或  \??\C:\...
                val = line.split(":", 1)[1].strip()
                if val.startswith("\\??\\"):
                    val = val[4:]
                return val
    except Exception:
        pass
    return ""


def inspect_link(path: Path) -> LinkInfo:
    p = str(path)
    if path.is_symlink():
        try:
            tgt = os.readlink(path)
        except OSError:
            tgt = ""
        return LinkInfo(p, True, True, "symlink", str(tgt))
    if is_junction(path):
        return LinkInfo(p, True, True, "junction", _read_junction_target(path))
    if path.exists():
        return LinkInfo(p, True, False, "real", "")
    return LinkInfo(p, False, False, "none", "")


# --------------------------------------------------------------------------- #
# 权限自检
# --------------------------------------------------------------------------- #
def can_create_symlink_without_admin() -> bool:
    """Windows 上检测当前进程能否不开开发者模式就建 symlink。"""
    if sys.platform != "win32":
        return True
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            src.write_text("x", encoding="utf-8")
            dst = Path(td) / "dst.txt"
            os.symlink(src, dst)
            return True
    except OSError as e:
        code = getattr(e, "winerror", None) or getattr(e, "errno", None)
        if code == 1314:
            return False
        return False
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# 历史记录
# --------------------------------------------------------------------------- #
@dataclass
class HistoryItem:
    source: str
    target: str
    kind: str            # "junction" | "symlink"
    link_type: str       # "folder" | "file"
    created_at: str
    ok: bool = True
    note: str = ""


def load_history(limit: int = 50) -> list[HistoryItem]:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        items = [HistoryItem(**d) for d in data if isinstance(d, dict)]
        return items[:limit]
    except Exception:
        return []


def save_history(items: list[HistoryItem]) -> None:
    try:
        HISTORY_FILE.write_text(
            json.dumps([asdict(i) for i in items[:50]], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def append_history(item: HistoryItem) -> list[HistoryItem]:
    items = load_history(50)
    items.insert(0, item)
    items = items[:50]
    save_history(items)
    return items


# --------------------------------------------------------------------------- #
# 预设路径（快速选目标 chip）
# --------------------------------------------------------------------------- #
DEFAULT_PRESETS: list[tuple[str, str]] = [
    # (显示名, 默认路径)
    ("Blender addons", r"C:\BlenderAPP\Blender5.1\portable\scripts\addons"),
    (".claude / CLAUDE.md", str(Path.home() / ".claude" / "CLAUDE.md")),
    (".codex / AGENTS.md", str(Path.home() / ".codex" / "AGENTS.md")),
    (".trae / rules", str(Path.home() / ".trae-cn" / "memory" / "project_memory.md")),
]


def load_presets() -> list[tuple[str, str]]:
    if not PRESETS_FILE.exists():
        return list(DEFAULT_PRESETS)
    try:
        data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return [(d.get("name", ""), d.get("path", "")) for d in data if isinstance(d, dict)]
    except Exception:
        pass
    return list(DEFAULT_PRESETS)


def save_presets(presets: list[tuple[str, str]]) -> None:
    try:
        PRESETS_FILE.write_text(
            json.dumps([{"name": n, "path": p} for n, p in presets], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
