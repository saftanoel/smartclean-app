import { useState, useEffect } from "react";
import { openUrl } from '@tauri-apps/plugin-opener';
import "./App.css";

type ApiStatus = "checking" | "connected" | "disconnected";

// Definim structura unui fișier venit de la Google Drive
interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: string;
  modifiedTime: string;
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [isConnected, setIsConnected] = useState(false);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);

  // Funcție ajutătoare pentru formatarea mărimii fișierelor
  const formatBytes = (bytes?: string) => {
    if (!bytes) return "--";
    const b = parseInt(bytes, 10);
    if (b < 1024) return b + " B";
    else if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    else return (b / 1048576).toFixed(1) + " MB";
  };

  // Funcție ajutătoare pentru a alege un emoji în funcție de tipul fișierului
  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes("document")) return "📄";
    if (mimeType.includes("spreadsheet")) return "📊";
    if (mimeType.includes("presentation")) return "🖥️";
    if (mimeType.includes("pdf")) return "📕";
    if (mimeType.includes("folder")) return "📁";
    if (mimeType.includes("colaboratory")) return "📓"; // Pentru Jupyter Notebooks
    return "📄";
  };

  // Funcție ajutătoare pentru a traduce mimeType-ul într-un text citibil
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
    
    // Fallback pt tipuri necunoscute (extrage extensia)
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
        // 1. Verificăm dacă serverul Python trăiește
        const healthRes = await fetch("http://localhost:8000/health");
        if (healthRes.ok) {
          setApiStatus("connected");

          // 2. Verificăm dacă utilizatorul a finalizat logarea cu Google
          const statusRes = await fetch("http://localhost:8000/api/status");
          const statusData = await statusRes.json();

          const newlyConnected = statusData.is_connected;

          // Dacă abia acum ne-am conectat și nu avem fișiere, le cerem
          if (newlyConnected && !isConnected) {
            setIsConnected(true);
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

    // Funcția care aduce efectiv lista de fișiere
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

    // Verificăm statusul imediat, apoi la fiecare 3 secunde 
    // (ideal pentru a prinde momentul când te întorci din browser)
    checkStatus();
    intervalId = setInterval(checkStatus, 3000);

    return () => clearInterval(intervalId);
  }, [isConnected]); // Dependență pe isConnected pentru a nu face fetch la infinit

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

          {/* Dashboard Grid */}
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
                    <span className="sub-text">AI will automatically analyze and organize them.</span>
                  </>
                ) : isLoadingFiles ? (
                  <div className="loading-spinner">Analyzing Drive...</div>
                ) : (
                  <ul className="file-list">
                    {files.map((file) => (
                      <li key={file.id} className="file-item">
                        <span className="file-icon">{getFileIcon(file.mimeType)}</span>
                        <div className="file-details">
                          <div className="file-name">{file.name}</div>
                          <span className="file-meta">
                            <span style={{color: "rgba(255,255,255,0.7)", fontWeight: 500}}>{getReadableFileType(file.mimeType)}</span> • {formatBytes(file.size)} • Modified {new Date(file.modifiedTime).toLocaleDateString()}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* AI Chat Placeholder */}
            <div className="panel ai-panel glass-panel">
              <div className="panel-header">
                <h3>SmartClean Assistant</h3>
              </div>
              <div className="chat-content">
                <div className="chat-bubble ai">
                  {isConnected
                    ? `I've found ${files.length} recent files in your Drive. Tell me what kind of clutter you want to clean up today!`
                    : "Hello! I'm your SmartClean AI. Connect your Google Drive and I'll help you find duplicates and free up space."}
                </div>
              </div>
              <div className="chat-input-area">
                <input
                  type="text"
                  className="macos-input"
                  placeholder={isConnected ? "e.g., Delete all PDFs older than 2 years..." : "Connect Drive to chat..."}
                  disabled={!isConnected}
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
