import React from 'react';

function LoadingScreen({ progress, message, topic }) {
  return (
    <div className="loading-container">
      <div className="loading-animation">
        <div className="spinner"></div>
      </div>

      <div className="loading-text">
        <h2>Generating Your Quiz</h2>
        <p>Topic: {topic}</p>
      </div>

      <div className="progress-bar-container">
        <div
          className="progress-bar"
          style={{ width: `${progress}%` }}
        ></div>
      </div>

      <p className="progress-percentage">{progress}%</p>
      <p style={{ color: 'rgba(255, 255, 255, 0.6)', marginTop: '10px' }}>
        {message}
      </p>
    </div>
  );
}

export default LoadingScreen;
