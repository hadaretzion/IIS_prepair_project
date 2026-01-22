import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { LoadingSpinner } from '../components/LoadingSpinner';
import './Landing.css';

function Landing() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleStartInterview = async () => {
    setLoading(true);
    try {
      const { user_id } = await api.ensureUser();
      localStorage.setItem('userId', user_id);
      navigate('/setup');
    } catch (error: any) {
      showToast(error.message || 'Failed to start. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleImproveCV = async () => {
    setLoading(true);
    try {
      const { user_id } = await api.ensureUser();
      localStorage.setItem('userId', user_id);
      navigate('/cv-improve');
    } catch (error: any) {
      showToast(error.message || 'Failed to start. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDashboard = async () => {
    setLoading(true);
    try {
      const userId = localStorage.getItem('userId');
      if (!userId) {
        const { user_id } = await api.ensureUser();
        localStorage.setItem('userId', user_id);
      }
      navigate('/dashboard');
    } catch (error: any) {
      showToast(error.message || 'Failed to load dashboard. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing">
      <div className="landing-container">
        <div className="landing-logo">
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="45" stroke="url(#gradient)" strokeWidth="2" fill="none" opacity="0.3"/>
            <circle cx="50" cy="50" r="30" stroke="url(#gradient)" strokeWidth="3" fill="none"/>
            <path d="M35 50L45 60L65 40" stroke="url(#gradient)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#6366f1"/>
                <stop offset="100%" stopColor="#a855f7"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        
        <h1>PrepAIr</h1>
        <p className="subtitle">AI-Powered Interview Preparation</p>
        
        <div className="action-buttons">
          <button 
            className="btn btn-primary" 
            onClick={handleStartInterview}
            disabled={loading}
          >
            {loading ? <LoadingSpinner size="small" /> : 'Start Interview Practice'}
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={handleImproveCV}
            disabled={loading}
          >
            {loading ? <LoadingSpinner size="small" /> : 'Optimize Your CV'}
          </button>
          <button 
            className="btn btn-tertiary" 
            onClick={handleDashboard}
            disabled={loading}
          >
            View Dashboard
          </button>
        </div>

        <div className="features-preview">
          <div className="feature-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>AI-Powered Feedback</span>
          </div>
          <div className="feature-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            <span>Real-time Analysis</span>
          </div>
          <div className="feature-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
            </svg>
            <span>Track Progress</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
