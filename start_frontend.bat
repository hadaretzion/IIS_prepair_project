@echo off
REM PrepAIr Frontend Server Startup Script
echo Starting PrepAIr Frontend Server...

REM Navigate to app directory
cd app

REM Install dependencies if node_modules doesn't exist
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)

REM Start the development server
call npm run dev
