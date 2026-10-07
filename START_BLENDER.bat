@echo off
cd /d "%~dp0"
set "BLENDER_USER_CONFIG=%~dp0tools\blender\user-config"
set "BLENDER_USER_SCRIPTS=%~dp0tools\blender\user-scripts"
set "DISABLE_TELEMETRY=true"
start "" "%~dp0tools\blender\blender-4.5.14-windows-x64\blender.exe" --python "%~dp0scripts\blender_bootstrap.py"
