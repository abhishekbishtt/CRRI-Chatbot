import React from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'; // For tables and better lists
import TenderCard from './TenderCard';

const MessageBubble = ({ message }) => {
  // Determine class based on sender
  const bubbleClass = message.sender === 'user' ? 'message-bubble user' : 'message-bubble bot';

  // Check if the message contains special JSON data for tenders
  let tenderData = null;
  let displayText = message.text;

  // Helper function to extract and parse JSON from text
  const extractJsonData = (text, key) => {
    // First try: JSON inside ```json ... ``` code blocks
    const codeBlockRegex = new RegExp('```(?:json)?\\s*({[\\s\\S]*?"' + key + '":[\\s\\S]*?})\\s*```', 'i');
    let match = text.match(codeBlockRegex);

    if (match && match[1]) {
      try {
        const parsed = JSON.parse(match[1]);
        if (parsed[key]) {
          return { data: parsed[key], fullMatch: match[0] };
        }
      } catch (e) {
        console.error(`Failed to parse ${key} JSON from code block`, e);
      }
    }

    // Second try: Raw JSON (not in code blocks) - fallback for when LLM doesn't format correctly
    const rawJsonRegex = new RegExp('({"' + key + '":\\s*\\[[\\s\\S]*?\\]\\s*})', 'i');
    match = text.match(rawJsonRegex);

    if (match && match[1]) {
      try {
        const parsed = JSON.parse(match[1]);
        if (parsed[key]) {
          return { data: parsed[key], fullMatch: match[0] };
        }
      } catch (e) {
        console.error(`Failed to parse raw ${key} JSON`, e);
      }
    }

    return null;
  };

  // Extract tenders data
  const tendersResult = extractJsonData(message.text, 'tenders');
  if (tendersResult) {
    tenderData = tendersResult.data;
    displayText = displayText.replace(tendersResult.fullMatch, '').trim();
  }

  // Also extract events data (similar structure to tenders)
  const eventsResult = extractJsonData(displayText, 'events');
  let eventData = null;
  if (eventsResult) {
    eventData = eventsResult.data;
    displayText = displayText.replace(eventsResult.fullMatch, '').trim();
  }

  return (
    <motion.div
      className={bubbleClass}
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      {message.sender === 'bot' ? (
        <div className="markdown-content">
          {/* Render text content first */}
          {displayText && (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]} // Enable tables, strikethrough, etc.
              components={{
                // Ensure links open in a new tab and look nice
                a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
                // Style tables if they appear
                table: ({ node, ...props }) => <div className="table-wrapper"><table {...props} /></div>,
              }}
            >
              {displayText}
            </ReactMarkdown>
          )}

          {/* Render Rich Tender Cards if data exists */}
          {tenderData && (
            <div className="rich-content-container">
              <TenderCard tenders={tenderData} />
            </div>
          )}
        </div>
      ) : (
        <div className="markdown-content">
          <ReactMarkdown>{message.text}</ReactMarkdown>
        </div>
      )}
    </motion.div>
  );
};

export default MessageBubble;