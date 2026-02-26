
@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo 🔨 Starting build process for Windows...
echo.

REM ============================================
REM CONFIG
REM ============================================
set PYTHON_VERSION=3.12.6
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_INSTALL_PATH=C:\Python312
set PYTHON_EXE=%PYTHON_INSTALL_PATH%\python.exe
set VENV_PATH=venv

REM ============================================
REM 1. Find REAL Python (exclude Microsoft Store stub)
REM ============================================
set "FOUND_PYTHON="

:: Проверяем Python по явному пути установки
if exist "%PYTHON_EXE%" (
    echo ✅ Found Python at %PYTHON_EXE%
    set "FOUND_PYTHON=%PYTHON_EXE%"
)

:: Если не найден, ищем в PATH, но исключаем WindowsApps
if not defined FOUND_PYTHON (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        echo [DEBUG] Checking: %%i
        echo "%%i" | findstr /i /c:"WindowsApps" >nul
        if errorlevel 1 (
            :: Это НЕ WindowsApps, проверяем что это реальный Python
            "%%i" --version >nul 2>&1
            if !errorlevel! equ 0 (
                echo ✅ Found valid Python: %%i
                set "FOUND_PYTHON=%%i"
                goto :python_found
            )
        )
    )
)

:python_found

:: Если Python всё ещё не найден — качаем и ставим
if not defined FOUND_PYTHON (
    echo ⚠️  Python not found! Installing Python %PYTHON_VERSION%...
    
    if not exist "%PYTHON_INSTALLER%" (
        echo 📥 Downloading Python %PYTHON_VERSION%...
        powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing}"
        if not exist "%PYTHON_INSTALLER%" (
            echo ❌ Failed to download Python installer
            exit /b 1
        )
    )

    echo 🔧 Installing Python to %PYTHON_INSTALL_PATH%...
    "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 TargetDir="%PYTHON_INSTALL_PATH%" PrependPath=1 Include_test=0 Include_doc=0 Include_debug=0 Include_dev=0 Include_launcher=1 InstallLauncherAllUsers=1 Shortcuts=0
    if !errorlevel! neq 0 (
        echo ❌ Python installation failed
        exit /b 1
    )
    
    timeout /t 3 /nobreak >nul
    if not exist "%PYTHON_EXE%" (
        echo ❌ Python installation verification failed
        exit /b 1
    )
    set "FOUND_PYTHON=%PYTHON_EXE%"
    echo ✅ Python installed successfully
)

echo 🐍 Using Python: !FOUND_PYTHON!
echo.

REM ============================================
REM 2. Setup Virtual Environment (using FULL PATHS)
REM ============================================

:: Преобразуем путь к venv в абсолютный (для надёжности)
for %%I in ("%VENV_PATH%") do set "VENV_ABS=%%~fI"
set "VENV_PYTHON=%VENV_ABS%\Scripts\python.exe"
set "VENV_PIP=%VENV_ABS%\Scripts\pip.exe"

if not exist "%VENV_PYTHON%" (
    echo 📦 Creating virtual environment...
    "!FOUND_PYTHON!" -m venv "%VENV_ABS%"
    if !errorlevel! neq 0 (
        echo ❌ Failed to create virtual environment
        exit /b 1
    )
    
    :: Критическая проверка: создался ли python.exe внутри venv?
    if not exist "%VENV_PYTHON%" (
        echo ❌ Virtual environment creation failed: %VENV_PYTHON% not found
        echo    Possible causes: antivirus, permissions, or broken Python install
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment exists
)

echo.
echo 📥 Installing dependencies...

REM ============================================
REM 3. Install Dependencies (using venv python directly)
REM ============================================

:: Не полагаемся на activate.bat, используем прямой вызов python.exe из venv
"%VENV_PYTHON%" -m pip install --upgrade pip
if !errorlevel! neq 0 (
    echo ❌ Failed to upgrade pip
    exit /b 1
)

"%VENV_PYTHON%" -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo ❌ Failed to install dependencies
    exit /b 1
)
echo ✅ Dependencies installed

echo.
echo 🎭 Installing Playwright browsers...
"%VENV_PYTHON%" -m playwright install chromium
if !errorlevel! neq 0 (
    echo ⚠️  Playwright browsers installation may have issues
) else (
    echo ✅ Playwright browsers installed
)

REM ============================================
REM 4. Run Application
REM ============================================

echo.
echo 🚀 Starting application...
echo.

if exist "main.py" (
    "%VENV_PYTHON%" main.py
) else (
    echo ❌ main.py not found!
    echo    Please run 'make build-client' first to generate obfuscated script
    exit /b 1
)

echo.
echo 👋 Application finished
pause