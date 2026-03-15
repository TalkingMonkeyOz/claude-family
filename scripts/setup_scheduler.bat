@echo off
REM Setup Windows Task Scheduler for Claude Family Job Runner
REM Run this as Administrator
REM Uses pythonw.exe (windowless) to prevent console flash during games/fullscreen apps

echo Creating Claude Family Job Runner scheduled task...

REM Find pythonw.exe path
where pythonw >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: pythonw.exe not found in PATH. Using python.exe (may flash console window)
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=pythonw
)

echo Using: %PYTHON_CMD%

REM Delete existing if any
schtasks /delete /tn "Claude Family Job Runner" /f 2>nul
schtasks /delete /tn "Claude Family Job Runner - Login" /f 2>nul

REM Create hourly task — runs hidden (no console window)
schtasks /create /tn "Claude Family Job Runner" /tr "%PYTHON_CMD% C:\Projects\claude-family\scripts\job_runner.py" /sc HOURLY /mo 1 /f /rl HIGHEST /np
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Hourly task created (windowless).
) else (
    echo FAILED: Could not create task. Try running as Administrator.
    pause
    exit /b 1
)

REM Create at-login trigger
schtasks /create /tn "Claude Family Job Runner - Login" /tr "%PYTHON_CMD% C:\Projects\claude-family\scripts\job_runner.py" /sc ONLOGON /f /rl HIGHEST /np
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Login task created (windowless).
) else (
    echo WARNING: Login task failed. Hourly task will still work.
)

echo.
echo Done. Job runner uses pythonw.exe - no console window flash.
echo View status: python C:\Projects\claude-family\scripts\job_runner.py --list
echo Dry run:     python C:\Projects\claude-family\scripts\job_runner.py --dry-run
echo.
echo NOTE: Re-run this script as Administrator to apply changes.
pause
