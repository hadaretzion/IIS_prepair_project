/** API client for PrepAIr backend. */

// Use relative URLs - Vite proxy handles forwarding /api to backend
// This works in dev (via Vite proxy) and in production (same domain)
const BACKEND_URL: string = '';

/** Interview settings passed to startInterview */
export interface InterviewSettings {
  num_open?: number;
  num_code?: number;
  duration_minutes?: number;
  persona?: 'friendly' | 'formal' | 'challenging';
  question_style?: number; // 0 = professional, 100 = personal
  language?: 'english' | 'hebrew';
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BACKEND_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Users
  ensureUser: (userId?: string) =>
    apiRequest<{ user_id: string }>('/api/users/ensure', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }),

  // CV
  ingestCV: (userId: string, cvText: string) =>
    apiRequest<{ cv_version_id: string }>('/api/cv/ingest', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, cv_text: cvText }),
    }),

  ingestCVPDF: async (userId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    
    const response = await fetch(`${BACKEND_URL}/api/cv/ingest-pdf`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  analyzeCV: (userId: string, cvVersionId: string, jobSpecId: string) =>
    apiRequest<{
      match_score: number;
      strengths: string[];
      gaps: string[];
      suggestions: string[];
      role_focus: any;
      cv_text: string;
    }>('/api/cv/analyze', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, cv_version_id: cvVersionId, job_spec_id: jobSpecId }),
    }),

  saveCV: (userId: string, updatedCvText: string, parentCvVersionId?: string) =>
    apiRequest<{ new_cv_version_id: string }>('/api/cv/save', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, updated_cv_text: updatedCvText, parent_cv_version_id: parentCvVersionId }),
    }),

  getCVImprovements: (userId: string, cvVersionId: string, jobSpecId: string) =>
    apiRequest<{
      success: boolean;
      improvements: {
        improved_sections: Array<{
          section: string;
          original: string;
          improved: string;
          explanation: string;
        }>;
        new_content_suggestions: string[];
        formatting_tips: string[];
      };
    }>('/api/cv/improve', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, cv_version_id: cvVersionId, job_spec_id: jobSpecId }),
    }),

  // JD
  ingestJD: (userId: string, jdText: string) =>
    apiRequest<{ job_spec_id: string; jd_hash: string; jd_profile_json?: any }>('/api/jd/ingest', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, jd_text: jdText }),
    }),

  ingestJDPDF: async (userId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    
    const response = await fetch(`${BACKEND_URL}/api/jd/ingest-pdf`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  // Interview
  startInterview: (userId: string, jobSpecId: string, cvVersionId: string | null, mode: string, settings?: InterviewSettings) =>
    apiRequest<{
      session_id: string;
      plan_summary: any;
      first_question: any;
      total_questions: number;
    }>('/api/interview/start', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        job_spec_id: jobSpecId,
        cv_version_id: cvVersionId,
        mode,
        settings: settings || { num_open: 4, num_code: 2, duration_minutes: 12, persona: 'friendly' },
      }),
    }),

  nextInterview: (sessionId: string, userTranscript: string, userCode?: string, isFollowup?: boolean, elapsedSeconds?: number) =>
    apiRequest<{
      interviewer_message: string;
      followup_question?: { text: string };
      next_question?: any;
      is_done: boolean;
      progress: { turn_index: number; total: number };
    }>('/api/interview/next', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        user_transcript: userTranscript,
        user_code: userCode,
        is_followup: isFollowup,
        elapsed_seconds: elapsedSeconds,
      }),
    }),
    
  skipToCode: (sessionId: string) =>
    apiRequest<{
      interviewer_message: string;
      followup_question?: { text: string };
      next_question?: any;
      is_done: boolean;
      progress: { turn_index: number; total: number };
    }>('/api/interview/skip-to-code', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  endInterview: (sessionId: string) =>
    apiRequest<{ ok: boolean }>('/api/interview/end', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  // Progress
  getProgressOverview: (userId: string, jobSpecId?: string) =>
    apiRequest<{
      latest_snapshot?: any;
      trend: any[];
      breakdown: any;
    }>(`/api/progress/overview?user_id=${userId}${jobSpecId ? `&job_spec_id=${jobSpecId}` : ''}`),

  // Interview History
  getInterviewHistory: (userId: string) =>
    apiRequest<{
      interviews: Array<{
        session_id: string;
        role_title: string;
        mode: string;
        created_at: string;
        ended_at: string | null;
        is_completed: boolean;
        questions_answered: number;
        average_score: number;
      }>;
    }>(`/api/interview/history/${userId}`),

  // Session
  getSession: (sessionId: string) =>
    apiRequest<{
      id: string;
      user_id: string;
      job_spec_id: string;
      mode: string;
      created_at: string;
      ended_at: string | null;
      plan_json: any;
      session_summary_json: any;
      turns: Array<{
        id: string;
        turn_index: number;
        question_id: string;
        question_snapshot: string;
        user_transcript: string;
        user_code: string | null;
        score_json: any;
        topics_json: string[];
        followup_json: any;
        created_at: string;
      }>;
    }>(`/api/interview/session/${sessionId}`),
};
