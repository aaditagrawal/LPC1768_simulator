@echo off
setlocal
cd /d "%~dp0"
set "LPC_LAB_URL=http://127.0.0.1:8879"
call npm.cmd run test:browser -- %*
exit /b %errorlevel%
