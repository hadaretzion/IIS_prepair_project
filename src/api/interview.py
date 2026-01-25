"""Deprecated legacy API module. Use backend/routers/interview.py instead."""

raise RuntimeError(
    "Legacy interview API is disabled. Use backend.main:app and backend/routers/interview.py instead."
)

app = FastAPI(title="PrepAIr Interview Simulator API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and ingest data on startup."""
    init_db()
    
    # Check if question bank is empty, if so run ingestion
    with Session(engine) as session:
        count = session.exec(select(QuestionBank)).first()
        if count is None:
            print("📚 Question bank is empty. Running data ingestion...")
            try:
                ingest_data()
            except Exception as e:
                print(f"⚠️  Ingestion warning: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PrepAIr Interview Simulator API", "status": "running"}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def get_or_create_user(session: Session, user_id: Optional[int] = None) -> User:
    """Get existing user or create a temporary one."""
    if user_id:
        user = session.get(User, user_id)
        if user:
            return user
    
    # Create temporary user
    user = User(
        name="Guest User",
        email=None
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_or_create_job_spec(session: Session, jd_text: str) -> JobSpec:
    """Get or create job specification."""
    jd_hash = hashlib.md5(jd_text.encode()).hexdigest()
    
    job_spec = session.exec(
        select(JobSpec).where(JobSpec.jd_hash == jd_hash)
    ).first()
    
    if job_spec:
        return job_spec
    
    # Extract role profile
    try:
        role_profile = extract_role_profile("", jd_text)  # CV text can be empty for direct mode
        role_profile_json = json.dumps(role_profile)
    except Exception as e:
        print(f"⚠️  Role profile extraction failed: {e}")
        role_profile_json = None
    
    job_spec = JobSpec(
        jd_hash=jd_hash,
        jd_text=jd_text,
        role_profile=role_profile_json
    )
    session.add(job_spec)
    session.commit()
    session.refresh(job_spec)
    return job_spec


@app.post("/api/interview/start")
async def start_interview(
    request: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Start a new interview session.
    
    Body:
    {
        "user_id": int (optional),
        "mode": "direct" | "after_cv",
        "cv_text": str,
        "jd_text": str,
        "cv_version_id": str (optional, for after_cv mode),
        "settings": {
            "num_open": int (optional),
            "num_code": int (optional),
            "duration_minutes": int (optional)
        }
    }
    """
    user_id = request.get("user_id")
    mode_str = request.get("mode", "direct")
    cv_text = request.get("cv_text", "")
    jd_text = request.get("jd_text", "")
    cv_version_id = request.get("cv_version_id")
    settings = request.get("settings", {})
    
    if not jd_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jd_text is required"
        )
    
    # Validate mode
    try:
        mode = InterviewMode(mode_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {mode_str}. Must be 'direct' or 'after_cv'"
        )
    
    # Get or create user
    user = get_or_create_user(session, user_id)
    
    # Get or create job spec
    job_spec = get_or_create_job_spec(session, jd_text)
    
    # Extract role profile (if not already extracted or if CV is provided)
    if cv_text or not job_spec.role_profile:
        try:
            role_profile = extract_role_profile(cv_text or "", jd_text)
            job_spec.role_profile = json.dumps(role_profile)
            session.add(job_spec)
            session.commit()
        except Exception as e:
            print(f"⚠️  Role profile extraction failed: {e}")
            # Use default
            role_profile = {
                "topics": [{"name": "General Programming", "weight": 0.7}],
                "seniority": "mid",
                "focus_areas": []
            }
    else:
        role_profile = json.loads(job_spec.role_profile)
    
    # Build interview plan
    num_open = settings.get("num_open", DEFAULT_NUM_OPEN)
    num_code = settings.get("num_code", DEFAULT_NUM_CODE)
    
    plan_items = build_interview_plan(
        session, role_profile, user.id, job_spec.jd_hash,
        num_open=num_open, num_code=num_code
    )
    
    # Check plan diversity (re-generate if too similar)
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts and not check_plan_diversity(session, user.id, job_spec.jd_hash, plan_items):
        attempt += 1
        plan_items = build_interview_plan(
            session, role_profile, user.id, job_spec.jd_hash,
            num_open=num_open, num_code=num_code
        )
    
    # Create interview session
    interview_session = InterviewSession(
        user_id=user.id,
        job_spec_id=job_spec.id,
        mode=mode,
        cv_text=cv_text if cv_text else None,
        cv_version_id=cv_version_id,
        plan=json.dumps(plan_items),
        status="active"
    )
    session.add(interview_session)
    session.commit()
    session.refresh(interview_session)
    
    # Get first question
    first_question_data = get_next_question(session, interview_session, 0)
    
    return {
        "session_id": interview_session.id,
        "plan": {
            "items": plan_items,
            "total_questions": len(plan_items)
        },
        "first_question": first_question_data
    }


@app.post("/api/interview/next")
async def next_interview_step(
    request: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Process answer and get next question.
    
    Body:
    {
        "session_id": int,
        "user_transcript": str,
        "user_code": str (optional),
        "client_metrics": dict (optional)
    }
    """
    session_id = request.get("session_id")
    user_transcript = request.get("user_transcript", "")
    user_code = request.get("user_code")
    client_metrics = request.get("client_metrics")
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required"
        )
    
    interview_session = session.get(InterviewSession, session_id)
    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )
    
    if interview_session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview session is not active"
        )
    
    # Get current turn number from existing turns
    turns = session.exec(
        select(InterviewTurn).where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.turn_number.desc())
    ).first()
    
    turn_number = (turns.turn_number + 1) if turns else 0
    
    # Process answer
    result = process_answer(
        session,
        interview_session,
        turn_number,
        user_transcript,
        user_code,
        client_metrics
    )
    
    return result


@app.get("/api/interview/session/{session_id}")
async def get_session_data(
    session_id: int,
    session: Session = Depends(get_session)
):
    """Get full interview session data."""
    interview_session = session.get(InterviewSession, session_id)
    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )
    
    # Get turns
    turns = list(session.exec(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.turn_number)
    ).all())
    
    # Serialize turns
    turns_data = []
    for turn in turns:
        turn_dict = {
            "id": turn.id,
            "turn_number": turn.turn_number,
            "question_text": turn.question_text,
            "user_transcript": turn.user_transcript,
            "user_code": turn.user_code,
            "interviewer_message": turn.interviewer_message,
            "followup_question": turn.followup_question,
            "score_json": json.loads(turn.score_json) if turn.score_json else None,
            "created_at": turn.created_at.isoformat(),
        }
        if turn.client_metrics:
            turn_dict["client_metrics"] = json.loads(turn.client_metrics)
        turns_data.append(turn_dict)
    
    return {
        "id": interview_session.id,
        "user_id": interview_session.user_id,
        "mode": interview_session.mode,
        "status": interview_session.status,
        "started_at": interview_session.started_at.isoformat(),
        "ended_at": interview_session.ended_at.isoformat() if interview_session.ended_at else None,
        "plan": json.loads(interview_session.plan) if interview_session.plan else [],
        "turns": turns_data
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
