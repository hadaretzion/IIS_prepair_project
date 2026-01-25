import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the api module before importing the component
jest.mock('../../../../app/src/api/client', () => ({
  api: {
    ensureUser: jest.fn().mockResolvedValue({ user_id: 'user-1' }),
  },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

import Landing from '../../../../app/src/pages/Landing';
import { api } from '../../../../app/src/api/client';

describe('Landing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders title and buttons', () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    );

    expect(screen.getByText('PrepAIr')).toBeInTheDocument();
    expect(screen.getByText('Start Interview Now')).toBeInTheDocument();
    expect(screen.getByText('Improve CV First')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('handles Start Interview click', async () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Start Interview Now'));

    await waitFor(() => {
      expect(api.ensureUser).toHaveBeenCalled();
    });

    expect(localStorage.getItem('userId')).toBe('user-1');
    expect(mockNavigate).toHaveBeenCalledWith('/setup');
  });

  it('handles Improve CV click', async () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Improve CV First'));

    await waitFor(() => {
      expect(api.ensureUser).toHaveBeenCalled();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/setup');
  });

  it('handles Dashboard click with existing user', async () => {
    localStorage.setItem('userId', 'existing-user');

    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Dashboard'));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });

    // Should not call ensureUser since userId exists
    expect(api.ensureUser).not.toHaveBeenCalled();
  });
});
