import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { FullPageLoader } from '../components/LoadingSpinner';
import './DocumentSetup.css';

function DocumentSetup() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [cvText, setCvText] = useState('');
  const [jdText, setJdText] = useState('');
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [cvInputMode, setCvInputMode] = useState<'text' | 'file'>('text');
  const [jdInputMode, setJdInputMode] = useState<'text' | 'file'>('text');
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');

  const validateInputs = () => {
    const userId = localStorage.getItem('userId');
    if (!userId) {
      showToast('Session expired. Please start again.', 'error');
      navigate('/');
      return false;
    }

    if (cvInputMode === 'file' && !cvFile) {
      showToast('Please upload a CV file', 'warning');
      return false;
    }
    if (cvInputMode === 'text' && !cvText.trim()) {
      showToast('Please provide CV text', 'warning');
      return false;
    }
    if (jdInputMode === 'file' && !jdFile) {
      showToast('Please upload a Job Description file', 'warning');
      return false;
    }
    if (jdInputMode === 'text' && !jdText.trim()) {
      showToast('Please provide Job Description text', 'warning');
      return false;
    }
    return true;
  };

  const handleAnalyzeAndImprove = async () => {
    if (!validateInputs()) return;
    const userId = localStorage.getItem('userId')!;

    setLoading(true);
    setLoadingMessage('Uploading documents...');
    try {
      let cvResult;
      if (cvInputMode === 'file' && cvFile) {
        cvResult = await api.ingestCVPDF(userId, cvFile);
      } else {
        cvResult = await api.ingestCV(userId, cvText);
      }

      let jdResult;
      if (jdInputMode === 'file' && jdFile) {
        jdResult = await api.ingestJDPDF(userId, jdFile);
      } else {
        jdResult = await api.ingestJD(userId, jdText);
      }

      setLoadingMessage('Analyzing your CV...');
      await api.analyzeCV(userId, cvResult.cv_version_id, jdResult.job_spec_id);

      localStorage.setItem('cvVersionId', cvResult.cv_version_id);
      localStorage.setItem('jobSpecId', jdResult.job_spec_id);
      if (cvInputMode === 'text') {
        localStorage.setItem('cvText', cvText);
      }

      showToast('CV analysis complete!', 'success');
      navigate('/cv-improve');
    } catch (error: any) {
      showToast(error.message || 'Failed to analyze CV. Please try again.', 'error');
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const handleSkipToInterview = async () => {
    if (!validateInputs()) return;
    const userId = localStorage.getItem('userId')!;

    setLoading(true);
    setLoadingMessage('Uploading documents...');
    try {
      let cvResult;
      if (cvInputMode === 'file' && cvFile) {
        cvResult = await api.ingestCVPDF(userId, cvFile);
      } else {
        cvResult = await api.ingestCV(userId, cvText);
      }

      let jdResult;
      if (jdInputMode === 'file' && jdFile) {
        jdResult = await api.ingestJDPDF(userId, jdFile);
      } else {
        jdResult = await api.ingestJD(userId, jdText);
      }

      setLoadingMessage('Preparing interview questions...');
      const sessionResult = await api.startInterview(
        userId,
        jdResult.job_spec_id,
        cvResult.cv_version_id,
        'direct',
        { num_open: 4, num_code: 2, duration_minutes: 12 }
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

      showToast('Interview ready! Good luck!', 'success');
      navigate(`/pre-interview?sessionId=${sessionResult.session_id}`);
    } catch (error: any) {
      showToast(error.message || 'Failed to start interview. Please try again.', 'error');
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    setFile: (file: File | null) => void
  ) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        showToast('Please select a PDF file', 'warning');
        return;
      }
      setFile(file);
      showToast(`${file.name} selected`, 'success');
    }
  };

  return (
    <div className="document-setup">
      {loading && <FullPageLoader message={loadingMessage} />}
      <div className="container">
        <h1>Document Setup</h1>
        <p>Upload PDF files or paste text for your CV and Job Description</p>

        <div className="input-group">
          <div className="input-header">
            <label>CV / Resume</label>
            <div className="mode-toggle">
              <button
                type="button"
                onClick={() => { setCvInputMode('text'); setCvFile(null); }}
                className={`toggle-btn ${cvInputMode === 'text' ? 'active' : ''}`}
              >
                Text
              </button>
              <button
                type="button"
                onClick={() => { setCvInputMode('file'); setCvText(''); }}
                className={`toggle-btn ${cvInputMode === 'file' ? 'active' : ''}`}
              >
                PDF Upload
              </button>
            </div>
          </div>
          {cvInputMode === 'file' ? (
            <div className="file-upload">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileChange(e, setCvFile)}
                id="cv-file"
              />
              <label htmlFor="cv-file" className="file-label">
                {cvFile ? (
                  <span className="file-selected">✓ {cvFile.name}</span>
                ) : (
                  <span>Click to upload PDF</span>
                )}
              </label>
            </div>
          ) : (
            <textarea
              value={cvText}
              onChange={(e) => setCvText(e.target.value)}
              placeholder="Paste your CV text here..."
              rows={12}
            />
          )}
        </div>

        <div className="input-group">
          <div className="input-header">
            <label>Job Description</label>
            <div className="mode-toggle">
              <button
                type="button"
                onClick={() => { setJdInputMode('text'); setJdFile(null); }}
                className={`toggle-btn ${jdInputMode === 'text' ? 'active' : ''}`}
              >
                Text
              </button>
              <button
                type="button"
                onClick={() => { setJdInputMode('file'); setJdText(''); }}
                className={`toggle-btn ${jdInputMode === 'file' ? 'active' : ''}`}
              >
                PDF Upload
              </button>
            </div>
          </div>
          {jdInputMode === 'file' ? (
            <div className="file-upload">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileChange(e, setJdFile)}
                id="jd-file"
              />
              <label htmlFor="jd-file" className="file-label">
                {jdFile ? (
                  <span className="file-selected">✓ {jdFile.name}</span>
                ) : (
                  <span>Click to upload PDF</span>
                )}
              </label>
            </div>
          ) : (
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the job description here..."
              rows={12}
            />
          )}
        </div>

        <div className="action-buttons">
          <button
            className="btn btn-primary"
            onClick={handleAnalyzeAndImprove}
            disabled={loading || 
              (cvInputMode === 'file' ? !cvFile : !cvText.trim()) ||
              (jdInputMode === 'file' ? !jdFile : !jdText.trim())}
          >
            Analyze & Improve CV
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleSkipToInterview}
            disabled={loading ||
              (cvInputMode === 'file' ? !cvFile : !cvText.trim()) ||
              (jdInputMode === 'file' ? !jdFile : !jdText.trim())}
          >
            Skip to Interview
          </button>
        </div>
      </div>
    </div>
  );
}

export default DocumentSetup;
