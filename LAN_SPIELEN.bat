@echo off
cd /d "%~dp0"
title BACKENBEBEN - LAN Spielsuche
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0server\lan_play.py"
) else if exist "%~dp0tools\blender-mcp\venv\Scripts\python.exe" (
  "%~dp0tools\blender-mcp\venv\Scripts\python.exe" "%~dp0server\lan_play.py"
) else (
  echo Zuerst SETUP_HOST.bat ausfuehren oder den LAN-Link des Hosts im Browser oeffnen.
  pause
  exit /b 1
)
if errorlevel 1 pause
