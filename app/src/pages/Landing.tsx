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
      navigate('/setup');
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
        <h1>PrepAIr</h1>
        <p className="subtitle">AI-Powered Career Preparation Platform</p>
        
        <div className="action-buttons">
          <button 
            className="btn btn-primary" 
            onClick={handleStartInterview}
            disabled={loading}
          >
            {loading ? <LoadingSpinner size="small" /> : 'Start Interview Now'}
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={handleImproveCV}
            disabled={loading}
          >
            {loading ? <LoadingSpinner size="small" /> : 'Improve CV First'}
          </button>
          <button 
            className="btn btn-tertiary" 
            onClick={handleDashboard}
            disabled={loading}
          >
            Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

export default Landing;
