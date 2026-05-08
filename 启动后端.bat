@echo off
cd /d "%~dp0backend"
echo Starting Django backend at http://127.0.0.1:8000/
echo Loading local config from "%cd%\.env"
echo Keep this window open while testing.
"D:\anaconda\anaconda\python.exe" manage.py runserver 0.0.0.0:8000 --noreload
echo.
echo Backend process exited. Press any key to close this window.
pause >nul
