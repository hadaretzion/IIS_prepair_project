import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '../components/Toast';
import './PreInterview.css';

function PreInterview() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('sessionId');
  const [voiceOn, setVoiceOn] = useState(true);
  const [captionsOn, setCaptionsOn] = useState(true);
  const [realismMode, setRealismMode] = useState('realistic');
  const [showQuestionProgress, setShowQuestionProgress] = useState(false);
  const [planSummary, setPlanSummary] = useState<any>(null);

  useEffect(() => {
    const stored = localStorage.getItem('planSummary');
    if (stored) {
      try {
        setPlanSummary(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to parse plan summary:', e);
      }
    }

    const storedProgress = localStorage.getItem('showQuestionProgress');
    if (storedProgress !== null) {
      setShowQuestionProgress(storedProgress === 'true');
    } else {
      setShowQuestionProgress(false);
    }
  }, []);

  const handleStart = () => {
    if (!sessionId) {
      showToast('Session not found. Please start again.', 'error');
      navigate('/');
      return;
    }
    
    // Store settings in localStorage before navigating
    localStorage.setItem('voiceOn', voiceOn.toString());
    localStorage.setItem('captionsOn', captionsOn.toString());
    localStorage.setItem('realismMode', realismMode);
    localStorage.setItem('showQuestionProgress', showQuestionProgress.toString());
    
    navigate(`/interview/${sessionId}`);
  };

  return (
    <div className="pre-interview">
      <div className="container">
        <h1>Interview Setup</h1>
        <p>Review your session plan and adjust settings</p>

        <div className="plan-summary">
          <h2>Session Plan</h2>
          {planSummary ? (
            <div>
              <p><strong>Total Questions:</strong> {planSummary.total || 'N/A'}</p>
              {planSummary.sections && planSummary.sections.length > 0 && (
                <div style={{ marginTop: '15px' }}>
                  <strong>Breakdown:</strong>
                  <ul style={{ marginTop: '10px', paddingLeft: '20px' }}>
                    {planSummary.sections.map((section: any, index: number) => (
                      <li key={index}>
                        {section.name || `Section ${index + 1}`}: {section.count || 0} questions
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!planSummary.sections && planSummary.total && (
                <p style={{ marginTop: '10px', color: '#666' }}>
                  Questions will be tailored to your CV and job description.
                </p>
              )}
            </div>
          ) : (
            <p>You'll be asked behavioral and technical questions tailored to your CV and job description.</p>
          )}
        </div>

        <div className="settings">
          <h2>Settings</h2>
          
          <div className="setting-item">
            <label>
              <input
                type="checkbox"
                checked={voiceOn}
                onChange={(e) => setVoiceOn(e.target.checked)}
              />
              Voice On/Off
            </label>
          </div>

          <div className="setting-item">
            <label>
              <input
                type="checkbox"
                checked={captionsOn}
                onChange={(e) => setCaptionsOn(e.target.checked)}
              />
              Captions On/Off
              <span className="tooltip">⚠️ Captions may reduce realism</span>
            </label>
          </div>

          <div className="setting-item">
            <label>
              <input
                type="checkbox"
                checked={showQuestionProgress}
                onChange={(e) => setShowQuestionProgress(e.target.checked)}
              />
              Show question progress (Q#/total)
            </label>
          </div>

          <div className="setting-item">
            <label>
              Realism Mode:
              <select value={realismMode} onChange={(e) => setRealismMode(e.target.value)}>
                <option value="realistic">Realistic</option>
                <option value="practice">Practice Mode</option>
              </select>
            </label>
          </div>
        </div>

        <button className="btn btn-primary" onClick={handleStart}>
          Start Interview
        </button>
      </div>
    </div>
  );
}

export default PreInterview;
