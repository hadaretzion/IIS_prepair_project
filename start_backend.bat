@echo off
REM PrepAIr Backend Server Startup Script
echo Starting PrepAIr Backend Server...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the server
uvicorn backend.main:app --reload --port 8000
