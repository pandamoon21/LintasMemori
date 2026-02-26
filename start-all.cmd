@echo off
setlocal

set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%start_all.py" %*

if errorlevel 1 (
  echo.
  echo [start-all.cmd] Failed to start stack.
  pause
  exit /b 1
)

echo.
echo [start-all.cmd] Command completed.
exit /b 0
