@echo off
REM Claude Family Silent Startup (for Windows Startup)
REM Runs at boot, shows balloon notification, no pause

cd /d "%~dp0scripts"

REM Run the sync
python auto_sync_startup.py > NUL 2>&1

REM Show balloon notification
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\show_startup_balloon.ps1"

REM Auto-close (no pause)
exit
