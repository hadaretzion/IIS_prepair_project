## Plan: Code Execution + Progressive Refinement for Interview Questions

TL;DR: Add two interconnected features: (1) live code execution with Monaco Editor so users can run and test code during interviews, and (2) progressive refinement for code questions that guides users from naive to optimal solutions. Includes safeguards for API costs, state management, and user experience.

### Steps

1) Add backend code execution endpoint
- Create backend/routers/code.py with POST /api/code/execute
- Forward code to Judge0 API (free tier, 50 calls/day)
- Support Python, JavaScript, Java, C++
- Handle timeouts (10s max), return stdout/stderr/errors
- Register router in backend/main.py

2) Extend database models for multi-attempt tracking
- Update backend/models.py InterviewTurn:
  - Add turn_type: enum ("initial" | "refinement" | "followup")
  - Add attempt_number: int (1, 2, 3)
  - Add interviewer_hint: Optional[str]
- Update InterviewSession:
  - Add current_question_id: str (separate from turn count)
  - Add current_question_complete: bool
  - Add current_attempt: int (1-3)

3) Build progressive refinement logic in backend
- Update backend/routers/interview.py /api/interview/next:
  - After scoring, detect if solution is optimal or needs refinement
  - If suboptimal AND attempt < 3: generate hint, stay on question
  - If optimal OR attempt >= 3 OR user says "skip": move to next question
  - Cap at 3 attempts per question (hard limit)
- Add to backend/services/scoring.py:
  - is_optimal boolean in score response
  - refinement_hint string when not optimal
  - Language-aware evaluation (don’t penalize Java verbosity)

4) Add skip/surrender detection
- In backend/routers/interview.py:
  - Detect keywords: "skip", "next question", "I give up", "I don't know", "move on"
  - Accept explicit skip_question: true flag from frontend
  - When detected: mark question complete, move to next

5) Upgrade frontend code editor
- In app/src/pages/InterviewRoom.tsx:
  - Replace textarea whiteboard with Monaco Editor (@monaco-editor/react)
  - Add language selector dropdown
  - Add "Run Code" button → calls /api/code/execute
  - Add output console panel (stdout, stderr, execution time)
  - Track which code version is "submitted" vs just "run"

6) Update interview UI for multi-attempt flow
- In app/src/pages/InterviewRoom.tsx:
  - Show dual progress: "Question 3/6 • Attempt 2/3"
  - Display interviewer hint prominently when received
  - Add "Skip Question" button (explicit surrender)
  - Show per-question timer (10 min max, visual warning at 8 min)
  - Auto-progress when timer expires

7) Update scoring and final score logic
- In backend/services/scoring.py:
  - Store all attempt scores in attempt_scores_json
  - Calculate final_score = best attempt
  - For API response: include is_optimal, refinement_hint, can_refine (attempt < 3)

8) Update feedback page for multi-attempt display
- In app/src/pages/FeedbackPlaceholder.tsx:
  - Group turns by question_id
  - Show collapsible attempts under each question
  - Display progression: "Attempt 1: O(n²) → Attempt 2: O(n) ✓"
  - Highlight hints given and how user improved

### Safeguards Built Into Plan
- API cost explosion: 3 attempt cap, lightweight hint prompts
- Infinite loop: Hard 3-attempt limit + 10 min timer
- Session state corruption: Separate current_question_id from turn count
- Scoring confusion: final_score = best attempt, store all attempts
- Follow-up vs refinement conflict: Explicit turn_type enum
- Optimal first solution: Detect is_optimal → skip refinement, move on
- User wants to skip: "Skip" button + keyword detection
- Voice/code mismatch: Prompt AI to prioritize code for code questions
- Language bias: Language-aware prompting in scorer
- Time hog questions: Per-question timer with auto-progress

### Further Considerations
- First-solution-is-optimal flow: If user nails it on attempt 1, proceed immediately, don’t force refinement
- Hint quality control: Add example hints in prompt for consistency; optional rating later
- Feedback page complexity: Decide default expanded/collapsed attempts; optionally show only final attempt with history toggle


## Plan: Code Execution + Progressive Refinement + Interview UX Tweaks

TL;DR: Add live code execution and progressive refinement, plus user-controlled question-count visibility, remove the visible timer, and use hidden per-question/hint timers scaled by difficulty.

### Steps

1) Add backend code execution endpoint
- Create backend/routers/code.py with POST /api/code/execute
- Forward to Judge0 (free tier), support Python/JS/Java/C++; 10s timeout; return stdout/stderr/errors
- Register router in backend/main.py

2) Extend database models for multi-attempt tracking
- InterviewTurn: add turn_type ("initial" | "refinement" | "followup"), attempt_number (1-3), interviewer_hint (optional)
- InterviewSession: add current_question_id, current_question_complete, current_attempt (1-3)

3) Build progressive refinement logic in backend
- /api/interview/next: if suboptimal and attempt<3 → hint + stay; if optimal or attempt≥3 or user skips → next; cap attempts at 3
- scoring: add is_optimal, refinement_hint; language-aware evaluation

4) Add skip/surrender detection
- Detect keywords (“skip”, “next question”, “I give up”, “I don’t know”, “move on”)
- Accept skip_question flag; mark complete and move on

5) Upgrade frontend code editor
- In InterviewRoom: swap textarea for Monaco Editor; language selector; Run Code → /api/code/execute; output console; track “submitted” vs “just run”

6) Interview UI controls for progress visibility and no visible timer
- PreInterview: add toggle “Show question progress” (persist in localStorage)
- InterviewRoom: conditionally render Q#/total only if toggle is on; remove visible timer entirely

7) Hidden per-question and hint timers (difficulty-based, invisible)
- Use question.difficulty to set limits, e.g.:
  - Easy: hint ~60–90s, cutoff ~4–5 min
  - Medium: hint ~120–150s, cutoff ~7–8 min
  - Hard: hint ~180–210s, cutoff ~10–12 min
- On hint timer: inject interviewer_hint; on cutoff: prompt to wrap or auto-advance

8) Update scoring and final score logic
- Store attempt_scores_json; final_score = best attempt; include is_optimal, refinement_hint, can_refine (attempt<3)

9) Update feedback page for multi-attempt display
- Group turns by question_id; collapsible attempts; show progression (Attempt 1 → Attempt 2 ✓); highlight hints and improvements

### Safeguards Built Into Plan
- API cost: 3-attempt cap, lightweight hint prompts
- Loop prevention: 3-attempt limit; hidden timers for cutoff
- State integrity: track current_question_id separately
- Scoring clarity: final_score = best attempt; store all attempts
- Follow-up vs refinement: explicit turn_type
- Optimal first solution: detect is_optimal → skip refinement
- Skip support: skip button + keyword detection
- Voice/code mismatch: prompt AI to prioritize code for code questions
- Language bias: language-aware scoring
- Hidden timers: per-question/hint timers are invisible; only drive hints/cutoffs

### Further Considerations
- Default for “Show question progress” toggle (suggest OFF for realism)
- Exact timing values per difficulty can be tweaked after first test pass
- Feedback view: default collapse attempts to reduce clutter
