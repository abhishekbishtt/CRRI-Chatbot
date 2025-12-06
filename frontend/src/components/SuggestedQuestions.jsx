import React from 'react';
import { motion } from 'framer-motion';

const SuggestedQuestions = ({ onQuestionClick }) => {
    const suggestions = [
        {
            icon: '📋',
            text: 'Can you provide information about current tenders?'
        },
        {
            icon: '👤',
            text: 'May I know the contact details of Miss Reeta Kukreja?'
        },
        {
            icon: '🏠',
            text: 'How to get accomodation at CRRI delhi'
        },
        {
            icon: '🔧',
            text: 'What is the working principle and applications of Pile Integrity Tester (PIT)?'
        }
    ];

    return (
        <div className="suggestions-container">
            <motion.div
                className="suggestions-content"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div className="suggestions-welcome">
                    <h2>Welcome to CRRI Assistant</h2>
                    <p>How can I help you today?</p>
                </div>
                <div className="suggestions-grid">
                    {suggestions.map((suggestion, index) => (
                        <motion.div
                            key={index}
                            className="suggestion-card"
                            onClick={() => onQuestionClick(suggestion.text)}
                            whileHover={{ scale: 1.01, x: 3, backgroundColor: "var(--bg-hover)" }}
                            whileTap={{ scale: 0.99 }}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1, type: "spring", stiffness: 300, damping: 20 }}
                        >
                            <div className="suggestion-icon">{suggestion.icon}</div>
                            <div className="suggestion-text">{suggestion.text}</div>
                        </motion.div>
                    ))}
                </div>
            </motion.div>
        </div>
    );
};

export default SuggestedQuestions;
