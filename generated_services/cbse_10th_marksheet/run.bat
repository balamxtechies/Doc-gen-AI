@echo off
title 10th marksheet Microservice (Port 8002)
echo Starting Standalone Document Extraction Service for 10th marksheet...
echo Running locally on port 8002 with ZERO AI API calls.
cd /d "%~dp0"
..\..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8002
pause
