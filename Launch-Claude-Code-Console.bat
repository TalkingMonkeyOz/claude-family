@echo off
REM Launch Claude Code Console with terminal selection
REM Usage: Launch-Claude-Code-Console.bat [project_path] [terminal]
REM   project_path: Optional - defaults to current directory
REM   terminal: Optional - 1=WezTerm, 2=Windows Terminal, 3=Direct

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

REM Check for terminal preference argument
if "%~2"=="1" goto :WEZTERM
if "%~2"=="2" goto :WINTERMINAL
if "%~2"=="3" goto :DIRECT

REM Show menu if no argument
echo Select Terminal:
echo.
echo   [1] WezTerm (Recommended - better Claude integration)
echo   [2] Windows Terminal
echo   [3] Direct (current console)
echo.
set /p CHOICE="Enter choice (1-3): "

if "%CHOICE%"=="1" goto :WEZTERM
if "%CHOICE%"=="2" goto :WINTERMINAL
if "%CHOICE%"=="3" goto :DIRECT

echo Invalid choice, using WezTerm...
goto :WEZTERM

:WEZTERM
echo.
echo Launching in WezTerm...

REM Sync configuration from database before launching
python "C:\Projects\claude-family\scripts\generate_project_settings.py" "%PROJECT_PATH%" 2>nul

REM Launch WezTerm with Claude (use cmd /k to keep window open)
start "" "C:\Program Files\WezTerm\wezterm-gui.exe" start --cwd "%PROJECT_PATH%" -- cmd /k claude
goto :END

:WINTERMINAL
echo.
echo Launching in Windows Terminal...

REM Sync configuration from database before launching
python "C:\Projects\claude-family\scripts\generate_project_settings.py" "%PROJECT_PATH%" 2>nul

REM Launch Windows Terminal with Claude
start "" wt.exe -d "%PROJECT_PATH%" --title "Claude - %PROJECT_PATH%" cmd /k claude
goto :END

:DIRECT
echo.
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
goto :EOF

:END
echo.
echo Terminal launched. You can close this window.
timeout /t 3 >nul
