@echo off
title AI AgriVision Launcher
echo ==========================================
echo       AI AgriVision Server Launcher
echo ==========================================
echo.

set PYTHONIOENCODING=utf-8

:: 1. Start Chatbot API Server (FastAPI on port 5000)
echo [1/3] Launching Chatbot Server...
start "AI AgriVision - Chatbot Server (Port 5000)" cmd /k "cd Models\Chatbot && python main.py --api --port 5000"

:: 2. Start Gateway API Server (FastAPI on port 8000)
echo [2/3] Launching Gateway Server...
start "AI AgriVision - Gateway Server (Port 8000)" cmd /k "python api.py"

:: 3. Start Frontend Dev Server (Vite on port 8080)
echo [3/3] Launching Frontend Server...
start "AI AgriVision - Frontend Server (Port 8080)" cmd /k "npm run dev"

echo.
echo ==========================================
echo   All servers launched in separate windows!
echo   Please wait a few seconds, then open:
echo   --> http://localhost:8080
echo ==========================================
echo.
pause
