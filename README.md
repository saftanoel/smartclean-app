# ✨ SmartClean

<p align="left">
  <img src="https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0" alt="macOS" />
  <img src="https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB" alt="React" />
  <img src="https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/vite-%23646CFF.svg?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/tauri-%2324C8DB.svg?style=for-the-badge&logo=tauri&logoColor=%23FFFFFF" alt="Tauri" />
  <img src="https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white" alt="Rust" />
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white" alt="Google Cloud" />
  <img src="https://img.shields.io/badge/Gemini%20AI-%238E75B2.svg?style=for-the-badge&logo=google&logoColor=white" alt="Gemini AI" />
  <img src="https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3" />
</p>

**SmartClean** is a modern, AI-driven macOS desktop application designed to solve cloud storage clutter. Instead of clicking through clunky filters and endless dropdowns to find old or heavy files, SmartClean introduces a **Text-to-Action** paradigm. You simply tell the AI what to delete, and it handles the complex API queries for you.

Wrapped in a beautiful, native-feeling macOS "liquid glass" UI, SmartClean acts as a smart intermediary between your natural language intentions and the Google Drive API.

---


## 🚀 Features

*   **🤖 Text-to-Action AI:** Type commands like *"Find and delete all mp3 files older than 2023"* or *"Show me all PDF duplicates."* The integrated **Google Gemini 2.5 Flash** LLM translates your prompt into precise Google Drive API queries.
*   **🛡️ Safety First:** SmartClean never deletes anything automatically. It performs a dry run, displays the targeted files in a clean UI for your review, and requires manual confirmation before moving files to the Trash.
*   **⚡ Smart Batching:** Safely handles rate-limits and large operations by paginating API requests (e.g., deleting files in batches to respect Google's limits).
*   **🔐 Secure Architecture:** Uses OAuth 2.0. Authentication tokens are handled securely, and users can revoke app access at any time. The Python backend is compiled into a standalone, secure binary sidecar using PyInstaller.
*   **💎 Native macOS Feel:** Built with Tauri, featuring a frameless window, transparent title bars, and a heavily optimized Glassmorphism UI that beautifully blurs your actual desktop wallpaper using `window-vibrancy`.


## 🛠️ Tech Stack

This project uses a decoupled, highly performant full-stack architecture:

### Frontend (Desktop Client)
*   **Framework:** React + TypeScript + Vite
*   **Desktop Engine:** Tauri 2.0 (Rust-based, incredibly lightweight compared to Electron)
*   **Icons:** Lucide React
*   **Styling:** Custom CSS3 with advanced `backdrop-filter` for native OS-level glassmorphism.

### Backend (AI & API Gateway)
*   **Framework:** FastAPI (Python) - highly performant, async-ready backend.
*   **Bundling:** PyInstaller (compiles backend into a native macOS ARM64 binary sidecar).
*   **Authentication:** Google OAuth 2.0 (`google-auth`, `google-api-python-client`).
*   **AI Integration:** Google Gemini API (`google-genai`) for lightning-fast prompt-to-query translation.

---

## 🚀 Getting Started (Local Development)

Follow these steps to set up and run the **SmartClean** application on your local machine.

### Prerequisites

Since this is a Tauri application, you will need to have both the frontend and backend environments set up on your machine:

1. **Node.js** (v18 or higher) - [Download here](https://nodejs.org/)
2. **Rust** & Cargo - [Download here](https://rustup.rs/)
3. **Python** (3.9+) - for backend development
4. **macOS dependencies** (Xcode Command Line Tools) - if you are building on a Mac:
```bash
xcode-select --install
```

### Installation Steps

**1. Clone the repository**
```bash
git clone https://github.com/saftanoel/smartclean.git
cd smartclean
```

**2. Setup Python Backend**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Install Frontend Dependencies**
Navigate to the `frontend` (or `smartclean`) folder and run:
```bash
cd ../frontend
npm install
```

**4. Configure Environment Variables**
Create a `.env` file in the `backend` folder and add your Google Cloud and Gemini credentials:
```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Note: Never commit your `.env` file to version control. It should be added to `.gitignore`.)*

**5. Build the Backend Sidecar (Required for Tauri)**
From the `backend` directory, inside your virtual environment:
```bash
pyinstaller --onefile main.py
cp dist/main ../frontend/src-tauri/binaries/main-aarch64-apple-darwin
```

**6. Run the Development Server**
Start both the React frontend and the Rust (Tauri) backend simultaneously from the `frontend` directory:
```bash
npm run tauri dev
```
