@echo off
title The Second Read
setlocal

REM --- locate the project root (this file lives in <root>\scripts) ---
cd /d "%~dp0.."
set "ROOT=%CD%"
set "PORT=8000"

echo ============================================================
echo   The Second Read - starting...
echo   Project: %ROOT%
echo ============================================================
echo.

REM --- kill anything already listening on the port (restart) ---
echo Freeing port %PORT% (if in use)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr LISTENING') do (
  echo   stopping PID %%a
  taskkill /F /PID %%a >nul 2>&1
)

REM --- make sure the venv exists ---
if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo.
  echo ERROR: virtual environment not found at "%ROOT%\.venv".
  echo Run once:  python -m venv .venv  ^&^&  .venv\Scripts\python -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

REM --- open the browser a few seconds after the server starts ---
start "" /min cmd /c "timeout /t 4 >nul & explorer http://localhost:%PORT%"

REM --- run the server in this window (logs stay visible) ---
echo.
echo Opening http://localhost:%PORT% in your browser...
echo Leave this window open while presenting.  Press Ctrl+C to stop.
echo.
cd /d "%ROOT%\backend"
"%ROOT%\.venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port %PORT%

echo.
echo Server stopped.
pause
