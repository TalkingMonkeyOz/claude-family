@echo off
REM Claude Sandbox Runner
REM Usage: run-sandbox.bat "Your task here" [workspace_path]
REM
REM Example: run-sandbox.bat "Create a hello.py file" C:\Projects\test
REM
REM Authentication: Uses your existing Claude Max credentials (no API key needed)

setlocal

REM Get task from argument
set TASK=%~1
if "%TASK%"=="" (
    set /p TASK="Enter task: "
)

REM Get workspace (default to current directory)
set WORKSPACE=%~2
if "%WORKSPACE%"=="" set WORKSPACE=%CD%

REM Check for credentials file
set CREDS_FILE=%USERPROFILE%\.claude\.credentials.json
if not exist "%CREDS_FILE%" (
    echo ERROR: No credentials found at %CREDS_FILE%
    echo Run 'claude login' first to authenticate.
    pause
    exit /b 1
)

echo.
echo Running sandboxed Claude agent...
echo Workspace: %WORKSPACE%
echo Task: %TASK%
echo Auth: Using Claude Max credentials
echo.

docker run --rm ^
    -v "%CREDS_FILE%:/home/claude/.claude/.credentials.json:ro" ^
    -v "%WORKSPACE%:/workspace" ^
    claude-sandbox:latest ^
    "%TASK%"

echo.
echo Done.
pause
