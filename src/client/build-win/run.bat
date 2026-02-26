@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo 🔨 Starting build process for Windows...
echo.

REM ============================================
REM Check Python and install if missing
REM ============================================

set PYTHON_VERSION=3.13.0
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_INSTALL_PATH=C:\Python313
set PYTHON_EXE=%PYTHON_INSTALL_PATH%\python.exe

:: Try to find Python
set "FOUND_PYTHON="
where python >nul 2>&1 && (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
    echo ✅ Found %PY_VER%
    set "FOUND_PYTHON=python"
)

:: Check specific path if not found in PATH
if not defined FOUND_PYTHON (
    if exist "%PYTHON_EXE%" (
        echo ✅ Found Python at %PYTHON_EXE%
        set "FOUND_PYTHON=%PYTHON_EXE%"
    )
)

:: Install Python if not found
if not defined FOUND_PYTHON (
    echo ⚠️  Python not found! Installing Python %PYTHON_VERSION%...
    echo.
    
    :: Download installer if not exists
    if not exist "%PYTHON_INSTALLER%" (
        echo 📥 Downloading Python %PYTHON_VERSION%...
        powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing}" 2>nul
        
        if not exist "%PYTHON_INSTALLER%" (
            echo ❌ Failed to download Python installer
            echo    Please download manually: https://www.python.org/downloads/ 
            exit /b 1
        )
        echo ✅ Downloaded %PYTHON_INSTALLER%
    )
    
    :: Install Python silently
    echo 🔧 Installing Python to %PYTHON_INSTALL_PATH%...
    "%PYTHON_INSTALLER%" /quiet ^
        InstallAllUsers=1 ^
        TargetDir="%PYTHON_INSTALL_PATH%" ^
        PrependPath=1 ^
        Include_test=0 ^
        Include_doc=0 ^
        Include_debug=0 ^
        Include_dev=0 ^
        Include_launcher=1 ^
        InstallLauncherAllUsers=1 ^
        Shortcuts=0
    
    if %errorLevel% neq 0 (
        echo ❌ Python installation failed
        exit /b 1
    )
    
    :: Verify installation
    timeout /t 2 /nobreak >nul
    if not exist "%PYTHON_EXE%" (
        echo ❌ Python installation verification failed
        exit /b 1
    )
    
    echo ✅ Python %PYTHON_VERSION% installed successfully
    set "FOUND_PYTHON=%PYTHON_EXE%"
    
    :: Add to PATH for future sessions (current session uses full path)
    setx /M PATH "%PYTHON_INSTALL_PATH%;%PYTHON_INSTALL_PATH%\Scripts;%PATH%" 2>nul
)

echo.
echo 🐍 Using Python: %FOUND_PYTHON%
echo.

REM ============================================
REM Setup virtual environment and dependencies
REM ============================================

set VENV_PATH=venv

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo 📦 Creating virtual environment...
    "%FOUND_PYTHON%" -m venv "%VENV_PATH%"
    if %errorLevel% neq 0 (
        echo ❌ Failed to create virtual environment
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment exists
)

echo.
echo 📥 Installing dependencies...
call "%VENV_PATH%\Scripts\activate.bat"
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo ❌ Failed to install dependencies
    exit /b 1
)
echo ✅ Dependencies installed

echo.
echo 🎭 Installing Playwright browsers...
playwright install chromium
if %errorLevel% neq 0 (
    echo ⚠️  Playwright browsers installation may have issues
) else (
    echo ✅ Playwright browsers installed
)

REM ============================================
REM Run obfuscated script
REM ============================================

echo.
echo 🚀 Starting application...
echo.

if exist "main.py" (
    python main.py
) else (
    echo ❌ main.py not found!
    echo    Please run 'make build-client' first to generate obfuscated script
    exit /b 1
)

echo.
echo 👋 Application finished
pause