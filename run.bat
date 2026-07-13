@echo off
setlocal
REM 清除被污染的 PYTHONHOME / PYTHONPATH（仅当前会话，不动全局）
set "PYTHONHOME="
set "PYTHONPATH="
cd /d "%~dp0"

set "PYEXE="
for %%P in (
  "C:\Users\EDY\.workbuddy\binaries\python\envs\default\python.exe"
  "C:\Users\EDY\.workbuddy\binaries\python\versions\3.13.12\python.exe"
  "C:\Users\EDY\AppData\Local\Programs\Python\Launcher\py.exe"
  "C:\Users\EDY\AppData\Local\Programs\Python\Python314\python.exe"
  python
) do (
  if not defined PYEXE (
    "%%~P" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYEXE=%%~P"
  )
)

if not defined PYEXE (
  echo [run] 找不到能正常启动的 Python 解释器
  pause
  exit /b 1
)

echo [run] 使用解释器: %PYEXE%
echo [run] 正在检查 PySide6 ...
"%PYEXE%" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo [run] 未检测到 PySide6，正在安装（需要联网，约几十 MB）...
  "%PYEXE%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [run] 安装失败，请手动执行: "%PYEXE%" -m pip install PySide6
    pause
    exit /b 1
  )
)

echo [run] 启动 MMY-SymLink GUI ...
"%PYEXE%" main.py
if errorlevel 1 (
  echo [run] 程序异常退出，错误码 %errorlevel%
  pause
)
endlocal