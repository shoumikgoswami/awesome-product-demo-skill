@echo off
rem Thin Windows wrapper: finds any Python 3 and runs the cross-platform launcher.
title Product demo voice server
cd /d "%~dp0"
set "PYL="
py -3 -c "import sys" >nul 2>&1 && set "PYL=py -3"
if not defined PYL python -c "import sys" >nul 2>&1 && set "PYL=python"
if not defined PYL (
  echo Python not found - installing Python 3.12 with winget...
  winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYL="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYL (
  echo Could not find or install Python. Install Python 3.12 from python.org ^(tick "Add to PATH"^), then run this file again.
  pause
  exit /b 1
)
%PYL% "%~dp0start_voice_server.py"
if errorlevel 1 pause
