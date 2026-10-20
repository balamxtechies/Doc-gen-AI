@echo off
title Autonomous AI Document Extraction Platform - DocuGen AI
color 0A

echo ======================================================================
echo   DocuGen AI - Autonomous Document API & Extraction Platform
echo ======================================================================
echo.

cd /d "%~dp0"

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please set up the venv first.
    pause
    exit /b 1
)

echo [INFO] Starting FastAPI Microservice on http://localhost:8000 ...
echo [INFO] Press Ctrl+C to stop the server.
echo.

venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
