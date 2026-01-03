@echo off
echo Starting Services...

echo Starting Backend...
start "Clarion Backend" cmd /k "poetry install && poetry run uvicorn clarion.server:app --reload"

echo Starting Frontend...
start "Clarion Frontend" cmd /k "cd gui && npm install && npm run tauri dev"

echo Services started!
echo Frontend: http://localhost:1420
echo Backend: http://localhost:8000/docs
