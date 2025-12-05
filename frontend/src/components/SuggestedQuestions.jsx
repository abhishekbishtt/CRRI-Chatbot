// frontend/src/components/SuggestedQuestions.jsx
import React from 'react';

const SuggestedQuestions = ({ onQuestionClick }) => {
    const suggestions = [
        {
            icon: '👤',
            text: 'May I know the contact details of Miss Reeta Kukreja?'
        },
        {
            icon: '📋',
            text: 'Can you provide information about current tenders?'
        },
        {
            icon: '🔧',
            text: 'What is the working principle and applications of Pile Integrity Tester (PIT)?'
        },
        {
            icon: '💰',
            text: 'What are the instrument usage charges for Ultrasonic Pulse Echo Test System?'
        }
    ];

    return (
        <div className="suggestions-container">
            <div className="suggestions-content">
                <div className="suggestions-welcome">
                    <h2>Welcome to CRRI Assistant</h2>
                    <p>How can I help you today?</p>
                </div>
                <div className="suggestions-grid">
                    {suggestions.map((suggestion, index) => (
                        <div
                            key={index}
                            className="suggestion-card"
                            onClick={() => onQuestionClick(suggestion.text)}
                        >
                            <div className="suggestion-icon">{suggestion.icon}</div>
                            <div className="suggestion-text">{suggestion.text}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default SuggestedQuestions;
