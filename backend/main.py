import os
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from dotenv import load_dotenv

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

# Scope-ul ca string simplu
SCOPES = 'https://www.googleapis.com/auth/drive'

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "API is running"}

@app.get("/auth/login")
async def login():
    """
    Generates the Google OAuth 2.0 URL manually to bypass strict state checks.
    """
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
    """
    Exchanges the code for a token directly via Google's token endpoint using httpx.
    """
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
        print("\n" + "="*50)
        print("🔥 SUCCES! AM OBȚINUT TOKEN-UL:")
        print("Access Token:", token_data["access_token"])
        if "refresh_token" in token_data:
            print("Refresh Token:", token_data["refresh_token"])
        print("="*50 + "\n")
        
        return HTMLResponse(
            content="""
            <div style="font-family: sans-serif; text-align: center; margin-top: 100px;">
                <h1 style="color: #4CAF50;">✅ Authentication successful!</h1>
                <p>You can close this tab and return to SmartClean.</p>
            </div>
            """
        )
    else:
        # Dacă apare o eroare de la Google, o vom printa clar în browser
        print("Error fetching token:", token_data)
        return HTMLResponse(content=f"<h1>❌ Error from Google:</h1><p>{token_data}</p>")