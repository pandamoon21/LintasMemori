@echo off
setlocal

set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%stop_all.py" %*

if errorlevel 1 (
  echo.
  echo [stop-all.cmd] Failed to stop stack cleanly.
  pause
  exit /b 1
)

echo.
echo [stop-all.cmd] Stack stopped.
exit /b 0
