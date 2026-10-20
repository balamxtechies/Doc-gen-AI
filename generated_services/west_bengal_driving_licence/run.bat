@echo off
title Driving Licence Microservice (Port 8004)
echo Starting Standalone Document Extraction Service for Driving Licence...
echo Running locally on port 8004 with ZERO AI API calls.
cd /d "%~dp0"
..\..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8004
pause
