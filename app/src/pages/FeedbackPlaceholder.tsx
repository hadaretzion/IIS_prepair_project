import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import './FeedbackPlaceholder.css';

function FeedbackPlaceholder() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [sessionData, setSessionData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError('Session ID missing');
      setLoading(false);
      return;
    }

    const loadSessionData = async () => {
      try {
        const data = await api.getSession(sessionId);
        setSessionData(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load session data');
      } finally {
        setLoading(false);
      }
    };

    loadSessionData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="feedback-placeholder">
        <div className="container">
          <h1>Feedback</h1>
          <p>Loading feedback...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="feedback-placeholder">
        <div className="container">
          <h1>Feedback</h1>
          <p style={{ color: 'red' }}>Error: {error}</p>
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!sessionData || !sessionData.turns || sessionData.turns.length === 0) {
    return (
      <div className="feedback-placeholder">
        <div className="container">
          <h1>Feedback</h1>
          <p>No interview data available for this session.</p>
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const turns = Array.isArray(sessionData.turns) ? sessionData.turns : [];
  const totalTurns = turns.length;
  
  // Calculate overall scores
  let totalScore = 0;
  let scoreCount = 0;
  const weakTopics = new Set<string>();
  const strongTopics = new Set<string>();

  turns.forEach((turn: any) => {
    const score = turn?.score_json;
    if (score && typeof score.overall === 'number') {
      totalScore += score.overall;
      scoreCount++;
      
      const topics = Array.isArray(turn?.topics_json) ? turn.topics_json : [];
      if (score.overall < 0.6) {
        topics.forEach((topic: string) => weakTopics.add(topic));
      } else if (score.overall >= 0.8) {
        topics.forEach((topic: string) => strongTopics.add(topic));
      }
    }
  });

  const averageScore = scoreCount > 0 ? (totalScore / scoreCount) * 100 : 0;

  // Generate recommendations
  const recommendations: string[] = [];
  if (weakTopics.size > 0) {
    recommendations.push(`Focus on improving: ${Array.from(weakTopics).slice(0, 5).join(', ')}`);
  }
  if (averageScore < 70) {
    recommendations.push('Consider practicing more interview questions to improve your responses');
  }
  if (turns.some((t: any) => typeof t?.question_id === 'string' && t.question_id.startsWith('code:') && !t.user_code)) {
    recommendations.push('Try to provide code solutions for technical questions');
  }

  return (
    <div className="feedback-placeholder">
      <div className="container">
        <h1>Interview Feedback</h1>
        
        <div style={{ marginBottom: '30px', color: '#e8ecf5' }}>
          <h2>Overall Performance</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div>
              <div style={{ fontSize: '48px', fontWeight: 'bold', color: averageScore >= 80 ? '#28a745' : averageScore >= 60 ? '#ffc107' : '#dc3545' }}>
                {averageScore.toFixed(1)}%
              </div>
              <div style={{ fontSize: '14px', color: '#cbd5e1' }}>Average Score</div>
            </div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{totalTurns}</div>
              <div style={{ fontSize: '14px', color: '#cbd5e1' }}>Questions Answered</div>
            </div>
          </div>
        </div>

        <div style={{ marginBottom: '30px', color: '#e8ecf5' }}>
          <h2>Per-Question Breakdown</h2>
          {turns.map((turn: any, index: number) => {
            const score = turn.score_json || {};
            const overall = (score.overall || 0) * 100;
            const rubric = score.rubric || {};
            const topics = turn.topics_json || [];

            return (
              <div key={turn.id} style={{ 
                border: '1px solid rgba(255,255,255,0.08)', 
                borderRadius: '12px', 
                padding: '20px', 
                marginBottom: '20px',
                backgroundColor: 'rgba(255,255,255,0.05)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '15px' }}>
                  <h3 style={{ margin: 0 }}>Question {index + 1}</h3>
                  <div style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold',
                    color: overall >= 80 ? '#28a745' : overall >= 60 ? '#ffc107' : '#dc3545'
                  }}>
                    {overall.toFixed(1)}%
                  </div>
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <strong>Question:</strong>
                  <p style={{ marginTop: '5px', color: '#e8ecf5' }}>{turn.question_snapshot}</p>
                </div>

                <div style={{ marginBottom: '15px' }}>
                  <strong>Your Answer:</strong>
                  <p style={{ marginTop: '5px', color: '#d9deeb', fontStyle: 'italic' }}>
                    {turn.user_transcript || '(No transcript provided)'}
                  </p>
                  {turn.user_code && (
                    <div style={{ marginTop: '10px' }}>
                      <strong>Code:</strong>
                      <pre style={{ 
                        backgroundColor: 'rgba(0,0,0,0.5)', 
                        padding: '10px', 
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '200px'
                      }}>
                        {turn.user_code}
                      </pre>
                    </div>
                  )}
                </div>

                {Object.keys(rubric).length > 0 && (
                  <div style={{ marginBottom: '15px' }}>
                    <strong>Score Breakdown:</strong>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginTop: '10px' }}>
                      {Object.entries(rubric).map(([key, value]: [string, any]) => (
                        <div key={key} style={{ 
                          padding: '10px', 
                          backgroundColor: 'rgba(255,255,255,0.05)', 
                          borderRadius: '8px',
                          border: '1px solid rgba(255,255,255,0.08)'
                        }}>
                          <div style={{ fontSize: '12px', color: '#cbd5e1', textTransform: 'capitalize' }}>{key}</div>
                          <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                            {((value || 0) * 100).toFixed(0)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {topics.length > 0 && (
                  <div style={{ marginBottom: '15px' }}>
                    <strong>Topics:</strong>
                    <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {topics.map((topic: string, i: number) => (
                        <span key={i} style={{
                          display: 'inline-block',
                          padding: '6px 10px',
                          backgroundColor: 'rgba(99, 102, 241, 0.15)',
                          color: '#cdd5ff',
                          borderRadius: '999px',
                          fontSize: '12px'
                        }}>
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {score.notes && score.notes.length > 0 && (
                  <div>
                    <strong>Notes:</strong>
                      <ul style={{ marginTop: '5px', paddingLeft: '20px', color: '#d9deeb' }}>
                      {score.notes.map((note: string, i: number) => (
                        <li key={i} style={{ color: '#cbd5e1' }}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {turn.followup_json && (
                  <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#fff3cd', borderRadius: '4px' }}>
                    <strong>Follow-up:</strong> {turn.followup_json.text || JSON.stringify(turn.followup_json)}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {recommendations.length > 0 && (
          <div style={{ marginBottom: '30px' }}>
            <h2>Recommendations</h2>
            <ul style={{ paddingLeft: '20px' }}>
              {recommendations.map((rec, i) => (
                <li key={i} style={{ marginBottom: '10px', color: '#333' }}>{rec}</li>
              ))}
            </ul>
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
            View Dashboard
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            Start New Interview
          </button>
        </div>
      </div>
    </div>
  );
}

export default FeedbackPlaceholder;
