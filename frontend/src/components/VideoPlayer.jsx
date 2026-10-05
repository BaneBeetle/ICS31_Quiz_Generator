import React from 'react';

function VideoPlayer({ videoUrl, topic, onDownload, onNewVideo }) {
  return (
    <div className="video-container">
      <div className="success-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      <h2>Your Quiz Video is Ready!</h2>

      <div className="video-wrapper">
        <video
          controls
          autoPlay
          src={videoUrl}
        >
          Your browser does not support the video tag.
        </video>
      </div>

      <div className="action-buttons">
        <button className="download-btn" onClick={onDownload}>
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download Video
        </button>

        <button className="new-video-btn" onClick={onNewVideo}>
          Generate New Quiz
        </button>
      </div>
    </div>
  );
}

export default VideoPlayer;
