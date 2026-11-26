@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 exit /b 1
)
if exist "requirements.lock.txt" (
  ".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -e "./backend[dev]"
if errorlevel 1 exit /b 1
echo Setup complete. Run start.bat.
