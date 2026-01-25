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
        // prefer backend cv_text (handles PDF uploads); fall back to local copy
        if (result.cv_text) {
          setCvText(result.cv_text);
          localStorage.setItem('cvText', result.cv_text);
        }
      } catch (error: any) {
        showToast(error.message || 'Failed to load analysis', 'error');
      } finally {
        setLoading(false);
      }
    };

    loadAnalysis();
  }, [navigate, showToast]);

  const handleProceedToInterview = () => {
    navigate('/interview/settings');
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
  const estimatedScore = Math.min(100, parseInt(matchPercent) + 14);

  const renderCvPreview = () => {
    const sectionKeywords = [
      'Summary',
      'Objective',
      'Profile',
      'Projects',
      'Experience',
      'Professional Experience',
      'Work Experience',
      'Technical Skills',
      'Skills',
      'Education',
      'Languages',
      'Certifications',
      'Publications'
    ];

    const normalizeCvText = (raw: string) => {
      let text = raw.replace(/\r\n/g, '\n');

      // If user pasted a single long line, add breaks before common section keywords
      if (!text.includes('\n')) {
        text = text.replace(/\s+/g, ' ').trim();
        sectionKeywords.forEach((k) => {
          const re = new RegExp(`\\s*(${k})\\b`, 'gi');
          text = text.replace(re, `\n\n${k}`);
        });
      }
      return text.trim();
    };

    const normalized = normalizeCvText(cvText);
    if (!normalized) {
      return <p className="cv-empty">No CV content available</p>;
    }

    const lines = normalized.split(/\n+/);
    const blocks: Array<{ type: 'list' | 'text'; items: string[] }> = [];
    let current: { type: 'list' | 'text'; items: string[] } | null = null;

    const flush = () => {
      if (current && current.items.length) {
        blocks.push(current);
      }
      current = null;
    };

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        flush();
        continue;
      }

      const isBullet = /^[-*•]/.test(line);
      if (isBullet) {
        if (!current || current.type !== 'list') {
          flush();
          current = { type: 'list', items: [] };
        }
        current.items.push(line.replace(/^[-*•]\s*/, ''));
      } else {
        if (!current || current.type !== 'text') {
          flush();
          current = { type: 'text', items: [] };
        }
        current.items.push(line);
      }
    }
    flush();

    return blocks.map((block, idx) => {
      if (block.type === 'list') {
        return (
          <ul className="cv-list" key={`list-${idx}`}>
            {block.items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        );
      }
      return block.items.map((p, i) => (
        <p className="cv-line" key={`p-${idx}-${i}`}>
          {p}
        </p>
      ));
    });
  };

  return (
    <div className="cv-improve">
      <div className="container">
        <h1>CV Optimization: Aligning with Job Requirements</h1>

        <div className="score-comparison">
          <div className="score-badge current">
            <span>Match Score: {matchPercent}%</span>
            <span className="score-tag">(Current)</span>
          </div>
          <div className="score-badge estimated">
            <span>{estimatedScore}%</span>
            <span className="score-tag">(Estimated after edits)</span>
          </div>
        </div>

        <div className="cv-layout">
          {/* Left side: CV Preview */}
          <div className="cv-preview-panel">
            <div className="panel-header">Your CV (Preview)</div>
            <div className="cv-content">
              <div className="cv-paper">
                <div className="cv-body">{renderCvPreview()}</div>
              </div>
            </div>
          </div>

          {/* Right side: AI Suggestions */}
          <div className="suggestions-panel">
            <div className="panel-header">AI Suggestions</div>
            
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

            <div className="analysis-card suggestions">
              <h3>Improvement Suggestions</h3>
              <ul>
                {analysis.suggestions?.map((s: string, i: number) => (
                  <li key={i}>
                    <span className="suggestion-text">{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="action-buttons">
          <button 
            className="btn btn-primary" 
            onClick={handleProceedToInterview}
          >
            Continue to Interview Setup
          </button>
        </div>
      </div>
    </div>
  );
}

export default CvImprove;
