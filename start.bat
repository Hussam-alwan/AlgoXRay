@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8000 in your browser.
".venv\Scripts\python.exe" -m algoxray.cli serve --port 8000
if errorlevel 1 pause
