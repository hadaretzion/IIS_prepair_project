"""PrepAIr Backend - FastAPI main application."""

import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from backend.db import init_db
from backend.routers import users, cv, jd, interview, progress, tts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PrepAIr API",
    description="AI-Powered Career Preparation Platform",
    version="1.0.0"
)

# CORS middleware (allow all origins for Replit environment)
# IMPORTANT: CORS middleware must be added BEFORE routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(tts.router)


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with user-friendly messages."""
    errors = exc.errors()
    messages = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        messages.append(f"{field}: {msg}")
    
    logger.warning(f"Validation error: {messages}")
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(messages) if messages else "Invalid request data"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully."""
    logger.error(f"Unhandled error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
