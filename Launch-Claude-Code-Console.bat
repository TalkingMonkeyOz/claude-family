@echo off
REM Launch Claude Code Console in a new terminal window
REM This opens Windows Terminal (or cmd) with Claude Code Console running

title Claude Code Console

echo.
echo ================================================================================
echo Claude Code Console - Terminal AI Assistant
echo ================================================================================
echo.
echo Starting Claude Code Console v2.0.13...
echo.

REM Launch claude in interactive mode (uses npm global installation)
claude

REM Keep window open if claude exits
pause
