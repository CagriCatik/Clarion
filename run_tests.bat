@echo off
echo ===================================================
echo   CLARION BACKEND TEST SUITE
echo ===================================================

cd backend
call ..\.venv\Scripts\activate.bat
python -m pytest
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] All tests passed!
) else (
    echo.
    echo [FAILURE] Tests failed with exit code %ERRORLEVEL%
)
