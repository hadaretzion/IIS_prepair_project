import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import './DocumentSetup.css';

function DocumentSetup() {
  const navigate = useNavigate();
  const [cvText, setCvText] = useState('');
  const [jdText, setJdText] = useState('');
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [cvInputMode, setCvInputMode] = useState<'text' | 'file'>('text');
  const [jdInputMode, setJdInputMode] = useState<'text' | 'file'>('text');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleAnalyzeAndImprove = async () => {
    const userId = localStorage.getItem('userId');
    if (!userId) {
      alert('Please ensure you are logged in');
      return;
    }

    // Validate inputs
    if (cvInputMode === 'file' && !cvFile) {
      alert('Please upload a CV file');
      return;
    }
    if (cvInputMode === 'text' && !cvText.trim()) {
      alert('Please provide CV text');
      return;
    }
    if (jdInputMode === 'file' && !jdFile) {
      alert('Please upload a JD file');
      return;
    }
    if (jdInputMode === 'text' && !jdText.trim()) {
      alert('Please provide JD text');
      return;
    }

    setLoading(true);
    setUploading(true);
    try {
      // Ingest CV (file or text)
      let cvResult;
      if (cvInputMode === 'file' && cvFile) {
        cvResult = await api.ingestCVPDF(userId, cvFile);
      } else {
        cvResult = await api.ingestCV(userId, cvText);
      }

      // Ingest JD (file or text)
      let jdResult;
      if (jdInputMode === 'file' && jdFile) {
        jdResult = await api.ingestJDPDF(userId, jdFile);
      } else {
        jdResult = await api.ingestJD(userId, jdText);
      }

      // Analyze CV
      await api.analyzeCV(userId, cvResult.cv_version_id, jdResult.job_spec_id);

      // Store IDs for CV improve page
      localStorage.setItem('cvVersionId', cvResult.cv_version_id);
      localStorage.setItem('jobSpecId', jdResult.job_spec_id);
      // Store text if available (for editing)
      if (cvInputMode === 'text') {
        localStorage.setItem('cvText', cvText);
      }

      navigate('/cv-improve');
    } catch (error: any) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
      setUploading(false);
    }
  };

  const handleSkipToInterview = async () => {
    const userId = localStorage.getItem('userId');
    if (!userId) {
      alert('Please ensure you are logged in');
      return;
    }

    // Validate inputs
    if (cvInputMode === 'file' && !cvFile) {
      alert('Please upload a CV file');
      return;
    }
    if (cvInputMode === 'text' && !cvText.trim()) {
      alert('Please provide CV text');
      return;
    }
    if (jdInputMode === 'file' && !jdFile) {
      alert('Please upload a JD file');
      return;
    }
    if (jdInputMode === 'text' && !jdText.trim()) {
      alert('Please provide JD text');
      return;
    }

    setLoading(true);
    setUploading(true);
    try {
      // Ingest CV (file or text)
      let cvResult;
      if (cvInputMode === 'file' && cvFile) {
        cvResult = await api.ingestCVPDF(userId, cvFile);
      } else {
        cvResult = await api.ingestCV(userId, cvText);
      }

      // Ingest JD (file or text)
      let jdResult;
      if (jdInputMode === 'file' && jdFile) {
        jdResult = await api.ingestJDPDF(userId, jdFile);
      } else {
        jdResult = await api.ingestJD(userId, jdText);
      }

      // Start interview
      const sessionResult = await api.startInterview(
        userId,
        jdResult.job_spec_id,
        cvResult.cv_version_id,
        'direct',
        { num_open: 4, num_code: 2, duration_minutes: 12 }
      );

      // Store first question and plan summary for InterviewRoom
      if (sessionResult.first_question) {
        localStorage.setItem('firstQuestion', JSON.stringify(sessionResult.first_question));
      }
      if (sessionResult.plan_summary) {
        localStorage.setItem('planSummary', JSON.stringify(sessionResult.plan_summary));
      }
      if (sessionResult.total_questions) {
        localStorage.setItem('totalQuestions', sessionResult.total_questions.toString());
      }

      navigate(`/pre-interview?sessionId=${sessionResult.session_id}`);
    } catch (error: any) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
      setUploading(false);
    }
  };

  return (
    <div className="document-setup">
      <div className="container">
        <h1>Document Setup</h1>
        <p>Upload PDF files or paste text for your CV and Job Description</p>

        <div className="input-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <label>CV</label>
            <div>
              <button
                type="button"
                onClick={() => {
                  setCvInputMode('text');
                  setCvFile(null);
                }}
                style={{
                  marginRight: '10px',
                  padding: '5px 10px',
                  backgroundColor: cvInputMode === 'text' ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Text
              </button>
              <button
                type="button"
                onClick={() => {
                  setCvInputMode('file');
                  setCvText('');
                }}
                style={{
                  padding: '5px 10px',
                  backgroundColor: cvInputMode === 'file' ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                PDF Upload
              </button>
            </div>
          </div>
          {cvInputMode === 'file' ? (
            <div>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    if (file.type !== 'application/pdf') {
                      alert('Please select a PDF file');
                      return;
                    }
                    setCvFile(file);
                  }
                }}
                style={{ marginBottom: '10px' }}
              />
              {cvFile && (
                <p style={{ color: '#28a745', fontSize: '14px' }}>
                  ✓ {cvFile.name} selected
                </p>
              )}
            </div>
          ) : (
            <textarea
              value={cvText}
              onChange={(e) => setCvText(e.target.value)}
              placeholder="Paste your CV text here..."
              rows={15}
            />
          )}
        </div>

        <div className="input-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <label>Job Description</label>
            <div>
              <button
                type="button"
                onClick={() => {
                  setJdInputMode('text');
                  setJdFile(null);
                }}
                style={{
                  marginRight: '10px',
                  padding: '5px 10px',
                  backgroundColor: jdInputMode === 'text' ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Text
              </button>
              <button
                type="button"
                onClick={() => {
                  setJdInputMode('file');
                  setJdText('');
                }}
                style={{
                  padding: '5px 10px',
                  backgroundColor: jdInputMode === 'file' ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                PDF Upload
              </button>
            </div>
          </div>
          {jdInputMode === 'file' ? (
            <div>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    if (file.type !== 'application/pdf') {
                      alert('Please select a PDF file');
                      return;
                    }
                    setJdFile(file);
                  }
                }}
                style={{ marginBottom: '10px' }}
              />
              {jdFile && (
                <p style={{ color: '#28a745', fontSize: '14px' }}>
                  ✓ {jdFile.name} selected
                </p>
              )}
            </div>
          ) : (
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the job description here..."
              rows={15}
            />
          )}
        </div>

        <div className="action-buttons">
          <button
            className="btn btn-primary"
            onClick={handleAnalyzeAndImprove}
            disabled={loading || uploading || 
              (cvInputMode === 'file' ? !cvFile : !cvText.trim()) ||
              (jdInputMode === 'file' ? !jdFile : !jdText.trim())}
          >
            {uploading ? 'Uploading...' : loading ? 'Processing...' : 'Analyze & Improve CV'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleSkipToInterview}
            disabled={loading || uploading ||
              (cvInputMode === 'file' ? !cvFile : !cvText.trim()) ||
              (jdInputMode === 'file' ? !jdFile : !jdText.trim())}
          >
            {uploading ? 'Uploading...' : loading ? 'Starting...' : 'Skip to Interview'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default DocumentSetup;
