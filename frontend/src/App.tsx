import { useState, useEffect } from "react";
import { openUrl } from '@tauri-apps/plugin-opener';
import "./App.css";

type ApiStatus = "checking" | "connected" | "disconnected";

interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: string;
  modifiedTime: string;
}

interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [isConnected, setIsConnected] = useState(false);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);

  // --- NOU: State-uri pentru AI Chat ---
  const [chatInput, setChatInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'ai', text: "Hello! I'm your SmartClean AI. Connect your Google Drive and I'll help you find duplicates and free up space." }
  ]);

  const formatBytes = (bytes?: string) => {
    if (!bytes) return "--";
    const b = parseInt(bytes, 10);
    if (b < 1024) return b + " B";
    else if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    else return (b / 1048576).toFixed(1) + " MB";
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes("document")) return "📄";
    if (mimeType.includes("spreadsheet")) return "📊";
    if (mimeType.includes("presentation")) return "🖥️";
    if (mimeType.includes("pdf")) return "📕";
    if (mimeType.includes("folder")) return "📁";
    if (mimeType.includes("image")) return "🖼️";
    if (mimeType.includes("colaboratory")) return "📓";
    return "📄";
  };

  const getReadableFileType = (mimeType: string) => {
    if (mimeType.includes("document")) return "Google Doc";
    if (mimeType.includes("spreadsheet")) return "Google Sheet";
    if (mimeType.includes("presentation")) return "Google Slides";
    if (mimeType.includes("pdf")) return "PDF Document";
    if (mimeType.includes("folder")) return "Folder";
    if (mimeType.includes("colaboratory")) return "Jupyter Notebook";
    if (mimeType.includes("image")) return "Image";
    if (mimeType.includes("video")) return "Video";
    if (mimeType.includes("audio")) return "Audio";
    if (mimeType.includes("text")) return "Text File";
    if (mimeType.includes("zip") || mimeType.includes("compressed")) return "Archive";
    
    const parts = mimeType.split('/');
    if (parts.length > 1) {
      return parts[1].toUpperCase();
    }
    return "File";
  };

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>;

    const checkStatus = async () => {
      try {
        const healthRes = await fetch("http://localhost:8000/health");
        if (healthRes.ok) {
          setApiStatus("connected");
          const statusRes = await fetch("http://localhost:8000/api/status");
          const statusData = await statusRes.json();

          const newlyConnected = statusData.is_connected;

          if (newlyConnected && !isConnected) {
            setIsConnected(true);
            setMessages([{ sender: 'ai', text: "Drive connected successfully! I'm ready to analyze your files. What should we clean up?" }]);
            fetchFiles();
          } else if (!newlyConnected) {
            setIsConnected(false);
          }
        } else {
          setApiStatus("disconnected");
        }
      } catch (error) {
        setApiStatus("disconnected");
      }
    };

    const fetchFiles = async () => {
      setIsLoadingFiles(true);
      try {
        const res = await fetch("http://localhost:8000/api/files");
        if (res.ok) {
          const data = await res.json();
          setFiles(data.files);
        }
      } catch (error) {
        console.error("Eroare la aducerea fișierelor:", error);
      } finally {
        setIsLoadingFiles(false);
      }
    };

    checkStatus();
    intervalId = setInterval(checkStatus, 3000);

    return () => clearInterval(intervalId);
  }, [isConnected]);

  // --- NOU: Funcția care trimite mesajul la Gemini ---
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !isConnected || files.length === 0) return;

    const userText = chatInput;
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setChatInput("");
    setIsThinking(true);
    setSelectedIds([]); // Resetăm selecția veche

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userText, files: files })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { sender: 'ai', text: data.reply }]);
        setSelectedIds(data.selected_ids || []);
      } else {
        setMessages(prev => [...prev, { sender: 'ai', text: "Eroare: Nu am putut procesa comanda." }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { sender: 'ai', text: "Eroare de conexiune cu serverul." }]);
    } finally {
      setIsThinking(false);
    }
  };

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
          </ul>

          <div className="sidebar-footer">
            <div className="api-status">
              <span className={`status-dot ${apiStatus}`}></span>
              <span className="status-text">
                {apiStatus === "connected" ? "Backend Online" : "Offline"}
              </span>
            </div>
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="main-area">
          <header className="top-bar">
            <div className="breadcrumbs">
              <h2>Overview</h2>
              <span className="subtitle">Dashboard</span>
            </div>

            {!isConnected ? (
              <button
                className="macos-button connect-button"
                onClick={async () => await openUrl('http://localhost:8000/auth/login')}
              >
                <span className="icon">☁️</span>
                Connect to Drive
              </button>
            ) : (
              <div className="connected-badge">
                <span className="status-dot connected"></span>
                Drive Synced
              </div>
            )}
          </header>

          <div className="dashboard-grid">
            {/* File List Panel */}
            <div className="panel files-panel glass-panel">
              <div className="panel-header">
                <h3>Recent Files</h3>
                <span className="panel-badge">{files.length} items</span>
              </div>

              <div className={`panel-content ${!isConnected ? 'empty-state' : ''}`}>
                {!isConnected ? (
                  <>
                    <div className="empty-icon">🗂️</div>
                    <p>Connect your drive to see files</p>
                  </>
                ) : isLoadingFiles ? (
                  <div className="loading-spinner">Analyzing Drive...</div>
                ) : (
                  <ul className="file-list">
                    {files.map((file) => {
                      // VERIFICĂM DACA FISIERUL E SELECTAT DE AI
                      const isSelected = selectedIds.includes(file.id);

                      return (
                        <li key={file.id} className={`file-item ${isSelected ? 'selected-by-ai' : ''}`}>
                          <span className="file-icon">{getFileIcon(file.mimeType)}</span>
                          <div className="file-details">
                            <div className="file-name">{file.name}</div>
                            <span className="file-meta">
                              <span style={{color: "rgba(255,255,255,0.7)", fontWeight: 500}}>{getReadableFileType(file.mimeType)}</span> • {formatBytes(file.size)} • Modified {new Date(file.modifiedTime).toLocaleDateString()}
                            </span>
                          </div>
                          {isSelected && <span className="selection-badge">✓ Selected</span>}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>

            {/* AI Chat Panel */}
            <div className="panel ai-panel glass-panel">
              <div className="panel-header">
                <h3>SmartClean Assistant</h3>
              </div>
              <div className="chat-content">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`chat-bubble ${msg.sender}`}>
                    {msg.text}
                  </div>
                ))}
                {isThinking && (
                  <div className="chat-bubble ai thinking">
                    Thinking<span className="dots">...</span>
                  </div>
                )}
              </div>
              <div className="chat-input-area">
                <input
                  type="text"
                  className="macos-input"
                  placeholder={isConnected ? "e.g., Select all presentations..." : "Connect Drive to chat..."}
                  disabled={!isConnected || isThinking}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSendMessage();
                  }}
                />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;