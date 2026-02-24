@echo off
echo 🔨 Starting build process for Windows...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.9 or higher.
    exit /b 1
)

REM Path to Playwright browsers
set BROWSERS_PATH=%USERPROFILE%\.cache\ms-playwright

REM Check if browsers exist
if not exist "%BROWSERS_PATH%" (
    echo ⚠️ Playwright browsers not found. Installing...
    python -m playwright install chromium
    if %errorlevel% neq 0 (
        echo ❌ Failed to install Playwright browsers
        exit /b 1
    )
)

REM Create build directory
if not exist .\dist mkdir .\dist

echo.
echo 📦 Compiling to single executable...
echo.

REM Compilation with Nuitka
python -m nuitka ^
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

REM Verify compilation result
if not exist ".\dist\main.exe" (
    echo ❌ Compilation failed: main.exe not created
    exit /b 1
)

echo.
echo ✅ Compilation completed successfully!

REM Create launcher script (batch file)
(
echo @echo off
echo set SCRIPT_DIR=%%~dp0
echo.
echo REM Set browser path for Playwright
echo set PLAYWRIGHT_BROWSERS_PATH=%%SCRIPT_DIR%%ms-playwright
echo.
echo REM Launch the application
echo start "" "%%SCRIPT_DIR%%main.exe" %%*
) > .\dist\run.bat

REM Create PowerShell launcher (alternative)
(
echo # PowerShell launcher
echo $SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
echo.
echo # Set browser path for Playwright
echo $env:PLAYWRIGHT_BROWSERS_PATH = "$SCRIPT_DIR\ms-playwright"
echo.
echo # Launch the application
echo Start-Process "$SCRIPT_DIR\main.exe" -Wait
) > .\dist\run.ps1

echo.
echo 📁 Creating distribution archive...

REM Create ZIP archive using PowerShell
powershell -Command "& {
    $src = '.\dist'
    $dst = '.\myapp_complete.zip'
    if (Test-Path $dst) { Remove-Item $dst }
    Compress-Archive -Path $src\* -DestinationPath $dst
}"

REM Get file size
for %%I in (".\dist\main.exe") do set FILESIZE=%%~zI
set /a FILESIZE_MB=%FILESIZE% / 1048576

echo.
echo ✅ ========== BUILD SUCCESSFUL ==========
echo    📦 Executable:     .\dist\main.exe (%FILESIZE_MB% MB)
echo    🚀 Launcher:       .\dist\run.bat or run.ps1
echo    📚 Archive:        .\myapp_complete.zip
echo.
echo 🚀 To run the application:
echo    cd dist && run.bat
echo.
echo 📦 To distribute:
echo    Send myapp_complete.zip to users
echo    They just need to extract and run run.bat
echo ==========================================
echo.