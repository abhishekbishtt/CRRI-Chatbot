// frontend/src/utils/api.js

// --- Configuration ---
// Use relative URL in production (when served from same origin)
// Use localhost in development (when using Vite dev server)
const API_BASE_URL = import.meta.env.PROD ? '' : 'http://localhost:8080';
const CHAT_ENDPOINT = '/chat';

/**
 * Sends the conversation history to the FastAPI backend and retrieves the bot's answer.
 * @param {Array} conversationHistory Array of message objects [{role: 'user', content: '...'}, {role: 'assistant', content: '...'}]
 * @returns {Promise<string>} A promise that resolves to the bot's answer text.
 */
export const sendMessageToAPI = async (conversationHistory) => {
  const url = `${API_BASE_URL}${CHAT_ENDPOINT}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header here if your API requires it
        // 'Authorization': `Bearer YOUR_API_TOKEN`,
      },
      // Send the conversation history in the request body
      body: JSON.stringify({ conversation_history: conversationHistory }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`API request failed with status ${response.status}:`, errorData);
      throw new Error(`API Error (${response.status}): ${errorData.detail || 'Failed to get response'}`);
    }

    const data = await response.json();
    return data.answer || "No answer provided.";
  } catch (error) {
    console.error("Error sending message to API:", error);
    throw error; // Re-throw for the caller to handle
  }
};