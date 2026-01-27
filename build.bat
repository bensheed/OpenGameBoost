@echo off
echo ========================================
echo OpenGameBoost Build Script
echo ========================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

:: Run build script
echo.
echo Building executable...
python build.py

echo.
echo ========================================
if exist "dist\OpenGameBoost.exe" (
    echo BUILD SUCCESSFUL!
    echo.
    echo Your executable is at: dist\OpenGameBoost.exe
    echo.
    echo To create an installer:
    echo 1. Install Inno Setup from https://jrsoftware.org/isinfo.php
    echo 2. Open installer.iss with Inno Setup
    echo 3. Click Build -^> Compile
) else (
    echo BUILD FAILED!
    echo Check the error messages above.
)
echo ========================================
pause
