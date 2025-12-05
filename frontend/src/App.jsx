// frontend/src/App.jsx
import React from 'react';
import './App.css'; // Import your main styles
import ChatContainer from './components/ChatContainer';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1
          onClick={() => window.location.reload()}
          style={{ cursor: 'pointer' }}
          title="Reload Chatbot"
        >
          CRRI Assistant
        </h1>
      </header>
      <main className="app-main">
        <ChatContainer />
      </main>
    </div>
  );
}

export default App;