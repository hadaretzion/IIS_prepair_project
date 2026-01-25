/**
 * Tests for API client
 * Note: Since the client uses import.meta.env which is tricky in Jest,
 * we test by mocking fetch and testing the exported functions.
 */

describe('api client', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.resetModules();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('calls ensureUser endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ user_id: 'user-1' }),
    });

    // Dynamically import to get fresh module with mocked fetch
    const { api } = await import('../../../../app/src/api/client');
    const result = await api.ensureUser();

    expect(result.user_id).toBe('user-1');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/users/ensure'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('throws on API error', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid request' }),
    });

    const { api } = await import('../../../../app/src/api/client');
    await expect(api.ensureUser()).rejects.toThrow('Invalid request');
  });

  it('calls ingestCV endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ cv_version_id: 'cv-1' }),
    });

    const { api } = await import('../../../../app/src/api/client');
    const result = await api.ingestCV('user-1', 'My CV text');

    expect(result.cv_version_id).toBe('cv-1');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/cv/ingest'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ user_id: 'user-1', cv_text: 'My CV text' }),
      })
    );
  });

  it('calls ingestJD endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ job_spec_id: 'job-1', jd_hash: 'hash1' }),
    });

    const { api } = await import('../../../../app/src/api/client');
    const result = await api.ingestJD('user-1', 'Job description text');

    expect(result.job_spec_id).toBe('job-1');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/jd/ingest'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('calls startInterview endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        session_id: 'session-1',
        plan_summary: {},
        first_question: { text: 'Question 1' },
        total_questions: 5,
      }),
    });

    const { api } = await import('../../../../app/src/api/client');
    const result = await api.startInterview('user-1', 'job-1', 'cv-1', 'direct');

    expect(result.session_id).toBe('session-1');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/interview/start'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('calls nextInterview endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        interviewer_message: 'Thank you',
        next_question: { text: 'Next question' },
        is_done: false,
        progress: { turn_index: 1, total: 5 },
      }),
    });

    const { api } = await import('../../../../app/src/api/client');
    const result = await api.nextInterview('session-1', 'My answer');

    expect(result.interviewer_message).toBe('Thank you');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/interview/next'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('calls endInterview endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    });

    const { api } = await import('../../../../app/src/api/client');
    const result = await api.endInterview('session-1');

    expect(result.ok).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/interview/end'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('calls getProgressOverview endpoint', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        latest_snapshot: { readiness_score: 75 },
        trend: [],
        breakdown: {},
      }),
    });

    const { api } = await import('../../../../app/src/api/client');
    const result = await api.getProgressOverview('user-1');

    expect(result.latest_snapshot.readiness_score).toBe(75);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/progress/overview?user_id=user-1'),
      expect.any(Object)
    );
  });
});
