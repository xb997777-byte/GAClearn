@echo off
echo Stopping processes listening on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
  taskkill /PID %%a /F >nul 2>nul
)
echo Done. Press any key to close this window.
pause >nul
