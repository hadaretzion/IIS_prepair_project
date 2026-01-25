import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the api module before importing the component
jest.mock('../../../../app/src/api/client', () => ({
  api: {
    analyzeCV: jest.fn().mockResolvedValue({
      match_score: 0.75,
      strengths: ['Python', 'REST APIs'],
      gaps: ['Docker'],
      suggestions: ['Add Docker experience'],
      role_focus: {},
    }),
    saveCV: jest.fn().mockResolvedValue({ new_cv_version_id: 'cv-2' }),
    startInterview: jest.fn().mockResolvedValue({
      session_id: 'session-1',
      first_question: { text: 'Tell me about yourself' },
      plan_summary: {},
      total_questions: 5,
    }),
  },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

import CvImprove from '../../../../app/src/pages/CvImprove';
import { api } from '../../../../app/src/api/client';

describe('CvImprove', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('userId', 'user-1');
    localStorage.setItem('cvVersionId', 'cv-1');
    localStorage.setItem('jobSpecId', 'job-1');
    localStorage.setItem('cvText', 'My CV text');
  });

  it('shows loading state initially', () => {
    render(
      <MemoryRouter>
        <CvImprove />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays analysis results after loading', async () => {
    render(
      <MemoryRouter>
        <CvImprove />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/75\.0%/)).toBeInTheDocument();
    });

    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('REST APIs')).toBeInTheDocument();
    expect(screen.getByText('Docker')).toBeInTheDocument();
  });

  it('redirects to setup when missing required data', async () => {
    localStorage.removeItem('cvVersionId');

    render(
      <MemoryRouter>
        <CvImprove />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/setup');
    });
  });

  it('saves CV when Save CV button is clicked', async () => {
    render(
      <MemoryRouter>
        <CvImprove />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/75\.0%/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Save CV'));

    await waitFor(() => {
      expect(api.saveCV).toHaveBeenCalledWith('user-1', 'My CV text', 'cv-1');
    });
  });

  it('proceeds to interview when button is clicked', async () => {
    render(
      <MemoryRouter>
        <CvImprove />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/75\.0%/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Proceed to Interview'));

    await waitFor(() => {
      expect(api.startInterview).toHaveBeenCalled();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/pre-interview?sessionId=session-1');
  });
});
