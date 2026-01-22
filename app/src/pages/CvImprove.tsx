import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { FullPageLoader } from '../components/LoadingSpinner';
import './CvImprove.css';

function CvImprove() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [cvText, setCvText] = useState(localStorage.getItem('cvText') || '');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [proceeding, setProceeding] = useState(false);

  useEffect(() => {
    const loadAnalysis = async () => {
      const userId = localStorage.getItem('userId');
      const cvVersionId = localStorage.getItem('cvVersionId');
      const jobSpecId = localStorage.getItem('jobSpecId');

      if (!userId || !cvVersionId || !jobSpecId) {
        showToast('Please upload your documents first', 'warning');
        navigate('/setup');
        return;
      }

      try {
        const result = await api.analyzeCV(userId, cvVersionId, jobSpecId);
        setAnalysis(result);
      } catch (error: any) {
        showToast(error.message || 'Failed to load analysis', 'error');
      } finally {
        setLoading(false);
      }
    };

    loadAnalysis();
  }, [navigate, showToast]);

  const handleSaveCV = async () => {
    const userId = localStorage.getItem('userId');
    const parentCvVersionId = localStorage.getItem('cvVersionId');

    if (!userId) return;

    setSaving(true);
    try {
      const result = await api.saveCV(userId, cvText, parentCvVersionId || undefined);
      localStorage.setItem('cvVersionId', result.new_cv_version_id);
      localStorage.setItem('cvText', cvText);
      showToast('CV saved successfully!', 'success');
    } catch (error: any) {
      showToast(error.message || 'Failed to save CV', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleProceedToInterview = async () => {
    const userId = localStorage.getItem('userId');
    const jobSpecId = localStorage.getItem('jobSpecId');
    const cvVersionId = localStorage.getItem('cvVersionId');

    if (!userId || !jobSpecId || !cvVersionId) return;

    setProceeding(true);
    try {
      const result = await api.startInterview(
        userId,
        jobSpecId,
        cvVersionId,
        'after_cv',
        { num_open: 4, num_code: 2, duration_minutes: 12 }
      );

      if (result.first_question) {
        localStorage.setItem('firstQuestion', JSON.stringify(result.first_question));
      }
      if (result.plan_summary) {
        localStorage.setItem('planSummary', JSON.stringify(result.plan_summary));
      }
      if (result.total_questions) {
        localStorage.setItem('totalQuestions', result.total_questions.toString());
      }

      showToast('Interview ready!', 'success');
      navigate(`/pre-interview?sessionId=${result.session_id}`);
    } catch (error: any) {
      showToast(error.message || 'Failed to start interview', 'error');
    } finally {
      setProceeding(false);
    }
  };

  if (loading) {
    return <FullPageLoader message="Analyzing your CV..." />;
  }

  if (!analysis) {
    return (
      <div className="cv-improve">
        <div className="container error-container">
          <h2>Analysis not available</h2>
          <p>Please try uploading your documents again.</p>
          <button className="btn btn-primary" onClick={() => navigate('/setup')}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const matchPercent = (analysis.match_score * 100).toFixed(0);

  return (
    <div className="cv-improve">
      {proceeding && <FullPageLoader message="Preparing interview..." />}
      <div className="container">
        <h1>CV Analysis & Improvement</h1>

        <div className="score-section">
          <div className="score-circle">
            <span className="score-value">{matchPercent}%</span>
            <span className="score-label">Match Score</span>
          </div>
        </div>

        <div className="analysis-grid">
          <div className="analysis-card strengths">
            <h3>Strengths</h3>
            <ul>
              {analysis.strengths?.map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>

          <div className="analysis-card gaps">
            <h3>Gaps to Address</h3>
            <ul>
              {analysis.gaps?.map((g: string, i: number) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>

          <div className="analysis-card suggestions full-width">
            <h3>Suggestions</h3>
            <ul>
              {analysis.suggestions?.map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="cv-editor">
          <label>Edit Your CV</label>
          <textarea
            value={cvText}
            onChange={(e) => setCvText(e.target.value)}
            rows={16}
            placeholder="Your CV text..."
          />
        </div>

        <div className="action-buttons">
          <button 
            className="btn btn-secondary" 
            onClick={handleSaveCV}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save CV'}
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleProceedToInterview}
            disabled={proceeding}
          >
            {proceeding ? 'Starting...' : 'Proceed to Interview'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CvImprove;
