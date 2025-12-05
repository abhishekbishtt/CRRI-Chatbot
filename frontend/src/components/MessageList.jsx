// src/components/MessageList.jsx
import React from 'react';
import MessageBubble from './MessageBubble';

const MessageList = ({ messages, isLoading, messagesEndRef }) => {
  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isLoading && (
        <div className="message-bubble bot">
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      )}
      {/* Invisible element for scrolling to the bottom */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;