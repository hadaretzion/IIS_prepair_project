@echo off
REM PrepAIr Backend Setup Script
echo Setting up PrepAIr Backend...

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    py -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
pip install -r backend\requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    echo GEMINI_API_KEY=your_api_key_here > .env
    echo DATA_DIR=src/data/questions_and_answers >> .env
    echo DB_PATH=backend/data/app.db >> .env
    echo VITE_BACKEND_URL=http://localhost:8000 >> .env
    echo.
    echo Please edit .env and add your GEMINI_API_KEY
)

REM Ingest question data
echo.
echo Ingesting question data...
python -m backend.services.ingest

echo.
echo Backend setup complete!
echo.
echo To start the backend server, run:
echo   start_backend.bat
echo.
pause
