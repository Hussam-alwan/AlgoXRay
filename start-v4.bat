@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
if not exist "results\v4-runtime.json" (
  echo Start Docker Desktop, then run .venv\Scripts\python.exe tools/prepare_v4_worker.py
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8002/v4 in your browser.
".venv\Scripts\python.exe" -m uvicorn algoxray.api:app --host 127.0.0.1 --port 8002
if errorlevel 1 pause
