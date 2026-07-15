@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title farm bot
echo.
echo  farm bot
echo.

set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python3.12\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python3.12\python.exe"
if not defined PY if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
if not defined PY if exist "C:\Program Files\Python312\python.exe" set "PY=C:\Program Files\Python312\python.exe"
if not defined PY (
    python --version 2>nul | findstr /C:"3.12" >nul 2>&1
    if not errorlevel 1 for /f "usebackq tokens=*" %%i in (`python -c "import sys; print(sys.executable)"`) do set "PY=%%i"
)
if not defined PY (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 for /f "usebackq tokens=*" %%i in (`py -3.12 -c "import sys; print(sys.executable)"`) do set "PY=%%i"
)
if not defined PY goto :dl
goto :run

:dl
echo  Python 3.12 absent, dl...
echo.
if "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
    set "PU=https://www.python.org/ftp/python/3.12.10/python-3.12.10-arm64.exe"
) else if "%PROCESSOR_ARCHITECTURE%"=="x86" (
    set "PU=https://www.python.org/ftp/python/3.12.10/python-3.12.10.exe"
) else (
    set "PU=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
)
set "PT=%TEMP%\py.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "(New-Object Net.WebClient).DownloadFile('!PU!', '!PT!')"
if not exist "!PT!" (
    echo  dl Python fail, verifiez la connexion
    pause
    exit /b 1
)
echo  install Python...
"!PT!" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del /f /q "!PT!" 2>nul
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "!PY!" (
    echo  install Python fail, va sur python.org
    pause
    exit /b 1
)
echo  Python ok
echo.

:run
cd /d "%~dp0"
"!PY!" installer.py
if errorlevel 1 (
    echo  install fail
    pause
    exit /b 1
)
endlocal
