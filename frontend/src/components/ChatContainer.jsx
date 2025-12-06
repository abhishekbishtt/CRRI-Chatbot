// frontend/src/components/ChatContainer.jsx
import React, { useState, useRef, useEffect } from 'react';
import MessageList from './MessageList';
import InputArea from './InputArea';
import SuggestedQuestions from './SuggestedQuestions';
import { sendMessageToAPI } from '../utils/api';

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async () => {
    const question = inputText.trim();
    if (!question || isLoading) return;

    const userMessage = { id: Date.now(), text: question, sender: 'user' };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputText('');
    setIsLoading(true);

    try {
      const conversationHistory = newMessages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.text
      }));

      const answer = await sendMessageToAPI(conversationHistory);

      const botMessage = { id: Date.now() + 1, text: answer, sender: 'bot' };
      setMessages(prevMessages => [...prevMessages, botMessage]);
    } catch (error) {
      console.error("Error fetching response:", error);
      const errorMessage = { id: Date.now() + 1, text: "Sorry, I couldn't get a response. Please try again.", sender: 'bot' };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestedQuestion = (question) => {
    setInputText(question);
    setTimeout(() => {
      const userMessage = { id: Date.now(), text: question, sender: 'user' };
      const newMessages = [...messages, userMessage];
      setMessages(newMessages);
      setInputText('');
      setIsLoading(true);

      (async () => {
        try {
          const conversationHistory = newMessages.map(msg => ({
            role: msg.sender === 'user' ? 'user' : 'assistant',
            content: msg.text
          }));

          const answer = await sendMessageToAPI(conversationHistory);
          const botMessage = { id: Date.now() + 1, text: answer, sender: 'bot' };
          setMessages(prevMessages => [...prevMessages, botMessage]);
        } catch (error) {
          console.error("Error fetching response:", error);
          const errorMessage = {
            id: Date.now() + 1,
            text: "Sorry, I couldn't get a response. Please try again.",
            sender: 'bot'
          };
          setMessages(prevMessages => [...prevMessages, errorMessage]);
        } finally {
          setIsLoading(false);
        }
      })();
    }, 100);
  };

  return (
    <div className="chat-container">
      {messages.length === 0 ? (
        <SuggestedQuestions onQuestionClick={handleSuggestedQuestion} />
      ) : (
        <MessageList messages={messages} isLoading={isLoading} messagesEndRef={messagesEndRef} />
      )}
      <InputArea
        inputText={inputText}
        isLoading={isLoading}
        onInputChange={handleInputChange}
        onSend={handleSend}
        onKeyPress={handleKeyPress}
      />
    </div>
  );
};

export default ChatContainer;