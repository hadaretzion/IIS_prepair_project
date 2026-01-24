import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { speak, speakSequential, stopSpeaking, onSpeakingChange, isSupported as ttsSupported } from '../voice/tts';
import { startRecognition, stopRecognition, isSupported as sttSupported, requestMicPermission } from '../voice/stt';
import { useToast } from '../components/Toast';
import './InterviewRoom.css';

interface Message {
  id: string;
  role: 'interviewer' | 'user';
  content: string;
  timestamp: Date;
}

function InterviewRoom() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [typedInput, setTypedInput] = useState('');
  const [userCode, setUserCode] = useState('');
  const [showWhiteboard, setShowWhiteboard] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [progress, setProgress] = useState({ turn_index: 0, total: 0 });
  const [timer, setTimer] = useState(0);
  const [voiceOn, setVoiceOn] = useState(true);
  const [currentQuestion, setCurrentQuestion] = useState<any>(null);
  const [sttAvailable] = useState(sttSupported());
  const [micPermission, setMicPermission] = useState<'granted' | 'denied' | 'prompt' | 'unknown'>('unknown');
  
  const stopRecognitionRef = useRef<(() => void) | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const pendingTimeoutsRef = useRef<NodeJS.Timeout[]>([]);
  const isMountedRef = useRef(true);
  const hasInitializedRef = useRef(false);

  const clearPendingTimeouts = useCallback(() => {
    pendingTimeoutsRef.current.forEach(t => clearTimeout(t));
    pendingTimeoutsRef.current = [];
  }, []);

  const safeSetTimeout = useCallback((fn: () => void, delay: number) => {
    const id = setTimeout(() => {
      if (isMountedRef.current) {
        fn();
      }
    }, delay);
    pendingTimeoutsRef.current.push(id);
    return id;
  }, []);

  const addMessage = useCallback((role: 'interviewer' | 'user', content: string) => {
    if (!isMountedRef.current) return;
    const newMessage: Message = {
      id: `${Date.now()}-${Math.random()}`,
      role,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    isMountedRef.current = true;
    
    if (!sessionId) {
      navigate('/');
      return;
    }

    const storedVoiceOn = localStorage.getItem('voiceOn');
    if (storedVoiceOn !== null) {
      setVoiceOn(storedVoiceOn === 'true');
    }

    timerIntervalRef.current = setInterval(() => {
      setTimer((prev) => prev + 1);
    }, 1000);

    const unsubscribeSpeaking = onSpeakingChange((speaking) => {
      if (isMountedRef.current) {
        setIsSpeaking(speaking);
      }
    });

    loadInitialQuestion();

    return () => {
      isMountedRef.current = false;
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      stopSpeaking();
      if (stopRecognitionRef.current) {
        stopRecognitionRef.current();
      }
      clearPendingTimeouts();
      unsubscribeSpeaking();
    };
  }, [sessionId, navigate, clearPendingTimeouts]);

  useEffect(() => {
    if (!sttAvailable) {
      return;
    }
    const permissions = (navigator as any).permissions;
    if (!permissions?.query) {
      return;
    }

    permissions
      .query({ name: 'microphone' })
      .then((status: any) => {
        if (!isMountedRef.current) {
          return;
        }
        setMicPermission(status.state);
        status.onchange = () => {
          if (isMountedRef.current) {
            setMicPermission(status.state);
          }
        };
      })
      .catch(() => {
        if (isMountedRef.current) {
          setMicPermission('unknown');
        }
      });
  }, [sttAvailable]);

  const loadInitialQuestion = async () => {
    if (hasInitializedRef.current) {
      return;
    }
    hasInitializedRef.current = true;
    const storedFirstQuestion = localStorage.getItem('firstQuestion');
    const storedTotalQuestions = localStorage.getItem('totalQuestions');

    if (storedFirstQuestion) {
      try {
        const firstQuestion = JSON.parse(storedFirstQuestion);
        const total = storedTotalQuestions ? parseInt(storedTotalQuestions, 10) : 6;
        startInterviewWithQuestion(firstQuestion, total);
        localStorage.removeItem('firstQuestion');
        localStorage.removeItem('totalQuestions');
      } catch (error) {
        console.error('Failed to parse first question:', error);
        handleSessionError();
      }
    } else {
      handleSessionError();
    }
  };

  const handleSessionError = () => {
    addMessage('interviewer', "I couldn't find your interview session. Please start a new interview from the document setup page.");
    showToast('Session expired. Please start a new interview.', 'warning');
    safeSetTimeout(() => navigate('/'), 3000);
  };

  const startInterviewWithQuestion = (question: any, total: number, isResume: boolean = false) => {
    setCurrentQuestion(question);
    setProgress((prev) => ({ ...prev, total }));

    const welcomeMsg = isResume 
      ? "Welcome back! Let's continue your interview."
      : "Welcome! Let's begin the interview. I'll be asking you questions based on your profile. Take your time to respond thoughtfully.";
    
    addMessage('interviewer', welcomeMsg);
    
    safeSetTimeout(() => {
      addMessage('interviewer', question.text);
      if (voiceOn && ttsSupported()) {
        speakSequential([
          isResume ? "Welcome back! Let's continue." : "Welcome! Let's begin the interview.",
          question.text
        ]);
      }
    }, 500);
  };

  const handleStartRecording = () => {
    if (!sttAvailable) {
      showToast('Speech recognition not supported in this browser. Please type your answer.', 'warning');
      return;
    }

    stopSpeaking();
    setIsRecording(true);
    setLiveTranscript('');
    
    stopRecognitionRef.current = startRecognition(
      (text) => {
        if (isMountedRef.current) {
          setLiveTranscript(text);
        }
      },
      (error) => {
        if (isMountedRef.current) {
          showToast(`Recognition error: ${error}`, 'error');
          setIsRecording(false);
        }
      }
    );
  };

  const handleRequestMic = async () => {
    if (!sttAvailable) {
      showToast('Speech recognition not supported in this browser. Please use Chrome or Edge.', 'warning');
      return;
    }
    const state = await requestMicPermission();
    if (!isMountedRef.current) {
      return;
    }
    setMicPermission(state);
    if (state === 'granted') {
      showToast('Microphone enabled', 'success');
    } else if (state === 'denied') {
      showToast('Microphone blocked. Please allow mic access in your browser settings.', 'error');
    } else {
      showToast('Unable to access microphone. Please try again.', 'warning');
    }
  };

  const handleStopRecording = () => {
    if (stopRecognitionRef.current) {
      stopRecognitionRef.current();
      stopRecognitionRef.current = null;
    }
    setIsRecording(false);
  };

  const handleSubmit = async () => {
    if (!sessionId) return;
    
    const answer = liveTranscript.trim() || typedInput.trim();
    if (!answer && !userCode.trim()) {
      showToast('Please provide an answer', 'warning');
      return;
    }

    addMessage('user', answer || userCode);

    setIsProcessing(true);
    handleStopRecording();
    setLiveTranscript('');
    setTypedInput('');

    try {
      const result = await api.nextInterview(
        sessionId,
        answer,
        userCode.trim() || undefined
      );

      if (result.is_done) {
        addMessage('interviewer', "Thank you for completing the interview! Let me prepare your feedback...");
        if (voiceOn && ttsSupported()) {
          speak("Thank you for completing the interview! Let me prepare your feedback.");
        }
        safeSetTimeout(() => navigate(`/done/${sessionId}`), 2500);
      } else {
        const responses: string[] = [];
        
        if (result.interviewer_message) {
          responses.push(result.interviewer_message);
          addMessage('interviewer', result.interviewer_message);
        }
        
        if (result.followup_question?.text) {
          responses.push(result.followup_question.text);
          safeSetTimeout(() => {
            addMessage('interviewer', result.followup_question!.text);
          }, 800);
        }
        
        if (result.next_question?.text) {
          responses.push(result.next_question.text);
          setCurrentQuestion(result.next_question);
          safeSetTimeout(() => {
            addMessage('interviewer', result.next_question!.text);
          }, responses.length > 1 ? 1600 : 800);
        }

        setUserCode('');
        setShowWhiteboard(false);
        setProgress(result.progress);

        if (voiceOn && ttsSupported() && responses.length > 0) {
          speakSequential(responses);
        }
      }
    } catch (error: any) {
      showToast(error.message || 'Failed to process answer', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleToggleVoice = () => {
    const newVoiceOn = !voiceOn;
    setVoiceOn(newVoiceOn);
    localStorage.setItem('voiceOn', String(newVoiceOn));
    if (!newVoiceOn) {
      stopSpeaking();
    }
    showToast(newVoiceOn ? 'Voice enabled' : 'Voice disabled', 'info');
  };

  const handleRepeatLast = () => {
    const lastInterviewerMessage = [...messages].reverse().find(m => m.role === 'interviewer');
    if (lastInterviewerMessage && voiceOn && ttsSupported()) {
      speak(lastInterviewerMessage.content);
    }
  };

  const handleEndInterview = async () => {
    if (!sessionId) return;

    handleStopRecording();
    stopSpeaking();
    clearPendingTimeouts();

    try {
      await api.endInterview(sessionId);
      showToast('Interview ended', 'success');
      navigate(`/done/${sessionId}`);
    } catch (error: any) {
      showToast(error.message || 'Failed to end interview', 'error');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isRecording && !isProcessing && typedInput.trim()) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="interview-room conversation-mode">
      <div className="conversation-container">
        {/* Header */}
        <div className="conversation-header">
          <div className="header-left">
            <div className="interviewer-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2a5 5 0 015 5v2a5 5 0 01-10 0V7a5 5 0 015-5z"/>
                <path d="M12 14c-5 0-9 2-9 5v3h18v-3c0-3-4-5-9-5z"/>
              </svg>
            </div>
            <div className="header-info">
              <h2>AI Interviewer</h2>
              <span className={`status ${isSpeaking ? 'speaking' : isProcessing ? 'thinking' : 'listening'}`}>
                {isSpeaking ? 'Speaking...' : isProcessing ? 'Thinking...' : 'Listening'}
              </span>
            </div>
          </div>
          <div className="header-right">
            <span className="timer">{formatTime(timer)}</span>
            <span className="progress-text">Q{progress.turn_index}/{progress.total}</span>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="chat-container" ref={chatContainerRef}>
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-bubble">
                {message.content}
              </div>
            </div>
          ))}
          
          {isProcessing && (
            <div className="message interviewer">
              <div className="message-bubble typing">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            </div>
          )}
        </div>

        {/* Voice Controls */}
        <div className="voice-controls">
          {!sttAvailable && (
            <div className="mic-permission-banner warning">
              Voice input is not supported in this browser. Please use Chrome or Edge.
            </div>
          )}
          {sttAvailable && micPermission !== 'granted' && (
            <div className="mic-permission-banner">
              <div className="mic-permission-text">
                {micPermission === 'denied'
                  ? 'Microphone access is blocked. Allow access in your browser settings.'
                  : 'Microphone access is not enabled. Click to allow microphone access.'}
              </div>
              <button className="btn btn-secondary" onClick={handleRequestMic}>
                Enable microphone
              </button>
            </div>
          )}
          {/* Live transcript display */}
          {isRecording && (
            <div className="live-transcript">
              <div className="transcript-label">
                <span className="recording-dot"></span>
                Listening...
              </div>
              <div className="transcript-text">
                {liveTranscript || '(Speak now...)'}
              </div>
            </div>
          )}

          <div className="control-buttons">
            {/* Main mic button - only show if STT is available */}
            {sttAvailable && (
              <button
                className={`btn-mic ${isRecording ? 'recording' : ''}`}
                onClick={isRecording ? handleStopRecording : handleStartRecording}
                disabled={isProcessing || isSpeaking}
              >
                {isRecording ? (
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/>
                    <path d="M19 10v2a7 7 0 01-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                  </svg>
                )}
              </button>
            )}

            {/* Submit button */}
            <button
              className="btn-submit"
              onClick={handleSubmit}
              disabled={isProcessing || (!(liveTranscript.trim() || typedInput.trim()) && !userCode.trim())}
            >
              {isProcessing ? 'Processing...' : 'Send'}
            </button>

            {/* Secondary controls */}
            <div className="secondary-controls">
              {ttsSupported() && (
                <>
                  <button
                    className={`btn-icon ${voiceOn ? 'active' : ''}`}
                    onClick={handleToggleVoice}
                    title={voiceOn ? 'Mute voice' : 'Enable voice'}
                  >
                    {voiceOn ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                        <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                        <line x1="23" y1="9" x2="17" y2="15"/>
                        <line x1="17" y1="9" x2="23" y2="15"/>
                      </svg>
                    )}
                  </button>

                  <button
                    className="btn-icon"
                    onClick={handleRepeatLast}
                    disabled={!voiceOn || isSpeaking}
                    title="Repeat last message"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="1 4 1 10 7 10"/>
                      <path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
                    </svg>
                  </button>
                </>
              )}

              {currentQuestion?.type === 'code' && (
                <button
                  className="btn-icon code"
                  onClick={() => setShowWhiteboard(true)}
                  title="Open code whiteboard"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="16 18 22 12 16 6"/>
                    <polyline points="8 6 2 12 8 18"/>
                  </svg>
                </button>
              )}

              <button
                className="btn-icon danger"
                onClick={handleEndInterview}
                title="End interview"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          {/* Text input */}
          <div className="text-input-fallback">
            <input
              type="text"
              value={typedInput}
              onChange={(e) => setTypedInput(e.target.value)}
              placeholder={sttAvailable ? "Or type your answer here..." : "Type your answer here..."}
              onKeyDown={handleKeyDown}
              disabled={isRecording || isProcessing}
            />
          </div>
        </div>
      </div>

      {/* Code Whiteboard Modal */}
      {showWhiteboard && (
        <div className="whiteboard-overlay" onClick={() => setShowWhiteboard(false)}>
          <div className="whiteboard-modal" onClick={(e) => e.stopPropagation()}>
            <div className="whiteboard-header">
              <h3>Code Whiteboard</h3>
              <button className="close-btn" onClick={() => setShowWhiteboard(false)}>
                ✕
              </button>
            </div>
            <textarea
              className="whiteboard-editor"
              value={userCode}
              onChange={(e) => setUserCode(e.target.value)}
              placeholder="Type your code solution here..."
              autoFocus
              spellCheck={false}
            />
            <div className="whiteboard-footer">
              <button className="btn btn-secondary" onClick={() => setShowWhiteboard(false)}>
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  setShowWhiteboard(false);
                  handleSubmit();
                }}
                disabled={!userCode.trim() && !(liveTranscript.trim() || typedInput.trim())}
              >
                Submit Code
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default InterviewRoom;
