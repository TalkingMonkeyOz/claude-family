@echo off
REM Claude Family Startup Script
REM Run this at the start of each Claude Desktop session to sync PostgreSQL -> MCP memory

echo.
echo ================================================================================
echo CLAUDE FAMILY STARTUP - Syncing PostgreSQL to MCP Memory
echo ================================================================================
echo.

cd /d "%~dp0scripts"

python auto_sync_startup.py

echo.
echo ================================================================================
echo READY - Context loaded, now tell Claude to read the sync files
echo ================================================================================
echo.
echo Next: In Claude Desktop, say: "Read the MCP sync files and populate memory"
echo.
echo Files location: %~dp0postgres\data\
echo.

pause
