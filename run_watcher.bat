@echo off
REM Run Job Watcher
cd /d %~dp0
call venv\Scripts\activate
cd watcher
python watcher.py
pause
