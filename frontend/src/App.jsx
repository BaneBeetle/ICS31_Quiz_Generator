import React, { useState, useCallback, useEffect, useRef } from 'react';
import PromptInput from './components/PromptInput';
import LoadingScreen from './components/LoadingScreen';
import VideoPlayer from './components/VideoPlayer';
import './App.css';

// The production build is served by the API server (directly or behind Nginx),
// so it calls the API on its own origin. The dev server (`npm start`, port 3000)
// calls the API on port 8000. REACT_APP_API_URL, read at build/start time,
// overrides both.
const API_BASE =
  process.env.REACT_APP_API_URL ??
  (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

function App() {
  const [stage, setStage] = useState('input'); // input, loading, complete, error
  const [topic, setTopic] = useState('');
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState(null);
  const jobIdRef = useRef(null);  // Track jobId for cleanup

  // Update ref whenever jobId changes
  useEffect(() => {
    jobIdRef.current = jobId;
  }, [jobId]);

  // Cleanup job when user leaves the page
  useEffect(() => {
    const cleanupJob = () => {
      if (jobIdRef.current) {
        // Use sendBeacon for reliable cleanup on page unload
        navigator.sendBeacon(`${API_BASE}/api/job/${jobIdRef.current}/cleanup`);
      }
    };

    // Clean up when tab/window closes
    window.addEventListener('beforeunload', cleanupJob);

    // Clean up when component unmounts
    return () => {
      window.removeEventListener('beforeunload', cleanupJob);
      cleanupJob();
    };
  }, []);

  const pollStatus = useCallback(async (id) => {
    try {
      const response = await fetch(`${API_BASE}/api/status/${id}`);
      if (response.status === 429) {
        // Rate limited: wait and keep polling instead of failing the job
        setTimeout(() => pollStatus(id), 5000);
        return;
      }
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get status');
      }

      setProgress(data.progress);
      setStatusMessage(data.message);

      if (data.status === 'completed') {
        setStage('complete');
        return;
      }

      if (data.status === 'failed') {
        setError(data.error || 'Video generation failed');
        setStage('error');
        return;
      }

      // Continue polling if still processing
      if (data.status === 'processing' || data.status === 'pending') {
        setTimeout(() => pollStatus(id), 2000);
      }
    } catch (err) {
      setError(err.message);
      setStage('error');
    }
  }, []);

  const handleGenerate = async (inputTopic) => {
    setTopic(inputTopic);
    setStage('loading');
    setProgress(0);
    setStatusMessage('Starting...');
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic: inputTopic }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start generation');
      }

      setJobId(data.job_id);
      pollStatus(data.job_id);
    } catch (err) {
      setError(err.message);
      setStage('error');
    }
  };

  const handleDownload = () => {
    if (jobId) {
      window.open(`${API_BASE}/api/video/${jobId}`, '_blank');
    }
  };

  const handleReset = async () => {
    // Delete the old job/video before resetting
    if (jobId) {
      try {
        await fetch(`${API_BASE}/api/job/${jobId}`, { method: 'DELETE' });
      } catch (err) {
        console.warn('Failed to cleanup old job:', err);
      }
    }

    setStage('input');
    setTopic('');
    setJobId(null);
    setProgress(0);
    setStatusMessage('');
    setError(null);
  };

  const getVideoUrl = () => {
    return jobId ? `${API_BASE}/api/video/${jobId}/stream` : null;
  };

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>ICS 31 Quiz Generator</h1>
          <p>Create engaging Python quiz videos instantly</p>
        </header>

        {stage === 'input' && (
          <PromptInput onGenerate={handleGenerate} />
        )}

        {stage === 'loading' && (
          <LoadingScreen
            progress={progress}
            message={statusMessage}
            topic={topic}
          />
        )}

        {stage === 'complete' && (
          <VideoPlayer
            videoUrl={getVideoUrl()}
            topic={topic}
            onDownload={handleDownload}
            onNewVideo={handleReset}
          />
        )}

        {stage === 'error' && (
          <div className="error-container">
            <div className="error-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            </div>
            <h2>Generation Failed</h2>
            <p className="error-message">{error}</p>
            <button className="retry-btn" onClick={handleReset}>
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
