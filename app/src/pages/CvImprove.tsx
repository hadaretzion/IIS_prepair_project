import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import './CvImprove.css';

function CvImprove() {
  const navigate = useNavigate();
  const [cvText, setCvText] = useState(localStorage.getItem('cvText') || '');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAnalysis = async () => {
      const userId = localStorage.getItem('userId');
      const cvVersionId = localStorage.getItem('cvVersionId');
      const jobSpecId = localStorage.getItem('jobSpecId');

      if (!userId || !cvVersionId || !jobSpecId) {
        navigate('/setup');
        return;
      }

      try {
        const result = await api.analyzeCV(userId, cvVersionId, jobSpecId);
        setAnalysis(result);
      } catch (error: any) {
        alert(`Error loading analysis: ${error.message}`);
      } finally {
        setLoading(false);
      }
    };

    loadAnalysis();
  }, [navigate]);

  const handleSaveCV = async () => {
    const userId = localStorage.getItem('userId');
    const parentCvVersionId = localStorage.getItem('cvVersionId');

    if (!userId) return;

    try {
      const result = await api.saveCV(userId, cvText, parentCvVersionId || undefined);
      localStorage.setItem('cvVersionId', result.new_cv_version_id);
      localStorage.setItem('cvText', cvText);
      alert('CV saved successfully!');
    } catch (error: any) {
      alert(`Error saving CV: ${error.message}`);
    }
  };

  const handleProceedToInterview = async () => {
    const userId = localStorage.getItem('userId');
    const jobSpecId = localStorage.getItem('jobSpecId');
    const cvVersionId = localStorage.getItem('cvVersionId');

    if (!userId || !jobSpecId || !cvVersionId) return;

    try {
      const result = await api.startInterview(
        userId,
        jobSpecId,
        cvVersionId,
        'after_cv',
        { num_open: 4, num_code: 2, duration_minutes: 12 }
      );

      // Store first question and plan summary for InterviewRoom
      if (result.first_question) {
        localStorage.setItem('firstQuestion', JSON.stringify(result.first_question));
      }
      if (result.plan_summary) {
        localStorage.setItem('planSummary', JSON.stringify(result.plan_summary));
      }
      if (result.total_questions) {
        localStorage.setItem('totalQuestions', result.total_questions.toString());
      }

      navigate(`/pre-interview?sessionId=${result.session_id}`);
    } catch (error: any) {
      alert(`Error starting interview: ${error.message}`);
    }
  };

  if (loading) {
    return <div className="loading">Loading analysis...</div>;
  }

  if (!analysis) {
    return <div className="error">Analysis not available</div>;
  }

  return (
    <div className="cv-improve">
      <div className="container">
        <h1>CV Analysis & Improvement</h1>

        <div className="score-section">
          <h2>Match Score: {(analysis.match_score * 100).toFixed(1)}%</h2>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${analysis.match_score * 100}%` }}
            />
          </div>
        </div>

        <div className="analysis-grid">
          <div className="analysis-card">
            <h3>Strengths</h3>
            <ul>
              {analysis.strengths?.map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>

          <div className="analysis-card">
            <h3>Gaps</h3>
            <ul>
              {analysis.gaps?.map((g: string, i: number) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>

          <div className="analysis-card full-width">
            <h3>Suggestions</h3>
            <ul>
              {analysis.suggestions?.map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="cv-editor">
          <label>Edit CV Text</label>
          <textarea
            value={cvText}
            onChange={(e) => setCvText(e.target.value)}
            rows={20}
          />
        </div>

        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={handleSaveCV}>
            Save CV
          </button>
          <button className="btn btn-primary" onClick={handleProceedToInterview}>
            Proceed to Interview
          </button>
        </div>
      </div>
    </div>
  );
}

export default CvImprove;
