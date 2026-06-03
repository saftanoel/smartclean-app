import { useState, useEffect } from "react";
import "./App.css";

type ApiStatus = "checking" | "connected" | "disconnected";

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const response = await fetch("http://localhost:8000/health");
        if (response.ok) {
          const data = await response.json();
          setApiStatus(data.status === "API is running" ? "connected" : "disconnected");
        } else {
          setApiStatus("disconnected");
        }
      } catch (error) {
        console.error("Failed to connect to API:", error);
        setApiStatus("disconnected");
      }
    };
    checkApiHealth();
  }, []);

  return (
    <div className="macos-window">
      <div data-tauri-drag-region className="mac-drag-region"></div>
      <div className="app-layout">
        {/* Sidebar */}
        <nav className="sidebar glass-panel">
          <div className="sidebar-header">
            <div className="app-icon">✨</div>
            <h1 className="app-title">SmartClean</h1>
          </div>

          <ul className="nav-menu">
            <li className="nav-item active">
              <span className="icon">📁</span>
              Dashboard
            </li>
            <li className="nav-item">
              <span className="icon">💬</span>
              AI Chat
            </li>
            <li className="nav-item">
              <span className="icon">⚙️</span>
              Settings
            </li>
          </ul>

          <div className="sidebar-footer">
            <div className="api-status">
              <span className={`status-dot ${apiStatus}`}></span>
              <span className="status-text">
                {apiStatus === "connected" ? "Backend Online" : apiStatus === "checking" ? "Connecting..." : "Offline"}
              </span>
            </div>
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="main-area">
          {/* Top Bar */}
          <header className="top-bar">
            <div className="breadcrumbs">
              <h2>Overview</h2>
              <span className="subtitle">Dashboard</span>
            </div>
            <button className="macos-button connect-button" disabled>
              <span className="icon">☁️</span>
              Connect to Drive
            </button>
          </header>

          {/* Dashboard Grid */}
          <div className="dashboard-grid">
            {/* File List Placeholder */}
            <div className="panel files-panel glass-panel">
              <div className="panel-header">
                <h3>Google Drive Files</h3>
                <span className="panel-badge">Placeholder</span>
              </div>
              <div className="panel-content empty-state">
                <div className="empty-icon">🗂️</div>
                <p>Connect your drive to see files</p>
                <span className="sub-text">AI will automatically analyze and organize them.</span>
              </div>
            </div>

            {/* AI Chat Placeholder */}
            <div className="panel ai-panel glass-panel">
              <div className="panel-header">
                <h3>SmartClean Assistant</h3>
              </div>
              <div className="chat-content">
                <div className="chat-bubble ai">
                  Hello! I'm your SmartClean AI. Connect your Google Drive and I'll help you find duplicates and free up space.
                </div>
              </div>
              <div className="chat-input-area">
                <input type="text" className="macos-input" placeholder="Ask AI to clean up your drive..." disabled />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
