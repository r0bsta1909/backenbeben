@echo off
cd /d "%~dp0"
title BACKENBEBEN - Host und Balancing
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0server\host.py" %*
) else if exist "%~dp0tools\blender-mcp\venv\Scripts\python.exe" (
  "%~dp0tools\blender-mcp\venv\Scripts\python.exe" "%~dp0server\host.py" %*
) else (
  echo Zuerst SETUP_HOST.bat ausfuehren.
  pause
  exit /b 1
)
if errorlevel 1 pause
