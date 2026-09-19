@echo off
setlocal enabledelayedexpansion
set FOUND=0

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>&1
    set FOUND=1
)

if "!FOUND!"=="1" (
    echo Server on port 8000 stopped.
) else (
    echo No server running on port 8000.
)
pause
