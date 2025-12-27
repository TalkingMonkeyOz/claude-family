@echo off
REM Launch Claude Code Console with centralized config deployment
REM Usage: Launch-Claude-Code-Console.bat [project_path]
REM   If no path provided, uses current directory

title Claude Code Console

echo.
echo ================================================================================
echo Claude Code Console - Terminal AI Assistant
echo ================================================================================
echo.

REM Determine project path
if "%~1"=="" (
    set "PROJECT_PATH=%CD%"
) else (
    set "PROJECT_PATH=%~1"
)

echo Project: %PROJECT_PATH%
echo.

REM Sync configuration from database before launching (self-healing)
echo Syncing configuration from database...
python "C:\Projects\claude-family\scripts\generate_project_settings.py" "%PROJECT_PATH%" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Config sync had issues, continuing anyway...
)
echo.

REM Change to project directory
cd /d "%PROJECT_PATH%"

echo Starting Claude Code Console...
echo.

REM Launch claude in interactive mode
claude

REM Keep window open if claude exits
pause
