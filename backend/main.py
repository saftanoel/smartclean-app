import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from dotenv import load_dotenv

# Importurile noi pentru Google Drive API
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

load_dotenv()

app = FastAPI(title="SmartClean API")

# Configure CORS for Tauri frontend
origins = [
    "http://localhost:1420",
    "tauri://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
SCOPES = 'https://www.googleapis.com/auth/drive'

# Aici vom stoca token-ul in memorie (fiind aplicatie locala desktop, o variabila globala e de ajuns momentan)
SESSION_STORE = {}

@app.get("/health")
async def health_check():
    return {"status": "API is running"}

# --- NOU: Endpoint ca React-ul să știe dacă suntem conectați ---
@app.get("/api/status")
async def api_status():
    is_connected = "default_user" in SESSION_STORE
    return {"is_connected": is_connected}

@app.get("/auth/login")
async def login():
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={SCOPES}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def callback(code: str):
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)
        token_data = response.json()
        
    if "access_token" in token_data:
        # SALVĂM TOKEN-UL ÎN MEMORIE
        SESSION_STORE["default_user"] = token_data["access_token"]
        
        print("\n✅ Token salvat in sesiune cu succes!\n")
        
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SmartClean - Connected</title>
            <style>
                body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #121212; background-image: radial-gradient(circle at 50% 0%, #2a2a35 0%, #121212 70%); height: 100vh; display: flex; align-items: center; justify-content: center; color: #ffffff; }
                .glass-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; padding: 40px 50px; text-align: center; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5); max-width: 400px; animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
                .icon { font-size: 48px; margin-bottom: 20px; display: inline-block; animation: scaleIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both; }
                h1 { margin: 0 0 10px 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }
                p { margin: 0; color: #a0a0a5; font-size: 15px; line-height: 1.5; }
                .sub-text { margin-top: 25px; font-size: 13px; color: #666; }
                @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                @keyframes scaleIn { from { transform: scale(0.5); opacity: 0; } to { transform: scale(1); opacity: 1; } }
            </style>
        </head>
        <body>
            <div class="glass-card">
                <div class="icon">✨</div>
                <h1>Connected to Drive</h1>
                <p>Authentication was successful. Your account is now safely linked.</p>
                <div class="sub-text">You can close this tab and return to SmartClean.</div>
            </div>
            <script>setTimeout(() => { window.close(); }, 3500);</script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content=f"<h1>❌ Error from Google:</h1><p>{token_data}</p>")

# --- NOU: Endpoint-ul care aduce efectiv fisierele din Drive ---
@app.get("/api/files")
async def get_files():
    token = SESSION_STORE.get("default_user")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")
        
    try:
        # Construim credentialele din token-ul salvat
        creds = Credentials(token=token)
        
        # Ne conectam la API-ul Google Drive v3
        service = build('drive', 'v3', credentials=creds)
        
        # Facem query-ul: Luam cele mai recente 15 fisiere care NU sunt in Trash
        results = service.files().list(
            pageSize=150,
            fields="files(id, name, mimeType, size, modifiedTime)",
            orderBy="modifiedTime desc",
            q="trashed = false"
        ).execute()
        
        items = results.get('files', [])
        return {"files": items}
        
    except Exception as e:
        print(f"Eroare la aducerea fisierelor: {e}")
        raise HTTPException(status_code=500, detail=str(e))