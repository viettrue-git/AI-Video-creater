@echo off
REM Double-click to watch overall progress (%) + ETA of the video being made (refreshes every 10 s).
REM Optional: pass a project id, e.g. show-video-render-progress.bat P002
chcp 65001 >nul
cd /d "%~dp0.."
ComfyUI\venv\Scripts\python.exe scripts\project_progress_monitor.py %1 --watch
pause
