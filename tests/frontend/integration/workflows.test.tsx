import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Mock the api module
jest.mock('../../../app/src/api/client', () => ({
  api: {
    ensureUser: jest.fn().mockResolvedValue({ user_id: 'user-1' }),
    ingestCV: jest.fn().mockResolvedValue({ cv_version_id: 'cv-1' }),
    ingestJD: jest.fn().mockResolvedValue({ job_spec_id: 'job-1', jd_hash: 'hash1' }),
    analyzeCV: jest.fn().mockResolvedValue({
      match_score: 0.8,
      strengths: ['Python'],
      gaps: ['Docker'],
      suggestions: ['Add Docker'],
      role_focus: {},
    }),
    startInterview: jest.fn().mockResolvedValue({
      session_id: 'session-1',
      first_question: { text: 'Tell me about yourself', type: 'open' },
      plan_summary: {},
      total_questions: 5,
    }),
    nextInterview: jest.fn().mockResolvedValue({
      interviewer_message: 'Thank you',
      next_question: { text: 'Next question', type: 'open' },
      is_done: false,
      progress: { turn_index: 1, total: 5 },
    }),
    endInterview: jest.fn().mockResolvedValue({ ok: true }),
    saveCV: jest.fn().mockResolvedValue({ new_cv_version_id: 'cv-2' }),
    getProgressOverview: jest.fn().mockResolvedValue({
      latest_snapshot: { readiness_score: 75, cv_score: 80, interview_score: 70, practice_score: 60 },
      trend: [],
      breakdown: {},
    }),
  },
}));

// Mock TTS/STT
jest.mock('../../../app/src/voice/tts', () => ({
  speak: jest.fn(),
  speakSequential: jest.fn(),
  stopSpeaking: jest.fn(),
}));

jest.mock('../../../app/src/voice/stt', () => ({
  startRecognition: jest.fn().mockReturnValue(jest.fn()),
  stopRecognition: jest.fn(),
  isSupported: jest.fn().mockReturnValue(true),
}));

import Landing from '../../../app/src/pages/Landing';
import DocumentSetup from '../../../app/src/pages/DocumentSetup';
import CvImprove from '../../../app/src/pages/CvImprove';
import InterviewRoom from '../../../app/src/pages/InterviewRoom';
import { api } from '../../../app/src/api/client';

describe('User Workflow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('Landing to Setup flow', () => {
    it('creates user and navigates to setup', async () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/setup" element={<DocumentSetup />} />
          </Routes>
        </MemoryRouter>
      );

      fireEvent.click(screen.getByText('Start Interview Now'));

      await waitFor(() => {
        expect(api.ensureUser).toHaveBeenCalled();
      });

      expect(localStorage.getItem('userId')).toBe('user-1');
    });
  });

  describe('Document Setup flow', () => {
    beforeEach(() => {
      localStorage.setItem('userId', 'user-1');
    });

    it('processes CV and JD then navigates to CV improve', async () => {
      render(
        <MemoryRouter initialEntries={['/setup']}>
          <Routes>
            <Route path="/setup" element={<DocumentSetup />} />
            <Route path="/cv-improve" element={<CvImprove />} />
          </Routes>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByPlaceholderText(/paste your cv text/i), {
        target: { value: 'My CV' },
      });
      fireEvent.change(screen.getByPlaceholderText(/paste the job description/i), {
        target: { value: 'Job description' },
      });

      fireEvent.click(screen.getByText('Analyze & Improve CV'));

      await waitFor(() => {
        expect(api.ingestCV).toHaveBeenCalled();
        expect(api.ingestJD).toHaveBeenCalled();
        expect(api.analyzeCV).toHaveBeenCalled();
      });

      expect(localStorage.getItem('cvVersionId')).toBe('cv-1');
      expect(localStorage.getItem('jobSpecId')).toBe('job-1');
    });

    it('skips CV analysis and goes directly to interview', async () => {
      render(
        <MemoryRouter initialEntries={['/setup']}>
          <Routes>
            <Route path="/setup" element={<DocumentSetup />} />
            <Route path="/pre-interview" element={<div>Pre-Interview</div>} />
          </Routes>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByPlaceholderText(/paste your cv text/i), {
        target: { value: 'My CV' },
      });
      fireEvent.change(screen.getByPlaceholderText(/paste the job description/i), {
        target: { value: 'Job description' },
      });

      fireEvent.click(screen.getByText('Skip to Interview'));

      await waitFor(() => {
        expect(api.startInterview).toHaveBeenCalled();
      });

      expect(localStorage.getItem('firstQuestion')).toBeTruthy();
    });
  });

  describe('CV Improve flow', () => {
    beforeEach(() => {
      localStorage.setItem('userId', 'user-1');
      localStorage.setItem('cvVersionId', 'cv-1');
      localStorage.setItem('jobSpecId', 'job-1');
      localStorage.setItem('cvText', 'My CV text');
    });

    it('displays analysis and allows proceeding to interview', async () => {
      render(
        <MemoryRouter initialEntries={['/cv-improve']}>
          <Routes>
            <Route path="/cv-improve" element={<CvImprove />} />
            <Route path="/pre-interview" element={<div>Pre-Interview</div>} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/80\.0%/)).toBeInTheDocument();
      });

      expect(screen.getByText('Python')).toBeInTheDocument();
      expect(screen.getByText('Docker')).toBeInTheDocument();

      fireEvent.click(screen.getByText('Proceed to Interview'));

      await waitFor(() => {
        expect(api.startInterview).toHaveBeenCalled();
      });
    });
  });

  describe('Interview Room flow', () => {
    beforeEach(() => {
      localStorage.setItem('userId', 'user-1');
      localStorage.setItem('firstQuestion', JSON.stringify({ text: 'Tell me about yourself', type: 'open' }));
      localStorage.setItem('totalQuestions', '5');
      localStorage.setItem('voiceOn', 'false');
    });

    it('displays question and handles answer submission', async () => {
      render(
        <MemoryRouter initialEntries={['/interview/session-1']}>
          <Routes>
            <Route path="/interview/:sessionId" element={<InterviewRoom />} />
            <Route path="/done/:sessionId" element={<div>Done</div>} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Tell me about yourself')).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/click mic to record or type here/i);
      fireEvent.change(textarea, { target: { value: 'I am a developer.' } });

      fireEvent.click(screen.getByText('Submit Answer'));

      await waitFor(() => {
        expect(api.nextInterview).toHaveBeenCalledWith('session-1', 'I am a developer.', undefined);
      });
    });
  });
});
