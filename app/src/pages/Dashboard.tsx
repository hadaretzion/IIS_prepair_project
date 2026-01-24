import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { FullPageLoader } from '../components/LoadingSpinner';
import './Dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProgress = async () => {
      const userId = localStorage.getItem('userId');
      const jobSpecId = localStorage.getItem('jobSpecId');

      if (!userId) {
        showToast('Please start from the home page', 'info');
        navigate('/');
        return;
      }

      try {
        const result = await api.getProgressOverview(userId, jobSpecId || undefined);
        setOverview(result);
      } catch (error: any) {
        showToast(error.message || 'Failed to load progress', 'error');
      } finally {
        setLoading(false);
      }
    };

    loadProgress();
  }, [navigate, showToast]);

  if (loading) {
    return <FullPageLoader message="Loading your progress..." />;
  }

  const snapshot = overview?.latest_snapshot;

  return (
    <div className="dashboard">
      <div className="container">
        <div className="dashboard-header">
          <div>
            <h1>Dashboard</h1>
            <p>Your readiness progress</p>
          </div>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            Back to Home
          </button>
        </div>

        {snapshot ? (
          <>
            <div className="readiness-section">
              <div className="readiness-score">
                <span className="score-value">{snapshot.readiness_score.toFixed(0)}%</span>
                <span className="score-label">Readiness Score</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${snapshot.readiness_score}%` }}
                />
              </div>
            </div>

            <div className="breakdown">
              <h3>Score Breakdown</h3>
              <div className="breakdown-grid">
                <div className="breakdown-item">
                  <div className="item-value">{snapshot.cv_score.toFixed(0)}%</div>
                  <div className="item-label">CV Score</div>
                </div>
                <div className="breakdown-item">
                  <div className="item-value">{snapshot.interview_score.toFixed(0)}%</div>
                  <div className="item-label">Interview Score</div>
                </div>
                <div className="breakdown-item">
                  <div className="item-value">{snapshot.practice_score.toFixed(0)}%</div>
                  <div className="item-label">Practice Score</div>
                </div>
              </div>
            </div>

            {overview.trend && overview.trend.length > 1 && (
              <div className="trend">
                <h3>Progress Trend</h3>
                <p>You've completed {overview.trend.length} practice sessions</p>
              </div>
            )}

            <div className="action-section">
              <button className="btn btn-primary" onClick={() => navigate('/setup')}>
                Start New Practice
              </button>
              <button className="btn btn-secondary" onClick={() => navigate('/history')}>
                View Interview History
              </button>
            </div>
          </>
        ) : (
          <div className="no-data">
            <div className="no-data-icon">📊</div>
            <h2>No Progress Data Yet</h2>
            <p>Complete a CV analysis or interview to see your readiness score.</p>
            <button className="btn btn-primary" onClick={() => navigate('/setup')}>
              Get Started
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
