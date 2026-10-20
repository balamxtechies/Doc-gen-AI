@echo off
title Active Microservices and Ports Checker
color 0B

cd /d "%~dp0"
venv\Scripts\python.exe check_ports.py

pause
