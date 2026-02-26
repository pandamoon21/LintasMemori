@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\stop-all.ps1" %*

if errorlevel 1 (
  echo.
  echo [stop-all.cmd] Failed to stop stack cleanly.
  pause
  exit /b 1
)

echo.
echo [stop-all.cmd] Stack stopped.
exit /b 0
