@echo off
setlocal
title Clarion App

echo ===================================================
echo   CLARION DOCUMENTATION ENGINE
echo ===================================================
echo.

:: Ensure we are in project root
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: -----------------------------------------------------
:: 1. VIRTUAL ENVIRONMENT SETUP
:: -----------------------------------------------------
if not exist ".venv" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create venv. Is Python installed?
        pause
        exit /b %ERRORLEVEL%
    )
)

echo [SETUP] Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate venv.
    pause
    exit /b %ERRORLEVEL%
)

:: -----------------------------------------------------
:: 2. INSTALL DEPENDENCIES (first run only)
:: -----------------------------------------------------
echo [SETUP] Checking backend dependencies...
pip install -e . -q
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b %ERRORLEVEL%
)

cd frontend
if not exist "node_modules" (
    echo [SETUP] Installing frontend dependencies...
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b %ERRORLEVEL%
    )
)
cd ..

:: -----------------------------------------------------
:: 3. START BACKEND FIRST
:: -----------------------------------------------------
echo.
echo [START] Starting Backend Server (port 8000)...
start "Clarion Backend" cmd /c "cd /d %PROJECT_ROOT% && call .venv\Scripts\activate.bat && uvicorn clarion.server:app --host 127.0.0.1 --port 8000"

:: Wait for backend to be ready
echo [WAIT] Waiting for backend to initialize...
timeout /t 3 /nobreak > nul

:: Check if backend is running
curl -s http://127.0.0.1:8000/v1/health > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Backend may still be starting...
    timeout /t 2 /nobreak > nul
)

:: -----------------------------------------------------
:: 4. START FRONTEND
:: -----------------------------------------------------
echo [START] Starting Frontend (port 5173)...
cd frontend
start "Clarion Frontend" cmd /c "npm run dev"

:: Wait a moment for frontend to start
timeout /t 2 /nobreak > nul

:: -----------------------------------------------------
:: 5. OPEN BROWSER
:: -----------------------------------------------------
echo.
echo ===================================================
echo   Clarion is running!
echo   
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ===================================================
echo.
echo Opening browser...
start http://localhost:5173

echo.
echo Press any key to STOP all services...
pause > nul

:: -----------------------------------------------------
:: 6. CLEANUP - Kill servers
:: -----------------------------------------------------
echo.
echo [STOP] Shutting down...
taskkill /FI "WINDOWTITLE eq Clarion Backend*" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq Clarion Frontend*" /F > nul 2>&1

echo [DONE] Application stopped.
endlocal
