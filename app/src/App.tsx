import { Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import DocumentSetup from './pages/DocumentSetup';
import CvImprove from './pages/CvImprove';
import InterviewSettings from './pages/InterviewSettings';
import PreInterview from './pages/PreInterview';
import InterviewRoom from './pages/InterviewRoom';
import Done from './pages/Done';
import FeedbackPlaceholder from './pages/FeedbackPlaceholder';
import Dashboard from './pages/Dashboard';
import InterviewHistory from './pages/InterviewHistory';
import './App.css';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/setup" element={<DocumentSetup />} />
      <Route path="/cv-improve" element={<CvImprove />} />
      <Route path="/interview/settings" element={<InterviewSettings />} />
      <Route path="/pre-interview" element={<PreInterview />} />
      <Route path="/interview/:sessionId" element={<InterviewRoom />} />
      <Route path="/done/:sessionId" element={<Done />} />
      <Route path="/feedback/:sessionId" element={<FeedbackPlaceholder />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/history" element={<InterviewHistory />} />
    </Routes>
  );
}

export default App;
