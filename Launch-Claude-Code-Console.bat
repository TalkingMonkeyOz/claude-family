@echo off
REM Launch Claude Code Console with terminal selection
REM Usage: Launch-Claude-Code-Console.bat [project_path] [terminal]
REM   project_path: Optional - defaults to current directory
REM   terminal: Optional - 1=Windows Terminal, 2=WezTerm, 3=Direct

title Claude Code Console Launcher

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

REM Derive project name from path for shared task list persistence
for %%I in ("%PROJECT_PATH%") do set "PROJECT_NAME=%%~nxI"
set CLAUDE_CODE_TASK_LIST_ID=%PROJECT_NAME%

REM Check for terminal preference argument
if "%~2"=="1" goto :WINTERMINAL
if "%~2"=="2" goto :WEZTERM
if "%~2"=="3" goto :DIRECT

REM Show menu if no argument
echo Select Terminal:
echo.
echo   [1] Windows Terminal (Recommended)
echo   [2] WezTerm
echo   [3] Direct (current console)
echo.
set /p CHOICE="Enter choice (1-3): "

if "%CHOICE%"=="1" goto :WINTERMINAL
if "%CHOICE%"=="2" goto :WEZTERM
if "%CHOICE%"=="3" goto :DIRECT

echo Invalid choice, using Windows Terminal...
goto :WINTERMINAL

:WINTERMINAL
echo.
echo Launching in Windows Terminal...

REM Sync all project config from database (settings, mcp, skills, commands, rules, agents, claude_md)
python "C:\Projects\claude-family\scripts\sync_project.py" "%PROJECT_PATH%" --no-interactive 2>nul

REM Launch Windows Terminal with Claude
REM suppressApplicationTitle in WT profile blocks VT escape sequences (Claude CLI title override)
REM cmd "title" command uses Win32 API (SetConsoleTitle) which is NOT blocked by suppressApplicationTitle
start "" wt.exe -d "%PROJECT_PATH%" --title "Claude - %PROJECT_NAME%" -p "Claude Code" cmd /k "title Claude - %PROJECT_NAME% && set CLAUDE_CODE_TASK_LIST_ID=%PROJECT_NAME% && claude --dangerously-load-development-channels server:channel-messaging"
goto :END

:WEZTERM
echo.
echo Launching in WezTerm...

REM Sync all project config from database (settings, mcp, skills, commands, rules, agents, claude_md)
python "C:\Projects\claude-family\scripts\sync_project.py" "%PROJECT_PATH%" --no-interactive 2>nul

REM Launch WezTerm with Claude (use cmd /k to keep window open)
start "" "C:\Program Files\WezTerm\wezterm-gui.exe" start --cwd "%PROJECT_PATH%" -- cmd /k "title Claude - %PROJECT_NAME% && claude --dangerously-load-development-channels server:channel-messaging"
goto :END

:DIRECT
echo.
echo Syncing configuration from database...
REM Sync all project config from database (settings, mcp, skills, commands, rules, agents, claude_md)
python "C:\Projects\claude-family\scripts\sync_project.py" "%PROJECT_PATH%" --no-interactive 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Config sync had issues, continuing anyway...
)
echo.

REM Change to project directory
cd /d "%PROJECT_PATH%"

echo Starting Claude Code Console...
echo.

REM Launch claude in interactive mode with channels support and debug logging
claude --dangerously-load-development-channels server:channel-messaging

REM Keep window open if claude exits
pause
goto :EOF

:END
echo.
echo Terminal launched. You can close this window.
timeout /t 3 >nul
