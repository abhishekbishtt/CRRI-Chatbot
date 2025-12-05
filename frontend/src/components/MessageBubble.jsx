// frontend/src/components/MessageBubble.jsx
import React from 'react';
import ReactMarkdown from 'react-markdown'; // Import ReactMarkdown

const MessageBubble = ({ message }) => {
  // Determine class based on sender
  const bubbleClass = message.sender === 'user' ? 'message-bubble user' : 'message-bubble bot';

  return (
    <div className={bubbleClass}>
      {/* Use ReactMarkdown to render the content for bot messages */}
      {/* For user messages, plain text is usually sufficient, but we can use it too */}
      {message.sender === 'bot' ? (
        <div className="markdown-content">
          <ReactMarkdown
            components={{
              // Ensure links open in a new tab
              a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" />,
            }}
          >
            {message.text}
          </ReactMarkdown>
        </div>
      ) : (
        // Optionally, render user messages with ReactMarkdown too, or keep as plain text
        // <div className="message-text">{message.text}</div>
        <div className="markdown-content">
           <ReactMarkdown>{message.text}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default MessageBubble;