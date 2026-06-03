from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "API is running"}

@app.get("/auth/login")
async def login():
    """
    Placeholder endpoint for Google OAuth login.
    Currently returns a dummy redirect URL string.
    """
    # In the future, this will generate the Google OAuth authorization URL and redirect the user.
    dummy_redirect_url = "https://accounts.google.com/o/oauth2/v2/auth?dummy=true"
    return {"redirect_url": dummy_redirect_url}
