"""PrepAIr Backend - FastAPI main application."""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.db import init_db
from backend.routers import users, cv, jd, interview, progress

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PrepAIr API",
    description="AI-Powered Career Preparation Platform",
    version="1.0.0"
)

# CORS middleware (allow app dev origin)
# IMPORTANT: CORS middleware must be added BEFORE routers
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",  # Allow localhost on any port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(cv.router)
app.include_router(jd.router)
app.include_router(interview.router)
app.include_router(progress.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("🚀 Starting PrepAIr backend...")
    init_db()
    logger.info("✅ Database initialized")
    
    # Check if question bank is empty, suggest running ingest
    from backend.db import engine
    from backend.models import QuestionBank
    from sqlmodel import Session, select
    
    with Session(engine) as session:
        count = len(list(session.exec(select(QuestionBank)).all()))
        if count == 0:
            logger.warning("⚠️  Question bank is empty. Run: python -m backend.services.ingest")
        else:
            logger.info(f"📚 Question bank has {count} questions")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PrepAIr API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
