@echo off
setlocal
REM 一键打包 MMY-SymLink for Windows
set "PYTHONHOME="
set "PYTHONPATH="
cd /d "%~dp0"

set "VERSION=1.0.0"
if not "%~1"=="" set "VERSION=%~1"

echo [build] 开始打包 MMY-SymLink v%VERSION% ...

"C:\Users\EDY\.workbuddy\binaries\python\versions\3.13.12\python.exe" "scripts\build.py" --platform win --version %VERSION%

if errorlevel 1 (
    echo [build] 打包失败。
    pause
    exit /b 1
)

echo [build] 打包完成，产物在 dist\v%VERSION%\Windows\ 目录。
pause
endlocal