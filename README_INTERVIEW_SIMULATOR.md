# PrepAIr Interview Simulator

A full-stack interview simulation prototype built with FastAPI (backend) and React + TypeScript (frontend), powered by Google Gemini 2.5 Pro for intelligent question selection and answer evaluation.

## 🎯 Overview

The Interview Simulator provides a realistic interview experience where users can practice answering questions tailored to their CV and job description. The system uses AI to:

- Extract role profiles from CV and JD
- Select personalized questions from a question bank
- Evaluate answers in real-time
- Adapt question difficulty based on performance
- Track question history to avoid repetition

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI
- **Database**: SQLite with SQLModel ORM
- **AI**: Google Gemini 2.5 Pro (via `GEMINI_API_KEY` environment variable)
  - Uses `gemini-2.5-pro` model for all LLM operations (role extraction, answer scoring, follow-up generation)
  - Model configured in `cv_improvement_services/gemini_client.py` via `call_gemini_json()`
- **Data Sources**: CSV files with questions and code problems

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router
- **Voice**: Web Speech API (TTS/STT) with graceful fallback to text input

## 📁 Project Structure

```
.
├── interview_backend/          # Interview Simulator Backend (FastAPI)
│   ├── main.py                 # FastAPI application and endpoints
│   ├── models.py               # Database models (SQLModel)
│   ├── database.py             # Database setup and session management
│   ├── config.py               # Configuration and paths
│   ├── ingest.py               # CSV data ingestion script
│   ├── gemini_helpers.py       # Gemini API integration
│   ├── question_selector.py    # Question selection algorithm
│   ├── interview_engine.py     # Interview runtime logic
│   └── requirements.txt        # Python dependencies
│
├── interview_frontend/         # Interview Simulator Frontend (React)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── StartPage.tsx   # Interview start page
│   │   │   ├── InterviewPage.tsx  # Main interview interface
│   │   │   └── FeedbackPage.tsx   # Placeholder feedback page
│   │   ├── App.tsx             # Main app component with routing
│   │   ├── main.tsx            # Entry point
│   │   └── types/              # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
│
└── data/
    └── questions_and_answers/  # CSV question banks
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Backend Setup

1. **Navigate to interview_backend directory:**
   ```bash
   cd interview_backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variable:**
   ```bash
   # Linux/Mac
   export GEMINI_API_KEY="your_api_key_here"
   
   # Windows PowerShell
   $env:GEMINI_API_KEY="your_api_key_here"
   
   # Windows CMD
   set GEMINI_API_KEY=your_api_key_here
   ```

4. **Run the backend server:**
   ```bash
   python main.py
   # Or using uvicorn directly:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will:
   - Initialize the SQLite database
   - Automatically ingest questions from CSV files if the database is empty
   - Start the API server on `http://localhost:8000`

### Frontend Setup

1. **Navigate to interview_frontend directory (in a new terminal):**
   ```bash
   cd interview_frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will start on `http://localhost:5173`

4. **Open your browser:**
   Navigate to `http://localhost:5173`

## 📖 Usage Guide

### Starting an Interview

1. **On the Start Page:**
   - Select interview mode:
     - **Direct Mode**: Skip CV improvement, use basic CV text
     - **After CV Mode**: Use improved CV version (if available)
   - Paste your CV text (optional for direct mode)
   - Paste the Job Description (required)
   - Click "🚀 Start Interview"

2. **The system will:**
   - Extract role profile from CV and JD
   - Build a personalized interview plan (5 open questions + 3 code questions by default)
   - Start the first question

### During the Interview

1. **Answer questions:**
   - **Voice Mode**: Click the mic button to start recording. Speak your answer, then click again to stop and submit.
   - **Text Mode**: If voice is not supported, type your answer in the text area and click "Submit Answer".

2. **Interview controls:**
   - **Repeat Question**: Replays the current question via TTS
   - **Show Subtitles**: Toggle to see question text (may reduce realism)
   - **End Interview**: Exit early and go to feedback

3. **Progress tracking:**
   - Timer shows elapsed time
   - Progress bar shows question completion
   - Interviewer provides brief acknowledgements after each answer

### After the Interview

- You'll be redirected to the Feedback page (placeholder)
- The full session data is stored in the database
- You can retrieve session details via the API

## 🔌 API Endpoints

### `POST /api/interview/start`
Start a new interview session.

**Request Body:**
```json
{
  "mode": "direct" | "after_cv",
  "cv_text": "string",
  "jd_text": "string (required)",
  "cv_version_id": "string (optional)",
  "settings": {
    "num_open": 5,
    "num_code": 3,
    "duration_minutes": 30
  }
}
```

**Response:**
```json
{
  "session_id": 1,
  "plan": {
    "items": [...],
    "total_questions": 8
  },
  "first_question": {...}
}
```

### `POST /api/interview/next`
Submit an answer and get the next question.

**Request Body:**
```json
{
  "session_id": 1,
  "user_transcript": "string",
  "user_code": "string (optional)",
  "client_metrics": {
    "seconds_spoken": 30
  }
}
```

**Response:**
```json
{
  "interviewer_message": "Thank you for your answer...",
  "next_question": {...} | null,
  "is_done": false,
  "progress": {"current": 2, "total": 8},
  "score": 75
}
```

### `GET /api/interview/session/{session_id}`
Get full interview session data including all turns.

## 🗄️ Database Schema

- **users**: User accounts (with auto-created guest users)
- **question_bank**: Questions loaded from CSV files
- **job_specs**: Job descriptions with extracted role profiles
- **interview_sessions**: Interview session metadata
- **interview_turns**: Q&A pairs with scores
- **question_history**: Tracks which questions were asked to avoid repetition
- **user_skill_state**: Adaptive skill tracking for future interviews

## 🔧 Configuration

Edit `interview_backend/config.py` to customize:

- Database path (`DATABASE_URL`)
- Data file paths (`DATA_DIR`, `CSV_PATHS`)
- Default interview settings (number of questions, duration)
- Similarity thresholds for plan diversity

## 🌐 Data Sources

The system loads questions from CSV files in `data/questions_and_answers/`:

- `all_open_questions_with_topics.csv` - Open-ended questions with topic tags
- `all_code_questions_with_topics.csv` - Coding questions with topics
- `all_open_questions.csv` - Fallback open questions
- `leetcode_problems_data.csv` - LeetCode-style problems

The ingestion script (`interview_backend/ingest.py`) runs automatically on backend startup if the database is empty.

## 🎤 Voice Features

### Browser Compatibility

- **TTS (Text-to-Speech)**: Supported in all modern browsers
- **STT (Speech-to-Speech)**: 
  - Chrome/Edge: Full support via Web Speech API
  - Firefox/Safari: Limited support (falls back to text input)

If STT is not available, the UI automatically shows a text input area instead of the mic button.

## ⚠️ Known Limitations

- **Prototype Quality**: This is a study/project prototype, not production-ready
- **Voice Recognition**: Works best in Chrome/Edge; other browsers may require text input
- **Question Bank**: Limited to available CSV files; more questions can be added via CSV
- **Feedback Page**: Currently a placeholder; detailed feedback analysis is not yet implemented

## 🐛 Troubleshooting

### Backend won't start
- Check that `GEMINI_API_KEY` is set correctly
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that data CSV files exist in `data/questions_and_answers/`

### Frontend won't connect to backend
- Ensure backend is running on port 8000
- Check CORS settings in `interview_backend/main.py` if using a different frontend port
- Verify proxy settings in `interview_frontend/vite.config.ts`

### Voice recognition not working
- Use Chrome or Edge browser for best compatibility
- Check browser permissions for microphone access
- If unsupported, the UI will automatically show text input

### Questions not loading
- Check that CSV files are in the correct location
- Run ingestion manually: `cd interview_backend && python ingest.py`
- Check database file permissions

## 📝 Development Notes

- The database file (`interview_simulator.db`) is created in the interview_backend directory
- Data ingestion is idempotent (safe to run multiple times)
- Question selection avoids repeating questions from the last 3 sessions for the same user+JD combination
- Plans are checked for diversity using Jaccard similarity threshold

## 🚢 Deployment (Replit-ready)

The codebase is designed to work on Replit:

1. Set `GEMINI_API_KEY` in Replit Secrets
2. Update `DATA_DIR` in `interview_backend/config.py` if CSV files are in `/mnt/data`
3. Backend runs on port 8000; frontend on 5173
4. Both can run in separate Replit consoles or use a single main.py with subprocess


## 🤖 AI Model Configuration

The interview simulator uses **Google Gemini 2.5 Pro** (`gemini-2.5-pro`) for all LLM operations:

- **Role Profile Extraction**: Analyzes CV and JD to extract topics, weights, and seniority level
- **Answer Scoring**: Evaluates user answers with strengths, weaknesses, and topic-specific scores
- **Follow-up Generation**: Generates contextual follow-up questions when appropriate

The model is configured in `cv_improvement_services/gemini_client.py` and shared between the CV improvement and interview simulator modules. All Gemini API calls use the `call_gemini_json()` function which enforces JSON responses.
