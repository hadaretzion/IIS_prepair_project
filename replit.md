# PrepAIr - AI-Powered Career Preparation Platform

## Overview
PrepAIr is a full-stack application that helps job seekers optimize their CVs and practice interviews using Google Gemini 2.5 Pro AI via Replit AI Integrations (no personal API key needed).

## Project Structure
```
.
├── app/              # React + Vite + TypeScript frontend (port 5000)
│   └── src/
│       ├── pages/        # Page components (Landing, DocumentSetup, etc.)
│       ├── components/   # Shared UI components (Toast, ErrorBoundary, LoadingSpinner)
│       ├── api/          # API client
│       └── voice/        # TTS/STT utilities
├── backend/          # FastAPI + SQLite backend (port 8000)
│   ├── routers/          # API route handlers
│   ├── services/         # Business logic (gemini_client, cv_analyzer, scoring)
│   └── models.py         # SQLModel database models
├── docs/             # API documentation
├── src/              # Legacy data files (CSV sources)
└── tests/            # Test files
```

## Tech Stack
- **Frontend**: React 18, Vite 5, TypeScript, React Router v6
- **Backend**: FastAPI, SQLModel, SQLite, Pydantic
- **AI**: Google Gemini 2.5 Pro (via Replit AI Integrations)
- **UI**: Modern dark theme with glassmorphism effects, Inter font

## Running the Application
The workflow runs both servers:
- Frontend: `cd app && npm run dev` (port 5000)
- Backend: `uvicorn backend.main:app --host localhost --port 8000`

## Environment Variables
- `AI_INTEGRATIONS_GEMINI_API_KEY`: Auto-provided by Replit AI Integrations
- `AI_INTEGRATIONS_GEMINI_BASE_URL`: Auto-provided by Replit AI Integrations
- `VITE_BACKEND_URL`: Backend URL (default: http://localhost:8000)

## Key Features
1. CV upload and AI-powered analysis
2. Job description matching with role profile extraction
3. AI-powered interview practice with scoring and feedback
4. CV improvement suggestions with before/after examples
5. Progress tracking dashboard
6. Modern UI with toast notifications, error boundaries, and loading states

## Recent Changes (January 2026)
- **Voice Conversation Interview**: Redesigned interview as a chat-style voice conversation
  - AI interviewer speaks questions aloud using Text-to-Speech (Web Speech API)
  - User responds verbally via Speech-to-Text (browser native, no API key needed)
  - Real-time transcript display during recording
  - Voice controls: mute/unmute, repeat last message, recording indicator
  - Questions still sourced from 2,487-question database/RAG system
- Complete UI redesign with modern dark theme (#0a0a0f background)
- Glassmorphism effects with backdrop blur and glass borders
- New accent gradient (indigo/violet: #6366f1 → #8b5cf6 → #a855f7)
- Inter font family for modern typography
- Smooth animations (fadeIn, slideUp, float effects)
- Integrated Gemini AI via Replit AI Integrations (no API key needed)
- Toast notification system replacing all alert() calls
- ErrorBoundary and LoadingSpinner components
- Enhanced CV analysis with AI-powered gap detection and suggestions
- Input validation with field length limits

## User Preferences
- Step-by-step approach preferred
- This is a prototype without authentication
- Uses Replit's built-in AI integrations (charged to credits)
