@echo off
setlocal
title Variable Global Platform Start - LIVE WRITE
set "_launcher=%~dp0start-platform.ps1"
if not exist "%_launcher%" (
  echo Launcher script not found: %_launcher%
  pause
  exit /b 1
)
echo.
echo  ==========================================================
echo   LIVE WRITE MODE
echo   This start enables real order submission.
echo   Expected console line:  Live Write: enabled
echo  ==========================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%_launcher%" -EnableLiveWrite
pause
