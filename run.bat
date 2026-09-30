@echo off
title AI Business Intelligence Dashboard
echo.
echo ============================================================
echo   AI-Powered Business Intelligence Dashboard
echo   Final Year Academic Project
echo ============================================================
echo.

REM ---- Step 1: Check if Python is installed ----
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not found in PATH.
    echo.
    echo Please install Python 3.8 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, make sure to check the box:
    echo   [x] Add Python to PATH
    echo.
    echo After installing Python, close this window and run run.bat again.
    echo.
    pause
    exit /b 1
)

REM ---- Step 2: Display Python version ----
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [INFO] Found: %PYVER%
echo.

REM ---- Step 3: Create virtual environment if not exists ----
if not exist "venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Please make sure Python is properly installed.
        pause
        exit /b 1
    )
    echo [SETUP] Virtual environment created.
) else (
    echo [INFO] Virtual environment already exists.
)

REM ---- Step 4: Activate virtual environment ----
call venv\Scripts\activate.bat

REM ---- Step 5: Install/upgrade dependencies ----
echo [SETUP] Installing dependencies (this may take a minute on first run)...
pip install -r requirements.txt --quiet --disable-pip-version-check >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies may not have installed correctly.
    echo Trying again with verbose output...
    pip install -r requirements.txt
)
echo [SETUP] Dependencies installed.
echo.

REM ---- Step 6: Start the application ----
echo ============================================================
echo.
echo   Starting the server...
echo   First run will create the database and load sample data.
echo.
echo   When ready, open your browser to:
echo   >>> http://127.0.0.1:5000 <<<
echo.
echo   Login:   admin / admin123
echo.
echo   Press Ctrl+C to stop the server.
echo.
echo ============================================================
echo.

REM Try to open the browser automatically (with a short delay)
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000" >nul 2>&1

REM Start the Flask application
python app.py

REM If the server stops, pause so the user can see any error messages
echo.
echo [INFO] Server has stopped.
pause
