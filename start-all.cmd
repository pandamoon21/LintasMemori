@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\start-all.ps1" %*

if errorlevel 1 (
  echo.
  echo [start-all.cmd] Failed to start stack.
  pause
  exit /b 1
)

echo.
echo [start-all.cmd] Command completed.
exit /b 0
