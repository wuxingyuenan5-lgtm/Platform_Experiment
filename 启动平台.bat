@echo off
setlocal
title Variable Global Platform Start
set "_launcher=%~dp0start-platform.ps1"
if not exist "%_launcher%" (
  echo Launcher script not found: %_launcher%
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%_launcher%"
pause
