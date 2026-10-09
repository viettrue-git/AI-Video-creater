@echo off
REM Start ComfyUI for a 16GB-RAM machine.
REM --disable-pinned-memory: pinned RAM (~6.5GB by default) caused "Memory allocation failure"
REM   + CUDA OOM on first sampling (tested 2026-10-05). Remove after the RAM upgrade and re-test.
REM Do NOT add --disable-dynamic-vram: it crashed with an access violation while loading SDXL.
REM Refuse to start a second server: leftover servers each hold GBs of RAM (found 5 processes on 2026-10-05).
netstat -ano | findstr /R /C:":8188 .*LISTENING" >nul
if %errorlevel%==0 (
  echo ComfyUI is already running on port 8188. Close it first or use http://127.0.0.1:8188
  exit /b 1
)
cd /d "%~dp0..\ComfyUI"
venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188 --disable-pinned-memory %*
