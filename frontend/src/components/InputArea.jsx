// src/components/InputArea.jsx
import React from 'react';

const InputArea = ({ inputText, isLoading, onInputChange, onSend, onKeyPress }) => {
  return (
    <div className="input-area">
      <textarea
        value={inputText}
        onChange={onInputChange}
        onKeyDown={onKeyPress}
        placeholder="Ask me about CRRI..."
        disabled={isLoading}
        className="message-input"
        rows="1"
      />
      <button onClick={onSend} disabled={isLoading || !inputText.trim()} className="send-button">
        {/* Simple text send button, or use an icon */}
        Send
      </button>
    </div>
  );
};

export default InputArea;