@echo off
REM Double-click, then type the project id (e.g. P002). Runs/resumes the whole video pipeline.
chcp 65001 >nul
cd /d "%~dp0.."
set /p PROJECT=Nhap ma project (vi du P002):
ComfyUI\venv\Scripts\python.exe scripts\make_video.py %PROJECT% %*
pause
