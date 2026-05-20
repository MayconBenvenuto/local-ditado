@echo off
cd /d "%~dp0"
start "" pythonw "%~dp0dictado_hotkey.py" --config "%~dp0config.json"
