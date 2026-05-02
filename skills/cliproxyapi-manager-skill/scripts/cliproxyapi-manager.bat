@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "%SCRIPT_DIR%cliproxyapi_manager.py" %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%SCRIPT_DIR%cliproxyapi_manager.py" %*
  exit /b %ERRORLEVEL%
)
echo Python 3.8+ is required but was not found in PATH. 1>&2
exit /b 127
