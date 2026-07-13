import sys, traceback, pathlib, subprocess, datetime

LOG = pathlib.Path(__file__).with_name("launch.log")


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%H:%M:%S}] {msg}\n")
    except Exception:
        pass


log("=== launch start ===")
log(f"executable={sys.executable}")
log(f"argv={sys.argv}")

CREATE_NO_WINDOW = 0x08000000


def msgbox(text, title="MMY-SymLink", flags=0):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(text), title, flags)
    except Exception:
        pass


def find_python_exe():
    exe = pathlib.Path(sys.executable)
    same = exe.parent / "python.exe"
    if same.exists():
        return str(same)
    for p in [
        r"C:\Users\EDY\.workbuddy\binaries\python\versions\3.13.12\python.exe",
        r"C:\Users\EDY\AppData\Local\Programs\Python\Python314\python.exe",
    ]:
        if pathlib.Path(p).exists():
            return p
    return "python"


def ensure_pyside():
    try:
        import PySide6
        log("PySide6 importable")
        return True
    except ImportError:
        log("PySide6 missing, installing")
        python = find_python_exe()
        req = pathlib.Path(__file__).with_name("requirements.txt")
        try:
            proc = subprocess.run(
                [python, "-m", "pip", "install", "-r", str(req)],
                creationflags=CREATE_NO_WINDOW,
                capture_output=True,
                text=True,
            )
        except Exception as e:
            log(f"pip launch error {e}")
            msgbox(f"无法启动 pip 安装：{e}")
            return False
        log(f"pip rc={proc.returncode}")
        if proc.returncode != 0:
            msgbox(
                f"PySide6 安装失败，请手动执行：\n{python} -m pip install -r {req}\n\n"
                f"{proc.stderr[-2000:]}"
            )
            return False
        try:
            import PySide6
            return True
        except ImportError:
            msgbox("安装后仍无法导入 PySide6")
            return False


def main():
    log("ensure_pyside")
    if not ensure_pyside():
        log("pyside failed")
        sys.exit(1)
    script_dir = pathlib.Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    log("import main")
    import main
    log("main.main()")
    main.main()
    log("main returned (GUI closed)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        log("EXCEPTION:\n" + tb)
        msgbox(
            "启动失败，详情见 launch.log：\n\n" + tb[-1500:],
            "MMY-SymLink 启动错误",
            0x10,
        )
        sys.exit(1)
    log("=== launch end ===")
