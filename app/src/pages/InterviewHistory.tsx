import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { FullPageLoader } from '../components/LoadingSpinner';
import './InterviewHistory.css';

interface InterviewRecord {
  session_id: string;
  role_title: string;
  mode: string;
  created_at: string;
  ended_at: string | null;
  is_completed: boolean;
  questions_answered: number;
  average_score: number;
}

function InterviewHistory() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [interviews, setInterviews] = useState<InterviewRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      const userId = localStorage.getItem('userId');

      if (!userId) {
        showToast('Please start from the home page', 'info');
        navigate('/');
        return;
      }

      try {
        const result = await api.getInterviewHistory(userId);
        setInterviews(result.interviews);
      } catch (error: any) {
        showToast(error.message || 'Failed to load interview history', 'error');
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [navigate, showToast]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getScoreClass = (score: number) => {
    if (score >= 70) return 'score-high';
    if (score >= 50) return 'score-medium';
    return 'score-low';
  };

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case 'direct': return 'Direct Interview';
      case 'after_cv': return 'After CV Review';
      default: return mode;
    }
  };

  if (loading) {
    return <FullPageLoader message="Loading interview history..." />;
  }

  return (
    <div className="interview-history">
      <div className="container">
        <div className="history-header">
          <div>
            <h1>Interview History</h1>
            <p>Review your past interview sessions</p>
          </div>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            Back to Home
          </button>
        </div>

        {interviews.length === 0 ? (
          <div className="no-interviews">
            <div className="no-interviews-icon">📋</div>
            <h2>No Interviews Yet</h2>
            <p>You haven't completed any interviews. Start practicing to see your history here!</p>
            <button className="btn btn-primary" onClick={() => navigate('/setup')}>
              Start Your First Interview
            </button>
          </div>
        ) : (
          <div className="interviews-list">
            {interviews.map((interview) => (
              <div 
                key={interview.session_id} 
                className={`interview-card ${interview.is_completed ? 'completed' : 'incomplete'}`}
                onClick={() => navigate(`/feedback/${interview.session_id}`)}
              >
                <div className="interview-main">
                  <div className="interview-info">
                    <h3>{interview.role_title}</h3>
                    <div className="interview-meta">
                      <span className="meta-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                          <line x1="16" y1="2" x2="16" y2="6"/>
                          <line x1="8" y1="2" x2="8" y2="6"/>
                          <line x1="3" y1="10" x2="21" y2="10"/>
                        </svg>
                        {formatDate(interview.created_at)}
                      </span>
                      <span className="meta-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                        {interview.questions_answered} questions
                      </span>
                      <span className="meta-item mode-badge">
                        {getModeLabel(interview.mode)}
                      </span>
                    </div>
                  </div>
                  <div className="interview-score">
                    <div className={`score-circle ${getScoreClass(interview.average_score)}`}>
                      <span className="score-value">{interview.average_score.toFixed(0)}%</span>
                    </div>
                    <span className="score-label">Avg Score</span>
                  </div>
                </div>
                <div className="interview-status">
                  {interview.is_completed ? (
                    <span className="status-badge completed">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                      </svg>
                      Completed
                    </span>
                  ) : (
                    <span className="status-badge incomplete">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"/>
                        <polyline points="12 6 12 12 16 14"/>
                      </svg>
                      In Progress
                    </span>
                  )}
                  <span className="view-details">View Details →</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {interviews.length > 0 && (
          <div className="history-actions">
            <button className="btn btn-primary" onClick={() => navigate('/setup')}>
              Start New Interview
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
              View Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default InterviewHistory;
