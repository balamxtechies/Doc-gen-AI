@echo off
title PAN Card Microservice (Port 8003)
echo Starting Standalone Document Extraction Service for PAN Card...
echo Running locally on port 8003 with ZERO AI API calls.
cd /d "%~dp0"
..\..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8003
pause
