@echo off
setlocal
title Variable Global Platform Setup
set "_launcher=%~dp0setup-platform.ps1"

if not exist "%_launcher%" (
  echo Launcher script not found: %_launcher%
  pause
  exit /b 1
)

rem Prefer PowerShell 7 when installed; the lifecycle scripts are validated there.
set "_ps=powershell.exe"
where pwsh.exe >nul 2>nul
if not errorlevel 1 set "_ps=pwsh.exe"

"%_ps%" -NoProfile -ExecutionPolicy Bypass -File "%_launcher%"
if errorlevel 1 (
  echo.
  echo Setup did not complete successfully. See the messages above.
)

endlocal
