import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the api module before importing the component
jest.mock('../../../../app/src/api/client', () => ({
  api: {
    getProgressOverview: jest.fn().mockResolvedValue({
      latest_snapshot: {
        readiness_score: 75.5,
        cv_score: 80,
        interview_score: 70,
        practice_score: 60,
      },
      trend: [],
      breakdown: {},
    }),
  },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

import Dashboard from '../../../../app/src/pages/Dashboard';
import { api } from '../../../../app/src/api/client';

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('userId', 'user-1');
  });

  it('shows loading state initially', () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays progress data after loading', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/75\.5%/)).toBeInTheDocument();
    });

    expect(api.getProgressOverview).toHaveBeenCalledWith('user-1', undefined);
  });

  it('redirects to home when no userId', async () => {
    localStorage.removeItem('userId');

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });
});
