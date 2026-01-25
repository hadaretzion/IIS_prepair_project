import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { FullPageLoader } from '../components/LoadingSpinner';
import './InterviewSettings.css';

type PersonaType = 'friendly' | 'formal' | 'challenging';

interface PersonaOption {
  id: PersonaType;
  name: string;
  description: string;
  icon: string;
  examples: string[];
}

const PERSONAS: PersonaOption[] = [
  {
    id: 'friendly',
    name: 'Friendly',
    description: 'Warm, encouraging, and supportive like a friendly mentor. Makes you feel comfortable and at ease.',
    icon: '😊',
    examples: [
      "That's a great point!",
      "Really interesting perspective - can you tell me more?",
      "I love how you approached that."
    ]
  },
  {
    id: 'formal',
    name: 'Formal',
    description: 'Professional, concise, and business-like. Polished and efficient while remaining respectful.',
    icon: '💼',
    examples: [
      "Thank you for that response.",
      "Could you elaborate on the technical implementation?",
      "Let's proceed to discuss your experience with..."
    ]
  },
  {
    id: 'challenging',
    name: 'Challenging',
    description: 'Probing, direct, and intellectually rigorous. Pushes for depth and precision.',
    icon: '🎯',
    examples: [
      "What trade-offs did you consider?",
      "Walk me through the edge cases.",
      "What if the requirements changed mid-sprint?"
    ]
  }
];

function InterviewSettings() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { showToast } = useToast();
  const [selectedPersona, setSelectedPersona] = useState<PersonaType>('friendly');
  const [questionStyle, setQuestionStyle] = useState(50); // 0 = professional, 100 = personal
  const [language, setLanguage] = useState<'english' | 'hebrew'>('english');
  const [loading, setLoading] = useState(false);

  const [loadingMessage, setLoadingMessage] = useState('');

  const getStyleLabel = (value: number) => {
    if (value <= 20) return 'Highly Technical';
    if (value <= 40) return 'Professional';
    if (value <= 60) return 'Balanced';
    if (value <= 80) return 'Conversational';
    return 'Personal';
  };

  const handleStartInterview = async () => {
    const userId = localStorage.getItem('userId');
    const jobSpecId = localStorage.getItem('jobSpecId');
    const cvVersionId = localStorage.getItem('cvVersionId');

    if (!userId || !jobSpecId) {
      showToast('Missing session data. Please start again.', 'error');
      navigate('/');
      return;
    }

    setLoading(true);
    setLoadingMessage('Preparing your interview...');

    try {
      const sessionResult = await api.startInterview(
        userId,
        jobSpecId,
        cvVersionId || null,
        'direct',
        { 
          num_open: 4, 
          num_code: 2, 
          duration_minutes: 12,
          persona: selectedPersona,
          question_style: questionStyle,
          language: language
        }
      );

      if (sessionResult.first_question) {
        localStorage.setItem('firstQuestion', JSON.stringify(sessionResult.first_question));
      }
      if (sessionResult.plan_summary) {
        localStorage.setItem('planSummary', JSON.stringify(sessionResult.plan_summary));
      }
      if (sessionResult.total_questions) {
        localStorage.setItem('totalQuestions', sessionResult.total_questions.toString());
      }
      
      localStorage.setItem('interviewLanguage', language);

      showToast('Interview ready! Good luck!', 'success');
      navigate(`/pre-interview?sessionId=${sessionResult.session_id}`);
    } catch (error: any) {
      showToast(error.message || 'Failed to start interview. Please try again.', 'error');
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const handleBack = () => {
    navigate('/setup');
  };

  return (
    <div className="interview-settings">
      {loading && <FullPageLoader message={loadingMessage} />}
      <div className="container">
        <button className="back-button" onClick={handleBack}>
          ← Back
        </button>
        
        <h1>Interview Settings</h1>
        <p className="subtitle">Choose your interviewer's personality</p>

        <div className="persona-grid">
          {PERSONAS.map((persona) => (
            <div
              key={persona.id}
              className={`persona-card ${selectedPersona === persona.id ? 'selected' : ''}`}
              onClick={() => setSelectedPersona(persona.id)}
            >
              <div className="persona-icon">{persona.icon}</div>
              <h2>{persona.name}</h2>
              <p className="persona-description">{persona.description}</p>
              <div className="persona-examples">
                <span className="examples-label">Sample phrases:</span>
                <ul>
                  {persona.examples.map((example, i) => (
                    <li key={i}>"{example}"</li>
                  ))}
                </ul>
              </div>
              {selectedPersona === persona.id && (
                <div className="selected-badge">✓ Selected</div>
              )}
            </div>
          ))}
        </div>

        {/* Language Selection */}
        <div className="style-section">
          <h2>🗣️ Interview Language</h2>
          <div className="language-selector">
            <button 
              className={`selection-card ${language === 'english' ? 'selected' : ''}`}
              onClick={() => setLanguage('english')}
            >
              <div className="selection-header">
                <span className="selection-icon">🇺🇸</span>
                <h3>English</h3>
              </div>
              <p>Standard professional English interview</p>
              {language === 'english' && <div className="selected-badge">✓ Selected</div>}
            </button>

            <button 
              className={`selection-card ${language === 'hebrew' ? 'selected' : ''}`}
              onClick={() => setLanguage('hebrew')}
            >
              <div className="selection-header">
                <span className="selection-icon">🇮🇱</span>
                <h3>Hebrew</h3>
              </div>
              <p>Interview conducted in Hebrew (Ivrit)</p>
              {language === 'hebrew' && <div className="selected-badge">✓ Selected</div>}
            </button>
          </div>
        </div>

        {/* Question Style Slider */}
        <div className="style-section">
          <h2>Question Style</h2>
          <p className="section-description">
            Adjust the balance between technical/professional questions and personal/behavioral ones
          </p>
          
          <div className="slider-container">
            <div className="slider-labels">
              <span>🔧 Technical</span>
              <span className="style-value">{getStyleLabel(questionStyle)}</span>
              <span>💬 Personal</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={questionStyle}
              onChange={(e) => setQuestionStyle(Number(e.target.value))}
              className="style-slider"
            />
            <div className="slider-hints">
              <span>System design, algorithms, code</span>
              <span>Teamwork, motivation, goals</span>
            </div>
          </div>
        </div>

        <div className="action-buttons">
          <button 
            className="btn btn-primary btn-large"
            onClick={handleStartInterview}
            disabled={loading}
          >
            Start Interview →
          </button>
        </div>
      </div>
    </div>
  );
}

export default InterviewSettings;
