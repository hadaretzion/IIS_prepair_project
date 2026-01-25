# How to Run PrepAIr

## Quick Start (Windows)

### Option 1: Using Batch Scripts (Easiest)

1. **Setup Backend (First Time Only):**
   ```cmd
   setup_backend.bat
   ```
   This will:
   - Create/activate virtual environment
   - Install Python dependencies
   - Create .env file (you'll need to add your GEMINI_API_KEY)
   - Ingest question data

2. **Start Backend:**
   ```cmd
   start_backend.bat
   ```
   Backend will run on `http://localhost:8000`

3. **Start Frontend (in a new terminal):**
   ```cmd
   start_frontend.bat
   ```
   Frontend will run on `http://localhost:5173`

### Option 2: Manual Setup

#### Backend Setup:

1. Create virtual environment:
   ```cmd
   py -m venv venv
   venv\Scripts\activate
   ```

2. Install dependencies:
   ```cmd
   pip install -r backend\requirements.txt
   ```

3. Create `.env` file in project root:
   ```
   GEMINI_API_KEY=your_api_key_here
   DATA_DIR=src/data/questions_and_answers
   DB_PATH=backend/data/app.db
   VITE_BACKEND_URL=http://localhost:8000
   ```

4. Ingest question data:
   ```cmd
   python -m backend.services.ingest
   ```

5. Start backend:
   ```cmd
   uvicorn backend.main:app --reload --port 8000
   ```

#### Frontend Setup:

1. Navigate to app directory:
   ```cmd
   cd app
   ```

2. Install dependencies:
   ```cmd
   npm install
   ```

3. Start frontend:
   ```cmd
   npm run dev
   ```

## Access the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Important Notes

1. **GEMINI_API_KEY:** You need a Google Gemini API key. Get one at: https://makersuite.google.com/app/apikey
   - Add it to the `.env` file
   - The system will work without it but will use fallback heuristics

2. **Two Terminals Required:**
   - Terminal 1: Backend server (port 8000)
   - Terminal 2: Frontend server (port 5173)

3. **First Time Setup:**
   - Make sure to run `python -m backend.services.ingest` to load questions into the database
   - This only needs to be done once (or when you want to reload questions)

## Troubleshooting

- **Port already in use:** Change the port in the command (e.g., `--port 8001`)
- **Module not found:** Make sure virtual environment is activated
- **npm errors:** Make sure Node.js 18+ is installed
- **Database errors:** The database is auto-created at `backend/data/app.db`
