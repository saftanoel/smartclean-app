import { useState, useEffect, useRef } from "react";
import { openUrl } from '@tauri-apps/plugin-opener';
import { FileText, Image as ImageIcon, FileSpreadsheet, Presentation, File as FileIcon, Folder, FileArchive, ArrowUpRight, RotateCcw, Search, Cloud, Trash2, LayoutDashboard, Loader2, Settings, ShieldCheck, Bot, Eraser, Palette, Lock } from "lucide-react";
import "./App.css";

type ApiStatus = "checking" | "connected" | "disconnected";

interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: string;
  modifiedTime: string;
  webViewLink?: string;
}

interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
}

const TypewriterText = ({ text, speed = 10 }: { text: string; speed?: number }) => {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    let i = 0;
    setDisplayedText("");
    const intervalId = setInterval(() => {
      setDisplayedText(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(intervalId);
    }, speed);
    
    return () => clearInterval(intervalId);
  }, [text, speed]);

  return <>{displayedText}</>;
};

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [isConnected, setIsConnected] = useState(false);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);


  const [chatInput, setChatInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showEmptyTrashModal, setShowEmptyTrashModal] = useState(false);
  const [isEmptyingTrash, setIsEmptyingTrash] = useState(false);
  const [currentView, setCurrentView] = useState<"dashboard" | "trash" | "settings">("dashboard");
  const [excludedExtensions, setExcludedExtensions] = useState<string>(
    () => localStorage.getItem('excludedExtensions') || ".wav, .flac, .logicx"
  );
  const [searchBatchSize, setSearchBatchSize] = useState<number>(
    () => parseInt(localStorage.getItem('searchBatchSize') || "500", 10)
  );
  const [typewriterSpeed, setTypewriterSpeed] = useState<number>(
    () => parseInt(localStorage.getItem('typewriterSpeed') || "10", 10)
  );
  const [isCompactMode, setIsCompactMode] = useState<boolean>(
    () => localStorage.getItem('isCompactMode') === 'true'
  );
  const [trashFiles, setTrashFiles] = useState<DriveFile[]>([]);
  const [isLoadingTrash, setIsLoadingTrash] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'ai', text: "Hello! I'm your SmartClean AI. Connect your Google Drive and I'll help you find duplicates and free up space." }
  ]);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    localStorage.setItem('excludedExtensions', excludedExtensions);
    localStorage.setItem('searchBatchSize', searchBatchSize.toString());
    localStorage.setItem('typewriterSpeed', typewriterSpeed.toString());
    localStorage.setItem('isCompactMode', isCompactMode.toString());
  }, [excludedExtensions, searchBatchSize, typewriterSpeed, isCompactMode]);

  const formatBytes = (bytes?: string) => {
    if (!bytes) return "--";
    const b = parseInt(bytes, 10);
    if (b < 1024) return b + " B";
    else if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    else return (b / 1048576).toFixed(1) + " MB";
  };

  const getFileIcon = (mimeType: string) => {
    const iconProps = { size: 20, color: "rgba(255, 255, 255, 0.7)" };
    if (mimeType.includes("document")) return <FileText {...iconProps} />;
    if (mimeType.includes("spreadsheet")) return <FileSpreadsheet {...iconProps} />;
    if (mimeType.includes("presentation")) return <Presentation {...iconProps} />;
    if (mimeType.includes("pdf")) return <FileText {...iconProps} />;
    if (mimeType.includes("folder")) return <Folder {...iconProps} />;
    if (mimeType.includes("image")) return <ImageIcon {...iconProps} />;
    if (mimeType.includes("zip") || mimeType.includes("compressed") || mimeType.includes("tar")) return <FileArchive {...iconProps} />;
    return <FileIcon {...iconProps} />;
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


  const handleSendMessage = async () => {
    if (!chatInput.trim() || !isConnected || files.length === 0) return;

    const userText = chatInput;
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setChatInput("");
    setIsThinking(true);
    setSelectedIds([]);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userText, files: files })
      });

      if (res.ok) {
        const data = await res.json();
        
        if (data.new_files && data.new_files.length > 0) {
          setFiles(prev => {
            const existingIds = new Set(prev.map(f => f.id));
            const uniqueNew = data.new_files.filter((f: DriveFile) => !existingIds.has(f.id));
            return [...uniqueNew, ...prev];
          });
        }
        
        setSelectedIds(data.selected_ids || []);
        setMessages(prev => [...prev, { sender: 'ai', text: data.reply }]);
      } else {
        setMessages(prev => [...prev, { sender: 'ai', text: "Eroare: Nu am putut procesa comanda." }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { sender: 'ai', text: "Eroare de conexiune cu serverul." }]);
    } finally {
      setIsThinking(false);
    }
  };

  const executeEmptyTrash = async () => {
    setShowEmptyTrashModal(false);
    setIsEmptyingTrash(true);

    try {
      const res = await fetch("http://localhost:8000/api/trash/empty", {
        method: "DELETE"
      });

      if (res.ok) {
        setTrashFiles([]);
        setMessages(prev => [...prev, { sender: 'ai', text: "✅ Trash emptied permanently!" }]);
      } else {
        setMessages(prev => [...prev, { sender: 'ai', text: "Error: Could not empty trash." }]);
      }
    } catch (error) {
      console.error("Error emptying trash:", error);
      setMessages(prev => [...prev, { sender: 'ai', text: "Connection error while emptying trash." }]);
    } finally {
      setIsEmptyingTrash(false);
    }
  };

  const executeDelete = async () => {
    if (selectedIds.length === 0) return;
    setShowConfirmModal(false);
    setIsDeleting(true);

    try {
      const res = await fetch("http://localhost:8000/api/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: selectedIds })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { sender: 'ai', text: `✅ Done! Moved ${data.deleted_count} files to Trash.` }]);
        setSelectedIds([]);


        const fetchRes = await fetch("http://localhost:8000/api/files");
        if (fetchRes.ok) {
          const fileData = await fetchRes.json();
          setFiles(fileData.files);
        }
      } else {
        setMessages(prev => [...prev, { sender: 'ai', text: "Error: Could not trash the files." }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { sender: 'ai', text: "Connection error during delete." }]);
    } finally {
      setIsDeleting(false);
    }
  };

  const fetchTrashFiles = async () => {
    setIsLoadingTrash(true);
    try {
      const res = await fetch("http://localhost:8000/api/trash");
      if (res.ok) {
        const data = await res.json();
        setTrashFiles(data.files);
      }
    } catch (error) {
      console.error("Eroare la aducerea fisierelor din trash:", error);
    } finally {
      setIsLoadingTrash(false);
    }
  };

  const handleRestoreFile = async (fileId: string) => {
    try {
      const res = await fetch("http://localhost:8000/api/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: [fileId] })
      });

      if (res.ok) {
        setTrashFiles(prev => prev.filter(f => f.id !== fileId));
        const fetchRes = await fetch("http://localhost:8000/api/files");
        if (fetchRes.ok) {
          const fileData = await fetchRes.json();
          setFiles(fileData.files);
        }
      }
    } catch (error) {
      console.error("Connection error during restore:", error);
    }
  };

  const toggleFileSelection = (fileId: string) => {
    setSelectedIds(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId) 
        : [...prev, fileId]
    );
  };

  const displayedFiles = files
    .filter(f => f.name.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => {
      const aSelected = selectedIds.includes(a.id);
      const bSelected = selectedIds.includes(b.id);
      
      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      return 0;
    });

  return (
    <div className="macos-window">
      {showConfirmModal && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <h3>⚠️ Confirm Trash</h3>
            <p>Are you sure you want to move {selectedIds.length} items to the trash?</p>
            <div className="modal-actions">
              <button className="macos-button secondary" onClick={() => setShowConfirmModal(false)}>Cancel</button>
              <button className="macos-button danger" onClick={executeDelete}>Yes, Trash Them</button>
            </div>
          </div>
        </div>
      )}

      {showEmptyTrashModal && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <h3>⚠️ Empty Trash</h3>
            <p>Are you sure you want to permanently delete all {trashFiles.length} files in the trash bin? This action cannot be undone.</p>
            <div className="modal-actions">
              <button className="macos-button secondary" onClick={() => setShowEmptyTrashModal(false)}>Cancel</button>
              <button className="macos-button danger" onClick={executeEmptyTrash}>Yes, Empty Trash</button>
            </div>
          </div>
        </div>
      )}


      <div data-tauri-drag-region className="mac-drag-region"></div>
      <div className="app-layout">

        <nav className="sidebar glass-panel">
          <div className="sidebar-header">
            <h1 className="app-title">SmartClean</h1>
          </div>

          <ul className="nav-menu">
            <li
              className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentView("dashboard")}
            >
              <LayoutDashboard size={16} /> Dashboard
            </li>
            <li
              className={`nav-item ${currentView === 'trash' ? 'active' : ''}`}
              onClick={() => {
                setCurrentView("trash");
                fetchTrashFiles();
              }}
            >
              <Trash2 size={16} /> Trash Bin
            </li>
            <li
              className={`nav-item ${currentView === 'settings' ? 'active' : ''}`}
              onClick={() => setCurrentView("settings")}
            >
              <Settings size={16} /> Settings
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


        <main className="main-area">
          <header className="top-bar">
            <div className="breadcrumbs">
              <h2>{currentView === 'dashboard' ? "Overview" : currentView === 'trash' ? "Trash Bin" : "Settings"}</h2>
              <span className="subtitle">{currentView === 'dashboard' ? "Dashboard" : currentView === 'trash' ? "Deleted Files" : "Preferences"}</span>
            </div>

            {!isConnected ? (
              <button
                className="macos-button connect-button"
                onClick={async () => await openUrl('http://localhost:8000/auth/login')}
              >
                <span className="icon"><Cloud size={16} /></span>
                Connect to Drive
              </button>
            ) : (
              <div className="connected-badge">
                <span className="status-dot connected"></span>
                Drive Synced
              </div>
            )}
          </header>

          {currentView === 'settings' ? (
            <div className="settings-panel">
              <div className="settings-card glass-panel">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><ShieldCheck size={18} /> Drive & Safety Settings</h3>
                <div className="setting-row">
                  <label>Excluded Extensions</label>
                  <input type="text" className="macos-input" value={excludedExtensions} onChange={e => setExcludedExtensions(e.target.value)} />
                </div>
                <div className="setting-row">
                  <label>Global Search Limit ({searchBatchSize} items)</label>
                  <input type="range" min="100" max="1000" step="50" value={searchBatchSize} onChange={e => setSearchBatchSize(parseInt(e.target.value))} />
                </div>
              </div>
              
              <div className="settings-card glass-panel">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Bot size={18} /> AI & Chat Preferences</h3>
                <div className="setting-row">
                  <label>Typewriter Effect Speed ({typewriterSpeed}ms)</label>
                  <input type="range" min="5" max="50" step="1" value={typewriterSpeed} onChange={e => setTypewriterSpeed(parseInt(e.target.value))} />
                </div>
                <div className="setting-row">
                  <button className="macos-button" onClick={() => setMessages([])}>
                    <Eraser size={14} /> Clear Chat History
                  </button>
                </div>
              </div>

              <div className="settings-card glass-panel">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Palette size={18} /> UI & Appearance</h3>
                <div className="setting-row" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                  <input type="checkbox" id="compactMode" checked={isCompactMode} onChange={e => setIsCompactMode(e.target.checked)} />
                  <label htmlFor="compactMode">Compact List Density</label>
                </div>
              </div>

              <div className="settings-card glass-panel">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Lock size={18} /> Account & Data</h3>
                <button className="danger-button" style={{ width: 'fit-content', display: 'flex', alignItems: 'center', gap: '6px' }} onClick={() => {
                   setIsConnected(false);
                   setFiles([]);
                   setTrashFiles([]);
                   setMessages([{ sender: 'ai', text: "Session disconnected." }]);
                }}>Disconnect Google Drive</button>
              </div>
            </div>
          ) : (
          <div className="dashboard-grid">

            <div className="panel files-panel glass-panel">
              <div className="panel-header">
                <h3>{currentView === 'dashboard' ? "Recent Files" : "Trash Bin"}</h3>
                <div className="header-actions">
                  <span className="panel-badge">{currentView === 'dashboard' ? files.length : trashFiles.length} items</span>
                  {currentView === 'dashboard' && selectedIds.length > 0 && (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="shadcn-button secondary" onClick={() => setSelectedIds([])}>Clear</button>
                      <button
                        className="danger-button"
                        onClick={() => setShowConfirmModal(true)}
                        disabled={isDeleting}
                      >
                        {isDeleting ? <><Loader2 className="spin-animation" size={16} /> Trashing...</> : <><Trash2 size={16} /> Trash {selectedIds.length} Items</>}
                      </button>
                    </div>
                  )}
                  {currentView === 'trash' && trashFiles.length > 0 && (
                    <button
                      className="danger-button"
                      onClick={() => setShowEmptyTrashModal(true)}
                      disabled={isEmptyingTrash}
                    >
                      {isEmptyingTrash ? <><Loader2 className="spin-animation" size={16} /> Emptying...</> : <><Trash2 size={16} /> Empty Trash</>}
                    </button>
                  )}
                </div>
              </div>

              <div className={`panel-content ${!isConnected ? 'empty-state' : ''}`}>
                {!isConnected ? (
                  <>
                    <div className="empty-icon">🗂️</div>
                    <p>Connect your drive to see files</p>
                  </>
                ) : (currentView === 'dashboard' ? isLoadingFiles : isLoadingTrash) ? (
                  <div className="loading-spinner">{currentView === 'dashboard' ? "Analyzing Drive..." : "Loading Trash..."}</div>
                ) : currentView === 'dashboard' ? (
                  <>
                    <div className="search-bar-container">
                      <span className="search-icon"><Search size={16} /></span>
                      <input
                        type="text"
                        className="search-input macos-input"
                        placeholder="Search files..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </div>
                    <ul className="file-list">
                      {displayedFiles.map((file) => {

                        const isSelected = selectedIds.includes(file.id);

                        return (
                          <li 
                            key={file.id} 
                            className={`file-item ${isSelected ? 'selected-by-ai' : ''} ${isCompactMode ? 'compact' : ''}`}
                            onClick={() => toggleFileSelection(file.id)}
                          >
                            <span className="file-icon">{getFileIcon(file.mimeType)}</span>
                            <div className="file-details">
                              <div className="file-name">{file.name}</div>
                              <span className="file-meta">
                                <span style={{ color: "rgba(255,255,255,0.7)", fontWeight: 500 }}>{getReadableFileType(file.mimeType)}</span> • {formatBytes(file.size)} • Modified {new Date(file.modifiedTime).toLocaleDateString()}
                              </span>
                            </div>
                            <div className="file-actions">
                              {file.webViewLink && (
                                <button
                                  className="shadcn-icon-button"
                                  onClick={(e) => { e.stopPropagation(); openUrl(file.webViewLink!); }}
                                  title="Open in Browser"
                                >
                                  <ArrowUpRight size={16} strokeWidth={2.5} />
                                </button>
                              )}
                              {isSelected && <span className="selection-badge">✓ Selected</span>}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </>
                ) : (
                  <ul className="file-list">
                    {trashFiles.map((file) => (
                      <li key={file.id} className={`file-item ${isCompactMode ? 'compact' : ''}`}>
                        <span className="file-icon">{getFileIcon(file.mimeType)}</span>
                        <div className="file-details">
                          <div className="file-name">{file.name}</div>
                          <span className="file-meta">
                            <span style={{ color: "rgba(255,255,255,0.7)", fontWeight: 500 }}>{getReadableFileType(file.mimeType)}</span> • {formatBytes(file.size)} • Modified {new Date(file.modifiedTime).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="file-actions">
                          <button
                            className="shadcn-button secondary"
                            onClick={(e) => { e.stopPropagation(); handleRestoreFile(file.id); }}
                          >
                            <RotateCcw size={14} /> Restore
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>


            <div className="panel ai-panel glass-panel">
              <div className="panel-header">
                <h3>SmartClean Assistant (Gemini 3.5 Flash)</h3>
                <button 
                  className="shadcn-icon-button clear-chat-btn"
                  onClick={() => {
                    setMessages([{ sender: 'ai', text: "Hello! I'm your SmartClean AI. Connect your Google Drive and I'll help you find duplicates and free up space." }]);
                    setSelectedIds([]);
                  }}
                  title="Clear Chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <div className="chat-content">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`chat-bubble ${msg.sender}`}>
                    {msg.sender === 'ai' ? <TypewriterText text={msg.text} speed={typewriterSpeed} /> : msg.text}
                  </div>
                ))}
                {isThinking && (
                  <div className="chat-bubble ai thinking">
                    Thinking<span className="dots">...</span>
                  </div>
                )}
                <div ref={chatEndRef} />
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
          )}
        </main>
      </div>
    </div>
  );
}

export default App;