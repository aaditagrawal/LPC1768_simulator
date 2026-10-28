@echo off
cd /d "%~dp0"
python tools\stop.py
if errorlevel 1 pause
