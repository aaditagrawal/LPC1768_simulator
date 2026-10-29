@echo off
setlocal
cd /d "%~dp0"
set "LPC_LAB_PORT=8879"
python tools\launch.py %*
if errorlevel 1 pause
