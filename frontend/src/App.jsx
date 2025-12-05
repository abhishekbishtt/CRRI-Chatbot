import React from 'react';
import './App.css'; // Import your main styles
import ChatContainer from './components/ChatContainer';
import { useTheme } from './context/ThemeContext';

function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="app">
      <header className="app-header">
        <h1
          onClick={(e) => {
            e.preventDefault();
            window.location.href = window.location.origin;
          }}
          style={{
            cursor: 'pointer',
            userSelect: 'none',
            WebkitUserSelect: 'none',
            mozUserSelect: 'none'
          }}
          title="Reload Chatbot - Go to Home"
        >
          CRRI Assistant
        </h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="theme-toggle-btn"
            onClick={() => toggleTheme('vscode')}
            style={{ opacity: theme === 'vscode' ? 1 : 0.6 }}
          >
            VS Code
          </button>
          <button
            className="theme-toggle-btn"
            onClick={() => toggleTheme('light')}
            style={{ opacity: theme === 'light' ? 1 : 0.6 }}
          >
            Light
          </button>
          <button
            className="theme-toggle-btn"
            onClick={() => toggleTheme('cyberpunk')}
            style={{ opacity: theme === 'cyberpunk' ? 1 : 0.6 }}
          >
            Cyberpunk
          </button>
        </div>
      </header>
      <main className="app-main">
        <ChatContainer />
      </main>
    </div>
  );
}

export default App;