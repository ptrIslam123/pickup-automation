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

REM ============================================
REM Use found Python (full path to avoid PATH issues)
REM ============================================

set "PYTHON_CMD=%FOUND_PYTHON%"
echo 🐍 Using Python: %PYTHON_CMD%

REM Check Python version (need 3.9+)
for /f "tokens=2" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do (
    set "PY_FULL_VER=%%v"
    for /f "delims=." %%a in ("%%v") do set "PY_MAJOR=%%a"
)

if %PY_MAJOR% LSS 3 (
    echo ❌ Python 3.9 or higher required, found %PY_FULL_VER%
    exit /b 1
)

REM ============================================
REM Install required packages
REM ============================================

echo.
echo 📦 Checking required packages...

"%PYTHON_CMD%" -c "import nuitka" 2>nul || (
    echo ⚠️  Installing Nuitka...
    "%PYTHON_CMD%" -m pip install nuitka -q
)

"%PYTHON_CMD%" -c "import playwright" 2>nul || (
    echo ⚠️  Installing Playwright...
    "%PYTHON_CMD%" -m pip install playwright -q
)

REM ============================================
REM Setup Playwright browsers
REM ============================================

set BROWSERS_PATH=%USERPROFILE%\.cache\ms-playwright

if not exist "%BROWSERS_PATH%" (
    echo.
    echo ⚠️  Installing Playwright browsers...
    "%PYTHON_CMD%" -m playwright install chromium
    if %errorLevel% neq 0 (
        echo ❌ Failed to install Playwright browsers
        exit /b 1
    )
)

REM ============================================
REM Build with Nuitka
REM ============================================

if not exist .\dist mkdir .\dist

echo.
echo 📦 Compiling to single executable...
echo.

:: Use full path to python for Nuitka
"%PYTHON_CMD%" -m nuitka ^
    --onefile ^
    --follow-imports ^
    --include-package=requests ^
    --include-package=ntplib ^
    --include-package=bs4 ^
    --include-package=Levenshtein ^
    --include-package=fuzzywuzzy ^
    --plugin-enable=playwright ^
    --lto=yes ^
    --remove-output ^
    --output-dir=./dist ^
    --include-data-dir="%BROWSERS_PATH%=ms-playwright" ^
    --windows-icon-from-ico=icon.ico ^
    --windows-company-name="YourCompany" ^
    --windows-product-name="LeoBot" ^
    --windows-file-version="1.0.0" ^
    --windows-product-version="1.0.0" ^
    --windows-file-description="Telegram Bot for LeoMatch" ^
    main.py

if not exist ".\dist\main.exe" (
    echo ❌ Compilation failed: main.exe not created
    exit /b 1
)

echo.
echo ✅ Compilation completed successfully!

REM ============================================
REM Create launchers
REM ============================================

(
echo @echo off
echo set SCRIPT_DIR=%%~dp0
echo set PLAYWRIGHT_BROWSERS_PATH=%%SCRIPT_DIR%%ms-playwright
echo start "" "%%SCRIPT_DIR%%main.exe" %%*
) > .\dist\run.bat

(
echo # PowerShell launcher
echo $SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
echo $env:PLAYWRIGHT_BROWSERS_PATH = "$SCRIPT_DIR\ms-playwright"
echo Start-Process "$SCRIPT_DIR\main.exe" -Wait
) > .\dist\run.ps1

REM ============================================
REM Create archive
REM ============================================

echo.
echo 📁 Creating distribution archive...

powershell -Command "& {
    if (Test-Path '.\myapp_complete.zip') { Remove-Item '.\myapp_complete.zip' }
    Compress-Archive -Path '.\dist\*' -DestinationPath '.\myapp_complete.zip'
}"

for %%I in (".\dist\main.exe") do set /a FILESIZE_MB=%%~zI / 1048576

echo.
echo ✅ ========== BUILD SUCCESSFUL ==========
echo    📦 Executable:     .\dist\main.exe (%FILESIZE_MB% MB)
echo    🚀 Launcher:       .\dist\run.bat
echo    📚 Archive:        .\myapp_complete.zip
echo.
if defined PYTHON_INSTALLER (
echo ⚠️  NOTE: Python was installed to %PYTHON_INSTALL_PATH%
echo    You may need to restart your command prompt to use 'python' command
echo.
)
echo 🚀 To run: cd dist ^&^& run.bat
echo ==========================================

endlocal
pause