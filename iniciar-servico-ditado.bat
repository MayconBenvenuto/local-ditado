@echo off
cd /d "%~dp0"
start "" "C:\Users\benve\AppData\Local\Programs\Python\Python312\pythonw.exe" "%~dp0dictado_hotkey.py" --device-name "External Mic" --engine whisper --whisper-model small --whisper-device cuda --whisper-compute-type int8_float16 --silence-seconds 2.5 --beam-size 5 --cpu-threads 8 --initial-prompt-file "%~dp0prompts\pt-br-default.txt"
