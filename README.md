# PrepAIr: AI-Powered Career Preparation Platform

A full end-to-end prototype for AI-powered career preparation. Help job seekers optimize their CVs and practice interviews using **Google Gemini 2.5 Pro**.

## 📋 Quick Overview

PrepAIr is a monorepo with two main components:

- **`backend/`** - FastAPI + SQLite backend API ([see backend/README.md](backend/README.md))
- **`app/`** - React + Vite + TypeScript frontend ([see app/README.md](app/README.md))

## 🚀 Quick Start

1. **Backend Setup:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r backend/requirements.txt
   python -m backend.services.ingest  # Load questions
   uvicorn backend.main:app --reload --port 8000
   ```

2. **Frontend Setup:**
   ```bash
   cd app
   npm install
   npm run dev
   ```

3. **Configure:**
   - Set `GEMINI_API_KEY` in `.env` or `api_keys.json`
   - See [SETUP_WORKFLOW.md](SETUP_WORKFLOW.md) for detailed steps

4. **Open:** `http://localhost:5173`

## 📁 Project Structure

```
.
├── backend/          # FastAPI backend (see backend/README.md)
├── app/              # React frontend (see app/README.md)
├── docs/             # API documentation (see docs/api.yaml)
└── src/              # Legacy data files (CSV sources)
 ```

## 📚 Documentation

- **[SETUP_WORKFLOW.md](SETUP_WORKFLOW.md)** - Detailed setup instructions
- **[LOGIC_DECISIONS.md](LOGIC_DECISIONS.md)** - Architecture & design decisions
- **[docs/api.yaml](docs/api.yaml)** - Complete API specification
- **[backend/README.md](backend/README.md)** - Backend setup & architecture
- **[app/README.md](app/README.md)** - Frontend setup & structure

## 🔑 Environment Variables

Create `.env` in the root:

```bash
GEMINI_API_KEY=your_api_key_here
DATA_DIR=src/data/questions_and_answers
DB_PATH=backend/data/app.db
VITE_BACKEND_URL=http://localhost:8000
```

## 🎯 System Flow

1. **Landing** → Choose to start interview or improve CV
2. **Document Setup** → Upload CV + Job Description
3. **(Optional) CV Improve** → Analyze CV, see suggestions, save version
4. **Pre-Interview** → Review plan and settings
5. **Interview Room** → Voice/text interview with AI questions
6. **Done** → Interview complete
7. **Dashboard** → View readiness scores and progress

## 📝 Notes

- Uses **Gemini 2.5 Pro** for all LLM operations (no OpenAI)
- SQLite database (auto-created at `backend/data/app.db`)
- Voice features require Chrome/Edge (Web Speech API)
- See folder-specific READMEs for detailed information
