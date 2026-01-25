import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the api module before importing the component
jest.mock('../../../../app/src/api/client', () => ({
  api: {
    ingestCV: jest.fn().mockResolvedValue({ cv_version_id: 'cv-1' }),
    ingestJD: jest.fn().mockResolvedValue({ job_spec_id: 'job-1', jd_hash: 'hash1' }),
    analyzeCV: jest.fn().mockResolvedValue({
      match_score: 0.8,
      strengths: ['Python'],
      gaps: [],
      suggestions: [],
    }),
    startInterview: jest.fn().mockResolvedValue({
      session_id: 'session-1',
      first_question: { text: 'Tell me about yourself' },
      plan_summary: {},
      total_questions: 5,
    }),
    ingestCVPDF: jest.fn().mockResolvedValue({ cv_version_id: 'cv-pdf-1' }),
    ingestJDPDF: jest.fn().mockResolvedValue({ job_spec_id: 'job-pdf-1', jd_hash: 'hash2' }),
  },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

import DocumentSetup from '../../../../app/src/pages/DocumentSetup';
import { api } from '../../../../app/src/api/client';

describe('DocumentSetup', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('userId', 'user-1');
  });

  it('renders CV and JD input areas', () => {
    render(
      <MemoryRouter>
        <DocumentSetup />
      </MemoryRouter>
    );

    expect(screen.getByText('Document Setup')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste your cv text/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste the job description/i)).toBeInTheDocument();
  });

  it('disables buttons when inputs are empty', () => {
    render(
      <MemoryRouter>
        <DocumentSetup />
      </MemoryRouter>
    );

    const analyzeButton = screen.getByText('Analyze & Improve CV');
    const skipButton = screen.getByText('Skip to Interview');

    expect(analyzeButton).toBeDisabled();
    expect(skipButton).toBeDisabled();
  });

  it('enables buttons when both inputs have text', () => {
    render(
      <MemoryRouter>
        <DocumentSetup />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/paste your cv text/i), {
      target: { value: 'My CV text' },
    });
    fireEvent.change(screen.getByPlaceholderText(/paste the job description/i), {
      target: { value: 'Job description' },
    });

    const analyzeButton = screen.getByText('Analyze & Improve CV');
    expect(analyzeButton).not.toBeDisabled();
  });

  it('calls API and navigates on Analyze & Improve', async () => {
    render(
      <MemoryRouter>
        <DocumentSetup />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/paste your cv text/i), {
      target: { value: 'My CV text' },
    });
    fireEvent.change(screen.getByPlaceholderText(/paste the job description/i), {
      target: { value: 'Job description' },
    });

    fireEvent.click(screen.getByText('Analyze & Improve CV'));

    await waitFor(() => {
      expect(api.ingestCV).toHaveBeenCalledWith('user-1', 'My CV text');
      expect(api.ingestJD).toHaveBeenCalledWith('user-1', 'Job description');
      expect(api.analyzeCV).toHaveBeenCalled();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/cv-improve');
  });

  it('calls API and navigates on Skip to Interview', async () => {
    render(
      <MemoryRouter>
        <DocumentSetup />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText(/paste your cv text/i), {
      target: { value: 'My CV text' },
    });
    fireEvent.change(screen.getByPlaceholderText(/paste the job description/i), {
      target: { value: 'Job description' },
    });

    fireEvent.click(screen.getByText('Skip to Interview'));

    await waitFor(() => {
      expect(api.ingestCV).toHaveBeenCalled();
      expect(api.ingestJD).toHaveBeenCalled();
      expect(api.startInterview).toHaveBeenCalled();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/pre-interview?sessionId=session-1');
  });
});
