@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run setup_windows.bat first.
    exit /b 1
)

chcp 65001 >nul
set PYTHONUTF8=1
".venv\Scripts\python.exe" -X utf8 main.py
