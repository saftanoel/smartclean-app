import { useState, useEffect } from "react";
import "./App.css";

type ApiStatus = "checking" | "connected" | "disconnected";

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    // Fetch the health endpoint from the FastAPI backend
    const checkApiHealth = async () => {
      try {
        const response = await fetch("http://localhost:8000/health");
        if (response.ok) {
          const data = await response.json();
          if (data.status === "API is running") {
            setApiStatus("connected");
          } else {
            setApiStatus("disconnected");
          }
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
    <div className="container">
      <header className="app-header">
        <h1>SmartClean</h1>
        <div className="status-container">
          <span className={`status-dot ${apiStatus}`}></span>
          <span className="status-text">
            {apiStatus === "connected"
              ? "Backend Connected"
              : apiStatus === "disconnected"
              ? "Backend Disconnected"
              : "Checking API..."}
          </span>
        </div>
      </header>

      <main className="main-content">
        <p className="description">
          AI-powered Google Drive cleaner. Connect your account to securely scan and organize your files.
        </p>
        <button className="connect-btn" disabled>
          Connect to Google Drive
        </button>
      </main>
    </div>
  );
}

export default App;
