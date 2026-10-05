import React, { useState } from 'react';

// Suggestions for quick topic selection
const SUGGESTIONS = [
  'Loops',
  'Data Structures',
  'Functions',
  'Conditionals',
  'Lists',
  'Strings',
  'Dictionaries',
  'File I/O'
];

// Input validation constants (must match server-side validation)
const TOPIC_MIN_LENGTH = 2;
const TOPIC_MAX_LENGTH = 100;
// Only allow alphanumeric, spaces, and basic punctuation
const ALLOWED_PATTERN = /^[a-zA-Z0-9\s\-_.,!?'"()]+$/;

/**
 * Validate topic input against security rules.
 * Returns error message or null if valid.
 */
function validateTopic(topic) {
  const trimmed = topic.trim();

  if (trimmed.length < TOPIC_MIN_LENGTH) {
    return `Topic must be at least ${TOPIC_MIN_LENGTH} characters`;
  }

  if (trimmed.length > TOPIC_MAX_LENGTH) {
    return `Topic must be less than ${TOPIC_MAX_LENGTH} characters`;
  }

  if (!ALLOWED_PATTERN.test(trimmed)) {
    return 'Topic contains invalid characters. Use only letters, numbers, and basic punctuation.';
  }

  return null;
}

function PromptInput({ onGenerate }) {
  const [topic, setTopic] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState(null);

  const handleTopicChange = (e) => {
    const value = e.target.value;
    setTopic(value);

    // Clear error when user starts typing
    if (validationError && value.trim().length >= TOPIC_MIN_LENGTH) {
      setValidationError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Client-side validation (defense in depth - server also validates)
    const error = validateTopic(topic);
    if (error) {
      setValidationError(error);
      return;
    }

    if (isSubmitting) return;

    setIsSubmitting(true);
    setValidationError(null);
    await onGenerate(topic.trim());
    setIsSubmitting(false);
  };

  const handleSuggestionClick = (suggestion) => {
    setTopic(suggestion);
  };

  return (
    <form className="prompt-form" onSubmit={handleSubmit}>
      <div className="input-group">
        <label htmlFor="topic">Enter a Python topic for your quiz</label>
        <input
          id="topic"
          type="text"
          className={`topic-input ${validationError ? 'input-error' : ''}`}
          value={topic}
          onChange={handleTopicChange}
          placeholder="e.g., Loops, Functions, Data Structures..."
          maxLength={TOPIC_MAX_LENGTH}
          minLength={TOPIC_MIN_LENGTH}
          disabled={isSubmitting}
          autoFocus
          aria-describedby={validationError ? 'topic-error' : undefined}
        />
        {validationError && (
          <p id="topic-error" className="validation-error" role="alert">
            {validationError}
          </p>
        )}
        <div className="suggestions">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              className="suggestion-chip"
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={isSubmitting}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        className="generate-btn"
        disabled={!topic.trim() || isSubmitting}
      >
        {isSubmitting ? 'Starting...' : 'Generate Quiz Video'}
      </button>
    </form>
  );
}

export default PromptInput;
