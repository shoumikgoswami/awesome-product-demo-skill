@echo off
setlocal EnableExtensions
title Product demo voice server
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONUNBUFFERED=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "ENVDIR=%LOCALAPPDATA%\product-demo-voice-env"
if defined VOICE_ENV_DIR set "ENVDIR=%VOICE_ENV_DIR%"
set "PYEXE=%ENVDIR%\Scripts\python.exe"
set "MARKER=%ENVDIR%\setup_done_v1.txt"

if exist "%MARKER%" goto run

echo ============================================================
echo  First-time setup (about 10-20 minutes, downloads ~5 GB).
echo  It only happens once. Please keep this window open.
echo ============================================================
echo.
nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo WARNING: nvidia-smi was not found. The NVIDIA driver may be missing.
  echo Continuing anyway - the GPU check below will tell us.
  echo.
)

set "BASEPY="
for /f "delims=" %%P in ('py -3.12 -c "import sys;print(sys.executable)" 2^>nul') do set "BASEPY=%%P"
if defined BASEPY goto havepy
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  set "BASEPY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  goto havepy
)
echo Python 3.12 not found - installing it with winget...
winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "BASEPY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined BASEPY goto nopython

:havepy
echo Using Python: %BASEPY%
if not exist "%PYEXE%" (
  echo Creating environment in %ENVDIR% ...
  "%BASEPY%" -m venv "%ENVDIR%"
  if errorlevel 1 goto fail
)
"%PYEXE%" -m pip install --upgrade pip
if errorlevel 1 goto fail

echo.
echo Installing speech packages...
"%PYEXE%" -m pip install -r "%~dp0requirements_windows.txt" --no-binary jieba,wget,antlr4-python3-runtime
if errorlevel 1 goto fail
"%PYEXE%" -m pip install nemo-toolkit==3.0.0 --no-deps
if errorlevel 1 goto fail

call :torchinstall
if errorlevel 1 goto nogpu

echo done> "%MARKER%"
echo.
echo Setup finished.

:run
"%PYEXE%" -c "import torch,torchvision,torchaudio;from torchvision.ops import nms;import sys;sys.exit(0 if torch.cuda.is_available() else 2)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo PyTorch needs repairing - reinstalling it, one time only...
  call :torchinstall
  if errorlevel 1 goto nogpu
)
echo.
echo Starting the voice server. The first start also downloads the voice model.
echo Leave this window open. Wait for the line that says it is watching for jobs.
echo.
"%PYEXE%" "%~dp0voice_server.py" --folder "%~dp0voice-data"
echo.
echo The server has stopped. Copy any error text above and send it to Claude.
pause
exit /b 0

:nopython
echo.
echo Could not find or install Python 3.12. Install it from python.org (tick "Add to PATH"), then run this file again.
pause
exit /b 1

:nogpu
echo.
echo PyTorch was installed but cannot see the GPU. Update the NVIDIA driver, then run this file again.
echo (To retry from scratch, delete the folder %ENVDIR%)
pause
exit /b 1

:fail
echo.
echo Setup stopped because a step failed. Copy the last lines above and send them to Claude.
pause
exit /b 1

:torchinstall
set "TORCH_OK="
for %%C in (cu128 cu126 cu124) do (
  if not defined TORCH_OK (
    echo.
    echo Installing PyTorch with CUDA build %%C ...
    "%PYEXE%" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/%%C --force-reinstall --no-deps
    "%PYEXE%" -c "import torch,torchvision,torchaudio;from torchvision.ops import nms;print('torch',torch.__version__,'torchvision',torchvision.__version__,'CUDA',torch.cuda.is_available());import sys;sys.exit(0 if torch.cuda.is_available() else 1)" && set "TORCH_OK=1"
  )
)
if defined TORCH_OK exit /b 0
exit /b 1
