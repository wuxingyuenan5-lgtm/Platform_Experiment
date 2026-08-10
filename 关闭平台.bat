@echo off
setlocal
title Variable Global Platform Stop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-platform.ps1"
pause
