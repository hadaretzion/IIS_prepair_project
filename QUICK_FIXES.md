# Quick Fixes for PrepAIr Demo

## 🔴 CRITICAL: Fix InterviewRoom First Question

**File**: `app/src/pages/InterviewRoom.tsx`

**Current Code** (lines 47-50):
```typescript
const loadQuestion = async () => {
  // For MVP, we'll get the first question from the session start
  // In a full implementation, this would come from the API
};
```

**Fix Option 1: Store first question from startInterview response**
```typescript
// In DocumentSetup.tsx and CvImprove.tsx, after startInterview:
localStorage.setItem('firstQuestion', JSON.stringify(result.first_question));

// In InterviewRoom.tsx:
const loadQuestion = async () => {
  const stored = localStorage.getItem('firstQuestion');
  if (stored) {
    const firstQuestion = JSON.parse(stored);
    setQuestion(firstQuestion);
    setProgress({ turn_index: 0, total: result.total_questions });
    if (firstQuestion?.text) {
      speak(firstQuestion.text);
    }
    localStorage.removeItem('firstQuestion'); // Clean up
  }
};
```

**Fix Option 2: Fetch from API (Better)**
```typescript
// Add to app/src/api/client.ts:
getSession: (sessionId: string) =>
  apiRequest<any>(`/api/interview/session/${sessionId}`),

// In InterviewRoom.tsx:
const loadQuestion = async () => {
  if (!sessionId) return;
  
  try {
    const sessionData = await api.getSession(sessionId);
    const plan = sessionData.plan_json;
    const planItems = plan.items || [];
    
    if (planItems.length > 0) {
      const firstItem = planItems[0];
      const firstQuestionId = firstItem.selected_question_id;
      
      // Fetch question details
      // OR extract from plan if it includes question text
      // For now, we need to get it from the startInterview response
    }
  } catch (error) {
    console.error('Failed to load session:', error);
  }
};
```

**Recommended**: Use Option 1 for quick fix, Option 2 for proper implementation.

---

## 🔴 CRITICAL: Add File Upload Support

**File**: `app/src/pages/DocumentSetup.tsx`

**Add PDF upload functionality**:

1. Add file input:
```typescript
const [cvFile, setCvFile] = useState<File | null>(null);
const [jdFile, setJdFile] = useState<File | null>(null);

// Add file input in JSX:
<input
  type="file"
  accept=".pdf"
  onChange={(e) => {
    const file = e.target.files?.[0];
    if (file) setCvFile(file);
  }}
/>
```

2. Add PDF text extraction (client-side or backend):
```typescript
// Option A: Client-side (using pdf.js or similar)
// Option B: Backend endpoint (recommended)

// Add to backend/routers/cv.py:
@router.post("/ingest-pdf")
async def ingest_cv_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session: Session = Depends(get_session)
):
    from src.shared.pdf_extractor import extract_pdf_text
    import io
    
    contents = await file.read()
    pdf_file = io.BytesIO(contents)
    cv_text = extract_pdf_text(pdf_file)
    
    # Then use existing ingest_cv logic
    ...
```

---

## 🟡 IMPORTANT: Implement Feedback Page

**File**: `app/src/pages/FeedbackPlaceholder.tsx`

**Replace with actual feedback**:

```typescript
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';

function Feedback() {
  const { sessionId } = useParams();
  const [sessionData, setSessionData] = useState<any>(null);
  
  useEffect(() => {
    if (sessionId) {
      // Add getSession to API client first!
      api.getSession(sessionId).then(setSessionData);
    }
  }, [sessionId]);
  
  if (!sessionData) return <div>Loading...</div>;
  
  const turns = sessionData.turns || [];
  
  return (
    <div>
      <h1>Interview Feedback</h1>
      {turns.map((turn: any, idx: number) => (
        <div key={idx}>
          <h3>Question {idx + 1}</h3>
          <p>{turn.question_snapshot}</p>
          <p>Score: {(JSON.parse(turn.score_json).overall * 100).toFixed(1)}%</p>
          {/* More feedback details */}
        </div>
      ))}
    </div>
  );
}
```

**Also add to API client**:
```typescript
getSession: (sessionId: string) =>
  apiRequest<any>(`/api/interview/session/${sessionId}`),
```

---

## 🟡 IMPORTANT: Show Actual Plan in PreInterview

**File**: `app/src/pages/PreInterview.tsx`

**Fetch and display session plan**:

```typescript
useEffect(() => {
  if (sessionId) {
    // Store plan in localStorage from startInterview response
    // OR fetch from API
    const plan = JSON.parse(localStorage.getItem('planSummary') || '{}');
    setPlanSummary(plan);
  }
}, [sessionId]);
```

---

## 🟢 NICE TO HAVE: Use Settings

**File**: `app/src/pages/InterviewRoom.tsx`

**Actually use voice/captions settings**:

```typescript
// Get settings from localStorage or props
const voiceOn = localStorage.getItem('voiceOn') === 'true';
const captionsOn = localStorage.getItem('captionsOn') === 'true';

// Use in component:
{voiceOn && question?.text && speak(question.text)}
{captionsOn && <div className="captions">...</div>}
```

---

## Priority Order for Demo

1. ✅ Fix InterviewRoom first question (CRITICAL - breaks flow)
2. ✅ Add file upload (CRITICAL - demo usability)
3. ✅ Implement feedback page (IMPORTANT - user expectation)
4. ✅ Show plan in PreInterview (IMPORTANT - better UX)
5. ⚪ Use settings (Nice to have)
