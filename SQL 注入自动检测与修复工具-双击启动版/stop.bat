@echo off
set KILLED=0
for /f "tokens=5" %%p in ('netstat -aon ^| findstr "127.0.0.1:5000 "') do (
    if "%%p" neq "0" (
        taskkill /F /PID %%p >nul 2>&1
        if not errorlevel 1 set KILLED=1
    )
)
if "%KILLED%"=="1" (
    echo Service stopped.
) else (
    echo Service is not running on port 5000.
)
pause
