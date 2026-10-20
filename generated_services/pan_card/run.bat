@echo off
title PAN card Microservice (Port 8001)
echo Starting Standalone Document Extraction Service for PAN card...
echo Running locally on port 8001 with ZERO AI API calls.
cd /d "%~dp0"
..\..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
pause
