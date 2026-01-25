import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Mock the api module before importing the component
jest.mock('../../../../app/src/api/client', () => ({
  api: {
    nextInterview: jest.fn().mockResolvedValue({
      interviewer_message: 'Got it - let\'s keep going.',
      next_question: { text: 'What is your greatest strength?', type: 'open' },
      is_done: false,
      progress: { turn_index: 1, total: 5 },
    }),
    endInterview: jest.fn().mockResolvedValue({ ok: true }),
  },
}));

// Mock TTS/STT
jest.mock('../../../../app/src/voice/tts', () => ({
  speak: jest.fn(),
  speakSequential: jest.fn(),
  stopSpeaking: jest.fn(),
}));

jest.mock('../../../../app/src/voice/stt', () => ({
  startRecognition: jest.fn().mockReturnValue(jest.fn()),
  stopRecognition: jest.fn(),
  isSupported: jest.fn().mockReturnValue(true),
}));

// Mock react-router-dom's useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

import InterviewRoom from '../../../../app/src/pages/InterviewRoom';
import { api } from '../../../../app/src/api/client';

describe('InterviewRoom', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('firstQuestion', JSON.stringify({
      text: 'Tell me about yourself.',
      type: 'open',
    }));
    localStorage.setItem('totalQuestions', '5');
    localStorage.setItem('voiceOn', 'false');
  });

  const renderWithRouter = (sessionId: string = 'session-1') => {
    return render(
      <MemoryRouter initialEntries={[`/interview/${sessionId}`]}>
        <Routes>
          <Route path="/interview/:sessionId" element={<InterviewRoom />} />
          <Route path="/done/:sessionId" element={<div>Done Page</div>} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('displays the first question from localStorage', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Tell me about yourself.')).toBeInTheDocument();
    });
  });

  it('shows progress indicator', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/Question 0 of 5/)).toBeInTheDocument();
    });
  });

  it('allows typing an answer', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Tell me about yourself.')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/click mic to record or type here/i);
    fireEvent.change(textarea, { target: { value: 'I am a software engineer.' } });

    expect(textarea).toHaveValue('I am a software engineer.');
  });

  it('submits answer and loads next question', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Tell me about yourself.')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/click mic to record or type here/i);
    fireEvent.change(textarea, { target: { value: 'I am a software engineer.' } });

    fireEvent.click(screen.getByText('Submit Answer'));

    await waitFor(() => {
      expect(api.nextInterview).toHaveBeenCalledWith(
        'session-1',
        'I am a software engineer.',
        undefined
      );
    });

    await waitFor(() => {
      expect(screen.getByText('What is your greatest strength?')).toBeInTheDocument();
    });
  });

  it('ends interview when End Interview button is clicked', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Tell me about yourself.')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('End Interview'));

    await waitFor(() => {
      expect(api.endInterview).toHaveBeenCalledWith('session-1');
    });

    expect(mockNavigate).toHaveBeenCalledWith('/done/session-1');
  });

  it('redirects to home if no sessionId', async () => {
    render(
      <MemoryRouter initialEntries={['/interview/']}>
        <Routes>
          <Route path="/interview/" element={<InterviewRoom />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });
});
