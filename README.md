# ✨ SmartClean
WORK IN PROGRESS

![macOS](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Tauri](https://img.shields.io/badge/Tauri-FFC131?style=for-the-badge&logo=Tauri&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)

**SmartClean** is a modern, AI-driven macOS desktop application designed to solve cloud storage clutter. Instead of clicking through clunky filters and endless dropdowns to find old or heavy files, SmartClean introduces a **Text-to-Action** paradigm. You simply tell the AI what to delete, and it handles the complex API queries for you.

Wrapped in a beautiful, native-feeling macOS "liquid glass" UI, SmartClean acts as a smart intermediary between your natural language intentions and the Google Drive API.

---

## 🚀 Features

*   **🤖 Text-to-Action AI:** Type commands like *"Find and delete all mp3 files older than 2023"* or *"Show me all PDF duplicates."* The integrated LLM translates your prompt into precise Google Drive API queries.
*   **🛡️ Safety First:** SmartClean never deletes anything automatically. It performs a dry run, displays the targeted files in a clean UI for your review, and requires manual confirmation before moving files to the Trash.
*   **⚡ Smart Batching:** Safely handles rate-limits and large operations by paginating API requests (e.g., deleting files in batches of 100).
*   **🔐 Secure Architecture:** Uses OAuth 2.0. Authentication tokens are handled securely, and users can revoke app access at any time.
*   **💎 Native macOS Feel:** Built with Tauri, featuring a frameless window, transparent title bars, and a heavily optimized Glassmorphism UI that beautifully blurs your actual desktop wallpaper.

---

## 🛠️ Tech Stack

This project uses a decoupled, highly performant full-stack architecture:

### Frontend (Desktop Client)
*   **Framework:** React + Vite
*   **Desktop Engine:** Tauri (Rust-based, incredibly lightweight compared to Electron)
*   **Styling:** Custom CSS with advanced `backdrop-filter` for native OS-level glassmorphism.

### Backend (AI & API Gateway)
*   **Framework:** FastAPI (Python) - highly performant, async-ready backend.
*   **Authentication:** Google OAuth 2.0 (`google-auth`, `google-api-python-client`).
*   **AI Integration:** OpenAI API / Google Gemini API for prompt-to-query translation.

---

## 🚀 Getting Started (Local Development)

Follow these steps to set up and run the **SmartClean** application on your local machine.

### Prerequisites

Since this is a Tauri application, you will need to have both the frontend and backend environments set up on your machine:

1. **Node.js** (v16 or higher) - [Download here](https://nodejs.org/)
2. **Rust** & Cargo - [Download here](https://rustup.rs/)
3. **macOS dependencies** (Xcode Command Line Tools) - if you are building on a Mac:
```bash
xcode-select --install
```

### Installation Steps

**1. Clone the repository**
```bash
git clone [https://github.com/your-username/smartclean.git](https://github.com/your-username/smartclean.git)
cd smartclean
```

**2. Install Frontend Dependencies**
Navigate to the root folder (where `package.json` is located) and run:
```bash
npm install
```

**3. Configure Environment Variables**
Create a `.env` file in the root of the project and add your Google Cloud credentials:
```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```
*(Note: Never commit your `.env` file to version control. It should be added to `.gitignore`.)*

**4. Run the Development Server**
Start both the React frontend and the Rust (Tauri) backend simultaneously:
```bash
npm run tauri dev
```
