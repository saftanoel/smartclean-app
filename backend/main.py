import os
import asyncio
import httpx
import json
import re
import base64 
import uvicorn
import time
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import sys

# Cooldown cache for failed/unavailable models to avoid cascade delays
MODEL_COOLDOWN_UNTIL: dict[str, float] = {}
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None
try:
    from core_secrets import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
except ImportError:
    CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:14201/auth/callback")

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

SCOPES = 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/userinfo.email openid email'

SESSION_STORE = {}

async def fetch_user_email(token: str) -> str:
    # 1. Drive API about
    try:
        creds = Credentials(token=token)
        service = build('drive', 'v3', credentials=creds)
        about = await asyncio.to_thread(lambda: service.about().get(fields="user(emailAddress)").execute())
        email = about.get('user', {}).get('emailAddress')
        if email:
            return email
    except Exception as e:
        print(f"Drive about email fetch failed: {e}")

    # 2. Gmail API profile
    try:
        creds = Credentials(token=token)
        service = build('gmail', 'v1', credentials=creds)
        profile = await asyncio.to_thread(lambda: service.users().getProfile(userId='me').execute())
        email = profile.get('emailAddress')
        if email:
            return email
    except Exception as e:
        print(f"Gmail profile email fetch failed: {e}")

    # 3. Google userinfo
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code == 200:
                data = res.json()
                if "email" in data:
                    return data["email"]
    except Exception as e:
        print(f"Userinfo email fetch failed: {e}")

    return ""

@app.get("/health")
async def health_check():
    return {"status": "API is running"}

@app.get("/api/status")
async def api_status():
    token = SESSION_STORE.get("default_user")
    is_connected = bool(token)
    user_email = SESSION_STORE.get("user_email")
    if is_connected and not user_email:
        user_email = await fetch_user_email(token)
        if user_email:
            SESSION_STORE["user_email"] = user_email
    return {
        "is_connected": is_connected,
        "user_email": user_email or ""
    }

@app.post("/api/logout")
async def logout():
    SESSION_STORE.clear()
    return {"message": "Logged out successfully"}

@app.get("/auth/login")
async def login():
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={SCOPES.replace(' ', '%20')}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def callback(code: str):
    try:
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(token_url, data=payload)
            token_data = response.json()
            
        if "access_token" in token_data:
            SESSION_STORE["default_user"] = token_data["access_token"]
            print("\nToken salvat in sesiune cu succes!\n")
            
            user_email = ""
            if "id_token" in token_data:
                try:
                    payload_part = token_data["id_token"].split(".")[1]
                    padded = payload_part + "=" * ((4 - len(payload_part) % 4) % 4)
                    jwt_data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                    if "email" in jwt_data:
                        user_email = jwt_data["email"]
                except Exception as e:
                    print(f"Error parsing id_token: {e}")
                    
            if not user_email:
                user_email = await fetch_user_email(token_data["access_token"])
                
            if user_email:
                SESSION_STORE["user_email"] = user_email
                print(f"User email identificat: {user_email}")
            
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
                    h1 { margin: 0 0 10px 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }
                    p { margin: 0; color: #a0a0a5; font-size: 15px; line-height: 1.5; }
                    .sub-text { margin-top: 25px; font-size: 13px; color: #666; }
                    @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                </style>
            </head>
            <body>
                <div class="glass-card">
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
            return HTMLResponse(content=f"<h1>Error from Google:</h1><p>{token_data}</p>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Python Backend Error:</h1><p>{str(e)}</p>")

@app.get("/api/files")
async def get_files():
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")
        
    try:
        creds = Credentials(token=token)
        service = build('drive', 'v3', credentials=creds)
        
        # NOU: Am adaugat 'thumbnailLink' la fields!
        results = await asyncio.to_thread(
            lambda: service.files().list(
                pageSize=500,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink, thumbnailLink)",
                orderBy="modifiedTime desc",
                q="trashed = false"
            ).execute()
        )
        
        items = results.get('files', [])
        return {"files": items}
        
    except Exception as e:
        print(f"Eroare la aducerea fisierelor: {e}")
        # Daca token-ul este expirat/invalid, il stergem din sesiune
        if "default_user" in SESSION_STORE:
            del SESSION_STORE["default_user"]
        raise HTTPException(status_code=401, detail="Token expirat sau invalid")


def is_complex_task(prompt: str) -> bool:
    if not prompt:
        return False
    if len(prompt) > 120:
        return True
    keywords = [
        "analyze", "organize", "compare", "duplicate", "summarize",
        "group", "cleanup plan", "unsubscribe", "archive", "filter by multiple",
        "analizeaza", "organizeaza", "compar", "older than", "newer than", "before", "after", "mai vechi"
    ]
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in keywords)

def is_romanian(text: str) -> bool:
    if not text:
        return False
    ro_words = {
        "poti", "sa", "le", "acum", "toate", "fisierele", "te", "rog", "salut",
        "multumesc", "da", "nu", "si", "in", "pe", "pentru", "debifeaza", "deselecteaza",
        "deselectezi", "curata", "sterge", "aratami", "arata", "bifeaza", "selectate", "tot"
    }
    tokens = set(re.findall(r'\b[a-zA-ZăâîșțĂÂÎȘȚ]+\b', text.lower()))
    return bool(tokens & ro_words)

def is_deselect_request(prompt: str) -> bool:
    if not prompt:
        return False
    p = prompt.strip().lower()
    keywords = [
        "deselect", "deselecteaza", "deselectezi", "deselectati", "deselectioneaza",
        "unselect", "uncheck", "debifeaza", "debifare", "clear selection",
        "anuleaza selectia", "sterge selectia", "reset selection", "goleste selectia"
    ]
    return any(kw in p for kw in keywords)

def match_local_file_type_filter(prompt: str, files: list) -> Optional[dict]:
    """Instant local fast-path (<10ms) for simple file-type selection queries without date/size/complex filters."""
    if not prompt or not files:
        return None
    p = prompt.strip().lower()

    # If date, size, or complex conditions exist, return None so Gemini handles it accurately
    condition_patterns = [
        r'\b(older|newer|before|after|since|until|between|during|from)\b',
        r'\b(mai vechi|mai nou|inainte|dupa|din)\b',
        r'\b(larger|smaller|bigger|more than|less than|over|under|peste|sub|mai mare|mai mic)\b',
        r'\b(\d+\s*(mb|gb|kb|megabytes|gigabytes))\b',
        r'\b(20[0-2][0-9])\b',
        r'\b(duplicate|duplicat|blurry|neclar|similar|burst|containing|numit|named)\b',
    ]
    for pattern in condition_patterns:
        if re.search(pattern, p):
            return None

    # Check for selection/find intent
    select_intent = any(w in p for w in [
        "select", "selecteaza", "alege", "bifeaza", "toate", "all", "fisiere", "files", "show", "get", "gaseste"
    ])
    if not select_intent:
        return None

    is_ro = is_romanian(p)

    # 1. PDFs
    pdf_keywords = ["pdf", "pdfs", "pdf-uri", "pdf-urile", "documente pdf"]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', p) for kw in pdf_keywords):
        matching = [
            f for f in files
            if f.get("mimeType") == "application/pdf" or f.get("name", "").lower().endswith(".pdf")
        ]
        label_ro = "fișiere PDF"
        label_en = "PDF files"
        matching_ids = [f["id"] for f in matching if f.get("id")]
        reply = (
            f"Am selectat toate cele {len(matching_ids)} {label_ro} din listă."
            if is_ro
            else f"Selected all {len(matching_ids)} {label_en} found in the list."
        ) if matching_ids else (
            f"Nu am găsit niciun {label_ro} în lista curentă."
            if is_ro
            else f"No {label_en} found in the current list."
        )
        return {
            "reply": reply,
            "selected_ids": matching_ids,
            "drive_query": None,
            "target_platform": "drive",
            "new_files": [],
            "model_used": "instant-local"
        }

    # 2. Audio / Music
    audio_keywords = ["music", "muzica", "audio", "melodii", "melodiile", "song", "songs", "mp3"]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', p) for kw in audio_keywords):
        audio_exts = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma')
        matching = [
            f for f in files
            if f.get("mimeType", "").startswith("audio/") or f.get("name", "").lower().endswith(audio_exts)
        ]
        label_ro = "fișiere audio / melodii"
        label_en = "audio files / music"
        matching_ids = [f["id"] for f in matching if f.get("id")]
        reply = (
            f"Am selectat toate cele {len(matching_ids)} {label_ro} din listă."
            if is_ro
            else f"Selected all {len(matching_ids)} {label_en} found in the list."
        ) if matching_ids else (
            f"Nu am găsit {label_ro} în lista curentă."
            if is_ro
            else f"No {label_en} found in the current list."
        )
        return {
            "reply": reply,
            "selected_ids": matching_ids,
            "drive_query": None,
            "target_platform": "drive",
            "new_files": [],
            "model_used": "instant-local"
        }

    # 3. Images / Photos
    image_keywords = ["image", "images", "photo", "photos", "picture", "pictures", "poze", "pozele", "imagini", "imaginile", "fotografii", "fotografiile"]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', p) for kw in image_keywords):
        img_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.tiff', '.raw', '.svg')
        matching = [
            f for f in files
            if f.get("mimeType", "").startswith("image/") or f.get("name", "").lower().endswith(img_exts)
        ]
        label_ro = "imagini / fotografii"
        label_en = "images / photos"
        matching_ids = [f["id"] for f in matching if f.get("id")]
        reply = (
            f"Am selectat toate cele {len(matching_ids)} {label_ro} din listă."
            if is_ro
            else f"Selected all {len(matching_ids)} {label_en} found in the list."
        ) if matching_ids else (
            f"Nu am găsit {label_ro} în lista curentă."
            if is_ro
            else f"No {label_en} found in the current list."
        )
        return {
            "reply": reply,
            "selected_ids": matching_ids,
            "drive_query": None,
            "target_platform": "drive",
            "new_files": [],
            "model_used": "instant-local"
        }

    # 4. Videos
    video_keywords = ["video", "videos", "movie", "movies", "videoclipuri", "videoclipurile", "filme", "filmele", "mp4"]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', p) for kw in video_keywords):
        vid_exts = ('.mp4', '.mkv', '.mov', '.avi', '.wmv', '.webm', '.m4v')
        matching = [
            f for f in files
            if f.get("mimeType", "").startswith("video/") or f.get("name", "").lower().endswith(vid_exts)
        ]
        label_ro = "videoclipuri"
        label_en = "videos"
        matching_ids = [f["id"] for f in matching if f.get("id")]
        reply = (
            f"Am selectat toate cele {len(matching_ids)} {label_ro} din listă."
            if is_ro
            else f"Selected all {len(matching_ids)} {label_en} found in the list."
        ) if matching_ids else (
            f"Nu am găsit {label_ro} în lista curentă."
            if is_ro
            else f"No {label_en} found in the current list."
        )
        return {
            "reply": reply,
            "selected_ids": matching_ids,
            "drive_query": None,
            "target_platform": "drive",
            "new_files": [],
            "model_used": "instant-local"
        }

    # 5. Archives
    archive_keywords = ["archive", "archives", "arhive", "arhivele", "zip", "rar", "7z"]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', p) for kw in archive_keywords):
        arch_exts = ('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2')
        matching = [
            f for f in files
            if f.get("name", "").lower().endswith(arch_exts)
            or f.get("mimeType") in ('application/zip', 'application/x-zip-compressed', 'application/x-rar-compressed', 'application/x-tar', 'application/x-7z-compressed')
        ]
        label_ro = "arhive"
        label_en = "archives"
        matching_ids = [f["id"] for f in matching if f.get("id")]
        reply = (
            f"Am selectat toate cele {len(matching_ids)} {label_ro} din listă."
            if is_ro
            else f"Selected all {len(matching_ids)} {label_en} found in the list."
        ) if matching_ids else (
            f"Nu am găsit {label_ro} în lista curentă."
            if is_ro
            else f"No {label_en} found in the current list."
        )
        return {
            "reply": reply,
            "selected_ids": matching_ids,
            "drive_query": None,
            "target_platform": "drive",
            "new_files": [],
            "model_used": "instant-local"
        }

    return None

def find_exact_duplicate_groups(files: list) -> list:
    """Pre-compute exact duplicate clusters sharing identical file size and normalized base name."""
    def normalize_filename(name: str) -> tuple:
        base, ext = os.path.splitext(name)
        # Strip (1), (2), copy, copia lui, etc.
        base = re.sub(r'\s*\(\d+\)$', '', base.strip(), flags=re.IGNORECASE)
        base = re.sub(r'^(Copy of |Copia lui )\s*', '', base.strip(), flags=re.IGNORECASE)
        base = re.sub(r'[\s_-]+copy$', '', base.strip(), flags=re.IGNORECASE)
        return (base.strip().lower(), ext.lower())

    size_map = {}
    for f in files:
        size = f.get('size')
        name = f.get('name', '')
        if size and int(size) > 0 and name:
            key = (size, normalize_filename(name))
            if key not in size_map:
                size_map[key] = []
            size_map[key].append(f)

    duplicate_groups = []
    for (size, norm_name), group in size_map.items():
        if len(group) > 1:
            duplicate_groups.append({
                "original_to_keep": group[0],
                "redundant_copies": group[1:]
            })
    return duplicate_groups

class ChatRequest(BaseModel):
    prompt: str
    files: list
    preferred_model: Optional[str] = "auto"

@app.post("/api/chat")
async def process_chat(request: ChatRequest, x_gemini_key: str = Header(None)):
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fast-path for deselect / clear requests (<10ms)
    if is_deselect_request(request.prompt):
        is_ro = is_romanian(request.prompt)
        reply_msg = (
            "Am debifat toate fișierele selectate."
            if is_ro
            else "Deselected all selected files."
        )
        print(f"⚡ Instant Fast-Path: Deselected all files locally (RO={is_ro})")
        return {
            "reply": reply_msg,
            "selected_ids": [],
            "drive_query": None,
            "target_platform": "drive",
            "new_files": [],
            "model_used": "instant-local"
        }

    # Fast-path for simple file-type selection queries without date/size constraints (<10ms)
    file_type_fast_path = match_local_file_type_filter(request.prompt, request.files)
    if file_type_fast_path is not None:
        print(f"⚡ Instant Fast-Path: Matched file-type selection locally for '{request.prompt}'")
        return file_type_fast_path

    if not x_gemini_key or not x_gemini_key.strip():
        raise HTTPException(status_code=401, detail="Gemini API Key is missing. Please add it in Settings.")
        
    try:
        system_instruction = """
        You are SmartClean, an advanced dual-agent AI for Google Drive and Gmail management.
        You receive a user request, a JSON list of recent files or emails, and thumbnails (if applicable).
        
        CRITICAL LANGUAGE RULE: Always respond 100% in the exact same language used by the user in their latest message. If the user writes in English, respond strictly in English. If the user writes in Romanian, respond strictly in Romanian. Never mix languages.
        
        CRITICAL DUPLICATE RULE: You only have access to file metadata (name, size, mimeType), NOT visual image content. NEVER guess or claim images are "burst shots", "similar poses", or taken seconds apart based on sequential filenames (like _DSC3543, _DSC3544). Only flag files as duplicates if they appear 2 or more times in the list with the exact same base filename (or '(1)', 'Copy of') AND identical file size. Most importantly: when selecting duplicates for deletion (selected_ids), ALWAYS keep the first/original file unselected and ONLY include the redundant copy's ID in selected_ids so the user never deletes all copies of a file.
        
        FORMATTING RULE: Use clean newlines (\\n) and simple bullet points (• ) to organize lists and summaries. Do NOT use markdown asterisks (**) or raw backticks (`) since the chat bubble renders formatted plain text. Keep text readable, organized, and clean.
        
        You have THREE modes of operation. Decide which one fits best:
        
        MODE 1 (DRIVE VISUAL/LOCAL): If the request requires analyzing image content in Drive (e.g. "blurry photos"), look at the provided files and thumbnails. Return "selected_ids" from the provided list, and set "drive_query" to null. Set "target_platform" to "drive".
        
        MODE 2 (DRIVE GLOBAL SEARCH): If the request asks to find all Drive files of a certain format/type globally (e.g. "all pdfs"), DO NOT rely on the provided list. Set "drive_query" to a valid Google Drive API query string (e.g. "mimeType contains 'application/pdf'"). Set "selected_ids" to []. Set "target_platform" to "drive".
        
        MODE 3 (GMAIL ACTION/SEARCH): If the user asks to delete emails, newsletters, spam, or search for specific messages, set "target_platform" to "gmail". Generate a valid Gmail search query in the "drive_query" field (e.g., "older_than:1y", "from:newsletter@example.com", "has:attachment"). Set "selected_ids" to []. 
        
        IMPORTANT: Your goal is to prepare files/emails for the user to review. You do NOT delete anything yourself. You only provide the IDs or the query so the system can display them to the user.
        
        Return ONLY valid JSON with this exact structure:
        {
          "reply": "friendly explanation of what you did and that the items are ready for review",
          "selected_ids": ["id1", "id2"],
          "drive_query": "query string or null",
          "target_platform": "drive" 
        }
        (Note: target_platform can ONLY be 'drive' or 'gmail')
        """
        
        gemini_client = genai.Client(api_key=x_gemini_key.strip())
        
        # Compact file metadata: include id, name, size, mimeType, and modifiedTime to support date queries
        compact_files = [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "size": f.get("size"),
                "mimeType": f.get("mimeType"),
                "modifiedTime": f.get("modifiedTime") or f.get("date") or f.get("createdTime") or ""
            }
            for f in request.files
            if isinstance(f, dict) and f.get("id")
        ]

        prompt_content = [
            f"User Request: {request.prompt}\n\n[IMPORTANT: Detect the language of the user's message above and write your entire response strictly in that same language. Do NOT use Romanian unless the user's message above is written in Romanian.]\n\n",
            f"Files Metadata: {json.dumps(compact_files, separators=(',', ':'))}\n\n",
        ]
        
        # Pre-compute exact duplicate groups in Python to prevent AI hallucination
        duplicate_clusters = find_exact_duplicate_groups(request.files)
        if duplicate_clusters:
            dup_info = []
            for cluster in duplicate_clusters:
                orig = cluster["original_to_keep"]
                redundant = cluster["redundant_copies"]
                dup_info.append({
                    "original_file_to_keep": {"id": orig["id"], "name": orig["name"], "size": orig.get("size")},
                    "redundant_copies_to_select": [{"id": r["id"], "name": r["name"], "size": r.get("size")} for r in redundant]
                })
            prompt_content.append(f"Pre-computed Verified Duplicate Clusters (Same file size and name): {json.dumps(dup_info, separators=(',', ':'))}\n\n")

        # Only download image thumbnails if the request explicitly asks for visual inspection (e.g. blurry photos)
        visual_keywords = ["blurry", "claritate", "neclar", "low quality", "pixelat", "visual", "look like"]
        needs_visual = any(vk in request.prompt.lower() for vk in visual_keywords)

        if needs_visual:
            async with httpx.AsyncClient(verify=False) as http_client:
                fetch_tasks = []
                file_metadata_for_tasks = []

                for file_obj in request.files[:20]:
                    if 'thumbnailLink' in file_obj and file_obj.get('mimeType', '').startswith('image/'):
                        thumb_url = file_obj['thumbnailLink'].replace('=s220', '=s800')
                        fetch_tasks.append(http_client.get(thumb_url))
                        file_metadata_for_tasks.append(file_obj)

                if fetch_tasks:
                    print(f"Downloading {len(fetch_tasks)} thumbnails in parallel for visual analysis...")
                    responses = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                    prompt_content.append("Images for visual analysis (if applicable):\n")
                    for file_obj, img_resp in zip(file_metadata_for_tasks, responses):
                        # Ensure request succeeded with status 200
                        if not isinstance(img_resp, Exception) and getattr(img_resp, 'status_code', None) == 200:
                            prompt_content.append(f"Image for file ID: {file_obj['id']}, Name: {file_obj['name']}")
                            prompt_content.append(
                                types.Part.from_bytes(data=img_resp.content, mime_type="image/jpeg")
                            )

        # Active hierarchy prioritizing fastest proven working models
        fallback_hierarchy = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-3.1-pro-preview"]
        
        # Smart Routing & Model Selection
        user_pref = (request.preferred_model or "auto").strip()
        if user_pref.lower() == "auto" or not user_pref:
            is_complex = is_complex_task(request.prompt)
            primary_model = "gemini-3.8-flash" if is_complex else "gemini-3.5-flash-lite"
            print(f"🧠 Smart Routing: selected '{primary_model}' (complex task: {is_complex})")
        else:
            primary_model = user_pref

        # Build ordered list ensuring primary_model is tried first
        candidate_models = [primary_model] + [m for m in fallback_hierarchy if m != primary_model]

        # Filter out models currently in cooldown
        now = time.time()
        models_to_try = [m for m in candidate_models if MODEL_COOLDOWN_UNTIL.get(m, 0) <= now]
        if not models_to_try:
            print("⚠️ All candidate models are currently in cooldown. Resetting cooldowns and retrying all.")
            models_to_try = candidate_models
        else:
            skipped = [m for m in candidate_models if m not in models_to_try]
            if skipped:
                print(f"⏳ Skipping models currently in cooldown: {skipped}")

        response = None
        successful_model = None
        last_error = None

        for model_name in models_to_try:
            try:
                print(f"🤖 Attempting generation with Gemini model: {model_name}...")
                try:
                    response = await gemini_client.aio.models.generate_content(
                        model=model_name,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json"
                        )
                    )
                except Exception as call_err:
                    call_err_str = str(call_err)
                    if "400" in call_err_str or "INVALID_ARGUMENT" in call_err_str:
                        print(f"⚠️ Model '{model_name}' rejected response_mime_type='application/json', retrying with plain config...")
                        response = await gemini_client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt_content,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction
                            )
                        )
                    else:
                        raise call_err

                successful_model = model_name
                MODEL_COOLDOWN_UNTIL.pop(model_name, None)
                print(f"✅ Successfully generated content using {model_name}")
                break
            except Exception as e:
                last_error = e
                status_code = getattr(e, "code", None)
                err_msg = str(e)
                print(f"⚠️ Gemini call failed with model '{model_name}': {err_msg}")

                # Check if this is an API key authentication/permission error (terminate immediately)
                is_auth_error = (
                    status_code in (401, 403)
                    or "API_KEY_INVALID" in err_msg
                    or "UNAUTHENTICATED" in err_msg
                    or "PERMISSION_DENIED" in err_msg
                    or "API key not valid" in err_msg
                )
                if is_auth_error:
                    print(f"❌ Auth error ({status_code}) with {model_name}: {err_msg}. Raising immediately.")
                    raise HTTPException(
                        status_code=401,
                        detail="Gemini API Key is invalid or expired. Please check your key in Settings."
                    )

                # Check if error is 404 (Not Found / Model deprecated or removed)
                is_404 = (
                    status_code == 404
                    or "404" in err_msg
                    or "NOT_FOUND" in err_msg
                )

                # Check if error is 400 (Invalid Argument / Model rejected request)
                is_400 = (
                    status_code == 400
                    or "400" in err_msg
                    or "INVALID_ARGUMENT" in err_msg
                )

                # Check if error is 429 (Rate Limit / Quota) or 503 (Unavailable / Overloaded)
                is_429_or_503 = (
                    status_code in (429, 503)
                    or "429" in err_msg
                    or "503" in err_msg
                    or "RESOURCE_EXHAUSTED" in err_msg
                    or "UNAVAILABLE" in err_msg
                    or "overloaded" in err_msg.lower()
                )

                if is_404 or is_400:
                    MODEL_COOLDOWN_UNTIL[model_name] = time.time() + 3600  # 1 hour
                    print(f"🚫 Model '{model_name}' hit {status_code or '400/404'}. Placed on 1-hour cooldown. Trying next model...")
                elif is_429_or_503:
                    MODEL_COOLDOWN_UNTIL[model_name] = time.time() + 120  # 2 minutes
                    print(f"⏳ Model '{model_name}' rate limited/overloaded. Placed on 2-minute cooldown. Trying next model...")
                else:
                    print(f"⚠️ Model '{model_name}' hit error: {err_msg}. Trying next fallback model...")

                continue

        if not response:
            print(f"❌ All Gemini models exhausted: {models_to_try}. Last error: {last_error}")
            raise HTTPException(
                status_code=503,
                detail=f"All Gemini models failed. Last error: {last_error}"
            )

        raw_text = response.text if response else ""
        
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        clean_text = match.group(0) if match else raw_text.strip()
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            print(f"Error parsing AI-generated JSON: {clean_text}")
            data = {
                "reply": raw_text,
                "selected_ids": [],
                "drive_query": None,
                "target_platform": "drive"
            }
        
        # HYBRID SEARCH: Only execute global query requested by AI if user actually asked for search/scan
        drive_query = data.get("drive_query")
        if drive_query and str(drive_query).strip().lower() not in ("none", "null", ""):
            search_keywords = ["search", "find", "all", "get", "show", "list", "cauta", "gaseste", "toate", "arata", "extrage", "scan", "email", "mail", "spam", "newsletter", "inbox"]
            has_search_intent = any(k in request.prompt.lower() for k in search_keywords)
            if not has_search_intent and not is_complex_task(request.prompt):
                print(f"ℹ️ Skipping unexpected drive_query '{drive_query}' because user prompt lacks search intent.")
                data["drive_query"] = None

        if data.get("drive_query"):
            print(f"🔎 Global search requested by AI: {data['drive_query']}")
            try:
                creds = Credentials(token=token)
                target_platform = data.get("target_platform", "drive")
                
                if target_platform == "gmail":
                    service = build('gmail', 'v1', credentials=creds)
                    final_q = f"({data['drive_query']}) -in:trash"
                    
                    results = await asyncio.to_thread(
                        lambda: service.users().messages().list(
                            userId='me',
                            q=final_q,
                            maxResults=500
                        ).execute()
                    )
                    
                    messages = results.get('messages', [])
                    
                    if messages:
                        async with httpx.AsyncClient(verify=False) as http_client:
                            sem = asyncio.Semaphore(50)
                            async def fetch_with_sem(msg):
                                async with sem:
                                    return await http_client.get(
                                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date",
                                        headers={"Authorization": f"Bearer {token}"}
                                    )
                            
                            fetch_tasks = [fetch_with_sem(msg) for msg in messages]
                            responses = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                            
                            new_files = []
                            for msg, resp in zip(messages, responses):
                                if not isinstance(resp, Exception) and getattr(resp, 'status_code', None) == 200:
                                    msg_data = resp.json()
                                    headers = msg_data.get('payload', {}).get('headers', [])
                                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                                    from_sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                                    date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                                    
                                    new_files.append({
                                        "id": msg['id'],
                                        "name": subject,
                                        "mimeType": "application/vnd.google-apps.mail",
                                        "webViewLink": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                                        "from": from_sender,
                                        "snippet": msg_data.get('snippet', ''),
                                        "modifiedTime": date_str
                                    })
                        data["new_files"] = new_files
                        data["selected_ids"] = [f["id"] for f in new_files]
                    else:
                        data["new_files"] = []
                        data["selected_ids"] = []
                        
                else:
                    service = build('drive', 'v3', credentials=creds)
                    
                    final_q = f"({data['drive_query']}) and trashed = false"
                    
                    results = await asyncio.to_thread(
                        lambda: service.files().list(
                            pageSize=500,
                            fields="files(id, name, mimeType, size, modifiedTime, webViewLink, thumbnailLink)",
                            orderBy="modifiedTime desc",
                            q=final_q
                        ).execute()
                    )
                    
                    new_files = results.get('files', [])
                    data["new_files"] = new_files
                    data["selected_ids"] = [f["id"] for f in new_files]
                    
            except Exception as query_err:
                print(f"Error during Google API Query: {query_err}")
                data["new_files"] = []
        else:
            data["new_files"] = []
            
        data["model_used"] = successful_model
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during AI processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class DeleteRequest(BaseModel):
    file_ids: list[str]

@app.post("/api/delete")
async def delete_files(request: DeleteRequest):
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        deleted_count = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            # Spargem lista in bucati de cate 50 pentru a evita Rate Limit-ul Google
            chunk_size = 50
            print(f"🗑️ Mutam {len(request.file_ids)} fisiere in trash (Batch processing async)...")
            
            for i in range(0, len(request.file_ids), chunk_size):
                chunk_ids = request.file_ids[i:i + chunk_size]
                tasks = []
                
                for file_id in chunk_ids:
                    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                    tasks.append(client.patch(url, headers=headers, json={"trashed": True}))
                    
                # Executam calupul de 50 concurent
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for resp in responses:
                    if not isinstance(resp, Exception) and getattr(resp, 'status_code', 500) < 300:
                        deleted_count += 1
                        
        return {
            "message": f"Successfully moved {deleted_count} files to Trash.", 
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"Error trashing files: {e}")
        raise HTTPException(status_code=500, detail="Eroare la stergerea fisierelor.")


@app.get("/api/trash")
async def get_trash_files():
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")
        
    try:
        creds = Credentials(token=token)
        service = build('drive', 'v3', credentials=creds)
        
        # Cerem fisierele care au parametrul trashed = true
        results = await asyncio.to_thread(
            lambda: service.files().list(
                pageSize=500,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
                orderBy="modifiedTime desc",
                q="trashed = true"
            ).execute()
        )
        
        items = results.get('files', [])
        return {"files": items}
        
    except Exception as e:
        print(f"Eroare la aducerea fisierelor din trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/trash/empty")
async def empty_trash():
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        creds = Credentials(token=token)
        service = build('drive', 'v3', credentials=creds)
        await asyncio.to_thread(lambda: service.files().emptyTrash().execute())
        return {"message": "Trash emptied successfully."}
    except Exception as e:
        print(f"Error emptying trash: {e}")
        raise HTTPException(status_code=500, detail="Error emptying trash.")

class RestoreRequest(BaseModel):
    file_ids: list[str]

@app.post("/api/restore")
async def restore_files(request: RestoreRequest):
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        restored_count = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            chunk_size = 50
            print(f"♻️ Restauram {len(request.file_ids)} fisiere (Batch processing async)...")
            
            for i in range(0, len(request.file_ids), chunk_size):
                chunk_ids = request.file_ids[i:i + chunk_size]
                tasks = []
                
                for file_id in chunk_ids:
                    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                    tasks.append(client.patch(url, headers=headers, json={"trashed": False}))
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for resp in responses:
                    if not isinstance(resp, Exception) and getattr(resp, 'status_code', None) == 200:
                        restored_count += 1
                        
        return {
            "message": f"Successfully restored {restored_count} files.", 
            "restored_count": restored_count
        }
        
    except Exception as e:
        print(f"Error restoring files: {e}")
        raise HTTPException(status_code=500, detail="Eroare la restaurarea fisierelor.")


@app.get("/api/gmail/emails")
async def get_gmail_emails():
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        creds = Credentials(token=token)
        service = build('gmail', 'v1', credentials=creds)
        
        results = await asyncio.to_thread(
            lambda: service.users().messages().list(
                userId='me',
                q="-in:trash",
                maxResults=500
            ).execute()
        )
        
        messages = results.get('messages', [])
        if not messages:
            return {"files": []}
            
        async with httpx.AsyncClient(verify=False) as http_client:
            sem = asyncio.Semaphore(50)
            async def fetch_with_sem(msg):
                async with sem:
                    return await http_client.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
            fetch_tasks = [fetch_with_sem(msg) for msg in messages]
            responses = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            
            email_list = []
            for msg, resp in zip(messages, responses):
                if not isinstance(resp, Exception) and getattr(resp, 'status_code', None) == 200:
                    msg_data = resp.json()
                    headers = msg_data.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                    from_sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                    date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    
                    email_list.append({
                        "id": msg['id'],
                        "name": subject,
                        "mimeType": "application/vnd.google-apps.mail",
                        "webViewLink": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                        "from": from_sender,
                        "snippet": msg_data.get('snippet', ''),
                        "modifiedTime": date_str
                    })
                    
        return {"files": email_list}
        
    except Exception as e:
        print(f"Eroare la aducerea emailurilor: {e}")
        raise HTTPException(status_code=500, detail="Eroare la aducerea emailurilor")


class GmailDeleteRequest(BaseModel):
    email_ids: list[str]

@app.post("/api/gmail/trash")
async def delete_gmail_emails(request: GmailDeleteRequest):
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        deleted_count = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            chunk_size = 50
            print(f"🗑️ Mutam {len(request.email_ids)} emailuri in trash (Batch processing async)...")
            
            for i in range(0, len(request.email_ids), chunk_size):
                chunk_ids = request.email_ids[i:i + chunk_size]
                tasks = []
                
                for email_id in chunk_ids:
                    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}/trash"
                    tasks.append(client.post(url, headers=headers))
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for resp in responses:
                    if not isinstance(resp, Exception) and getattr(resp, 'status_code', 500) < 300:
                        deleted_count += 1
                        
        return {
            "message": f"Successfully moved {deleted_count} emails to Trash.", 
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"Error trashing emails: {e}")
        raise HTTPException(status_code=500, detail="Eroare la stergerea emailurilor.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=14201)