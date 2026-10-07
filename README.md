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

**SmartClean** is a modern, AI-driven macOS desktop application designed to solve cloud storage and inbox clutter. Instead of clicking through clunky filters and endless dropdowns to find old or heavy files, SmartClean introduces a **Text-to-Action** paradigm. You simply tell the AI what to delete, and it handles the complex API queries for you.

Wrapped in a beautiful, native-feeling macOS "liquid glass" UI, SmartClean acts as a smart intermediary between your natural language intentions and the Google Drive and Gmail APIs.

---

## 🚀 Features

*   **🤖 Text-to-Action AI:** Type commands like *"Find and delete all mp3 files older than 2023"* or *"Delete all promotional emails from last month."* The integrated **Google Gemini 3.5 Flash** LLM translates your prompt into precise Google Drive and Gmail API queries.
*   **🔑 Bring Your Own Key (BYOK):** Completely privacy-first and open-source friendly. No central backend API key or subscription required. You supply your own free Gemini API key, stored locally in your client and scoped per connected Google account.
*   **🛡️ Safety First:** SmartClean never deletes anything automatically. It performs a dry run, displays targeted files in a clean UI for your review, and requires manual confirmation before moving files to the Trash.
*   **⚡ Smart Batching:** Safely handles rate-limits and large operations by paginating API requests (e.g., deleting files in batches to respect Google's limits).
*   **🔐 Secure Architecture:** Uses OAuth 2.0. Authentication tokens are handled securely, and users can revoke app access at any time. The Python backend is compiled into a standalone, secure binary sidecar using PyInstaller.
*   **📧 Dual-Agent Seamless Toggle:** Instantly switch between managing Google Drive files and Gmail messages from a unified, premium dashboard. The AI will even automatically switch the view for you depending on your prompt.
*   **💎 Native macOS Feel:** Built with Tauri, featuring a frameless window, transparent title bars, and a heavily optimized Glassmorphism UI that beautifully blurs your actual desktop wallpaper using `window-vibrancy`.

---

## 🛠️ Tech Stack

This project uses a decoupled, highly performant full-stack architecture:

### Frontend (Desktop Client)
*   **Framework:** React 19 + TypeScript + Vite
*   **Desktop Engine:** Tauri 2.0 (Rust-based, incredibly lightweight compared to Electron)
*   **Icons:** Lucide React
*   **Styling:** Custom CSS3 with advanced `backdrop-filter` for native OS-level glassmorphism.

### Backend (AI & API Gateway Sidecar)
*   **Framework:** FastAPI (Python) - highly performant, async-ready backend.
*   **Bundling:** PyInstaller (compiles backend into a native macOS ARM64 / x86_64 binary sidecar).
*   **Authentication:** Google OAuth 2.0 (`google-auth`, `google-api-python-client`).
*   **AI Integration:** Google Gemini 3.5 Flash (`google-genai`) powered via dynamic client-side BYOK requests (`x-gemini-key` header).

---

## 📦 Installation (For End Users)

The easiest way to start using SmartClean is to simply download the pre-compiled application:

1. Go to the [Releases](https://github.com/saftanoel/smartclean-app/releases) page.
2. Download the latest `.dmg` or `.app.zip` file for macOS.
3. Open the `.dmg` and drag **SmartClean** to your Applications folder.
4. Open the app and connect your Google Account.
5. In **Settings** (or when prompted by the assistant in chat), paste your free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## 💻 Local Development (For Developers)

If you want to contribute, modify the code, or build the app from source, follow these steps:

### Prerequisites

Since this is a Tauri application, you will need to have both frontend and backend environments set up on your machine:

1. **Node.js** (v18 or higher) - [Download here](https://nodejs.org/)
2. **Rust & Cargo** - [Install via rustup](https://rustup.rs/)
3. **Python** (3.9+) - for backend development
4. **Xcode Command Line Tools** - required on macOS:
   ```bash
   xcode-select --install
   ```

---

### Step-by-Step Setup

#### 1. Clone the repository
```bash
git clone https://github.com/saftanoel/smartclean.git
cd smartclean
```

#### 2. Setup Python Backend
Create a virtual environment and install dependencies:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configure Google OAuth Credentials
Create or edit `backend/core_secrets.py` with your Google Cloud OAuth 2.0 credentials:
```python
CLIENT_ID = "your_client_id.apps.googleusercontent.com"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI = "http://localhost:14201/auth/callback"
```

> **Google Cloud Console Settings:**
> - Ensure your OAuth 2.0 Client ID is set to **Web application**.
> - Add `http://localhost:14201/auth/callback` to **Authorized redirect URIs**.
> - Enable the **Google Drive API** and **Gmail API** in your Google Cloud Project.
>
> **No Backend Gemini Key Needed:**
> SmartClean uses a Bring Your Own Key (BYOK) architecture. You do not need to configure any Gemini API key in the backend.

#### 4. Build the Backend Sidecar (Required for Tauri)
From the `backend` directory (with the virtual environment activated), compile the Python binary:
```bash
pyinstaller --onefile main.py

# For Apple Silicon (M1/M2/M3/M4):
cp dist/main ../frontend/src-tauri/binaries/main-aarch64-apple-darwin
chmod +x ../frontend/src-tauri/binaries/main-aarch64-apple-darwin

# For Intel Macs (x86_64):
# cp dist/main ../frontend/src-tauri/binaries/main-x86_64-apple-darwin
# chmod +x ../frontend/src-tauri/binaries/main-x86_64-apple-darwin
```

#### 5. Install Frontend Dependencies & Start Dev Server
Navigate to the `frontend` directory and launch the Tauri app:
```bash
cd ../frontend
npm install
npm run tauri dev
```

#### 6. Connect & Add Your Gemini API Key
1. Once the application opens, click **Connect Google Drive** to authenticate.
2. Navigate to **Settings** and paste your free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
3. Start managing your files and inbox using natural language!
