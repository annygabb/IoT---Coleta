@echo off
cd /d "%~dp0"
python run_distributed.py %*
pause
