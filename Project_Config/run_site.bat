@echo off
title AI AgriVision - Server Launcher
echo ==============================================
echo      Starting AI AgriVision Servers...
echo ==============================================
echo.

echo [1/3] Starting Vite Frontend Server...
start "Frontend (Vite)" cmd /k "npm run dev"

echo [2/3] Starting Gateway API Server...
start "Gateway API" cmd /k "venv312\Scripts\python.exe api.py"

echo [3/3] Starting Chatbot Server...
start "Chatbot API" cmd /k "cd Models\Chatbot && set PYTHONIOENCODING=utf-8 && ..\..\venv312\Scripts\python.exe main.py --api --port 5000"

echo.
echo All servers have been launched in separate windows!
echo You can now open your browser and go to http://localhost:8080/
echo.
pause
