// src/components/InputArea.jsx
import React from 'react';
import { motion } from 'framer-motion';

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
      <motion.button
        onClick={onSend}
        disabled={isLoading || !inputText.trim()}
        className="send-button"
        title="Send Message"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.90 }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"></line>
          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg>
      </motion.button>
    </div>
  );
};

export default InputArea;