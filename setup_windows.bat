@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher was not found. Install Python 3.11 or newer first.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto :failed
)

if not exist ".env" copy ".env.example" ".env" >nul

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Setup complete. Start the app with run_windows.bat.
exit /b 0

:failed
echo.
echo Setup failed. Review the error above and try again.
exit /b 1
