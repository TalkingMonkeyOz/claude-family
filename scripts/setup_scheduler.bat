@echo off
REM Setup Windows Task Scheduler for Claude Family Job Runner
REM Run this as Administrator

echo Creating Claude Family Job Runner scheduled task...

REM Delete existing if any
schtasks /delete /tn "Claude Family Job Runner" /f 2>nul

REM Create hourly task
schtasks /create /tn "Claude Family Job Runner" /tr "python C:\Projects\claude-family\scripts\job_runner.py" /sc HOURLY /mo 1 /f /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Hourly task created.
) else (
    echo FAILED: Could not create task. Try running as Administrator.
    pause
    exit /b 1
)

REM Also create at-login trigger (requires XML for dual triggers, so we add a second task)
schtasks /create /tn "Claude Family Job Runner - Login" /tr "python C:\Projects\claude-family\scripts\job_runner.py" /sc ONLOGON /f /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Login task created.
) else (
    echo WARNING: Login task failed. Hourly task will still work.
)

echo.
echo Done. Job runner will execute hourly and at login.
echo View status: python C:\Projects\claude-family\scripts\job_runner.py --list
echo Dry run:     python C:\Projects\claude-family\scripts\job_runner.py --dry-run
pause
