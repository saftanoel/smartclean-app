import os
import asyncio
import httpx
import json
import re
import base64 
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google import genai
from google.genai import types

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

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(bundle_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
SCOPES = 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/gmail.modify'

# Configurare Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SESSION_STORE = {}

@app.get("/health")
async def health_check():
    return {"status": "API is running"}

@app.get("/api/status")
async def api_status():
    is_connected = "default_user" in SESSION_STORE
    return {"is_connected": is_connected}

@app.post("/api/logout")
async def logout():
    if "default_user" in SESSION_STORE:
        del SESSION_STORE["default_user"]
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
        SESSION_STORE["default_user"] = token_data["access_token"]
        print("\nToken salvat in sesiune cu succes!\n")
        
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

@app.get("/api/files")
async def get_files():
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")
        
    try:
        creds = Credentials(token=token)
        service = build('drive', 'v3', credentials=creds)
        
        # NOU: Am adaugat 'thumbnailLink' la fields!
        results = service.files().list(
            pageSize=500,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink, thumbnailLink)",
            orderBy="modifiedTime desc",
            q="trashed = false"
        ).execute()
        
        items = results.get('files', [])
        return {"files": items}
        
    except Exception as e:
        print(f"Eroare la aducerea fisierelor: {e}")
        # Daca token-ul este expirat/invalid, il stergem din sesiune
        if "default_user" in SESSION_STORE:
            del SESSION_STORE["default_user"]
        raise HTTPException(status_code=401, detail="Token expirat sau invalid")


class ChatRequest(BaseModel):
    prompt: str
    files: list

@app.post("/api/chat")
async def process_chat(request: ChatRequest):
    token = SESSION_STORE.get("default_user")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        system_instruction = """
        You are SmartClean, an advanced dual-agent AI for Google Drive and Gmail management.
        You receive a user request, a JSON list of recent files or emails, and thumbnails (if applicable).
        
        You have THREE modes of operation. Decide which one fits best:
        
        MODE 1 (DRIVE VISUAL/LOCAL): If the request requires analyzing image content in Drive, look at the provided files and thumbnails. Return "selected_ids" from the provided list, and set "drive_query" to null. Set "target_platform" to "drive".
        
        MODE 2 (DRIVE GLOBAL SEARCH): If the request asks to find all Drive files of a certain format/type globally, DO NOT rely on the provided list. Set "drive_query" to a valid Google Drive API query string. Set "selected_ids" to []. Set "target_platform" to "drive".
        
        MODE 3 (GMAIL SEARCH): If the user asks to delete emails, newsletters, spam, or old messages, set "target_platform" to "gmail" and generate a valid Gmail search query in "drive_query" (e.g., "older_than:1y", "from:newsletter@example.com", "has:attachment"). Set "selected_ids" to []. Keep using the field name "drive_query" for backwards compatibility, but it will hold the Gmail query.
        
        Return ONLY valid JSON with this exact structure:
        {
          "reply": "friendly explanation of what you did",
          "selected_ids": ["id1", "id2"],
          "drive_query": "query string or null",
          "target_platform": "drive"
        }
        (Note: target_platform can be 'drive' or 'gmail')
        """
        
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt_content = [
            f"User Request: {request.prompt}\n\n",
            f"Files Metadata: {json.dumps(request.files)}\n\n",
            "Images for visual analysis (if applicable):\n"
        ]
        
        async with httpx.AsyncClient() as http_client:
            fetch_tasks = []
            file_metadata_for_tasks = []

            for file_obj in request.files:
                if 'thumbnailLink' in file_obj and file_obj.get('mimeType', '').startswith('image/'):
                    # Pregătim URL-urile
                    thumb_url = file_obj['thumbnailLink'].replace('=s220', '=s800')
                    # Creăm "task-ul" de descărcare, dar nu îl executăm încă
                    fetch_tasks.append(http_client.get(thumb_url))
                    file_metadata_for_tasks.append(file_obj)

            if fetch_tasks:
                print(f"Descarc {len(fetch_tasks)} miniaturi in paralel...")
                # Executăm TOATE task-urile în același timp!
                responses = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                prompt_content.append("Images for visual analysis (if applicable):\n")
                for file_obj, img_resp in zip(file_metadata_for_tasks, responses):
                    # Ne asigurăm că request-ul nu a dat eroare și are status 200
                    if not isinstance(img_resp, Exception) and getattr(img_resp, 'status_code', None) == 200:
                        prompt_content.append(f"Image for file ID: {file_obj['id']}, Name: {file_obj['name']}")
                        prompt_content.append(
                            types.Part.from_bytes(data=img_resp.content, mime_type="image/jpeg")
                        )

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        raw_text = response.text
        
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        clean_text = match.group(0) if match else raw_text.strip()
        data = json.loads(clean_text)
        
        # MAGIA HIBRIDĂ: Executăm query-ul global cerut de AI
        if data.get("drive_query"):
            print(f"🔎 Căutare globală cerută de AI: {data['drive_query']}")
            try:
                creds = Credentials(token=token)
                target_platform = data.get("target_platform", "drive")
                
                if target_platform == "gmail":
                    service = build('gmail', 'v1', credentials=creds)
                    final_q = f"({data['drive_query']}) -in:trash"
                    
                    results = service.users().messages().list(
                        userId='me',
                        q=final_q,
                        maxResults=500
                    ).execute()
                    
                    messages = results.get('messages', [])
                    
                    if messages:
                        async with httpx.AsyncClient() as http_client:
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
                        data["reply"] += f" (Am scanat inbox-ul și am extras {len(new_files)} emailuri relevante)."
                    else:
                        data["new_files"] = []
                        data["selected_ids"] = []
                        data["reply"] += " (Nu am găsit emailuri relevante)."
                        
                else:
                    service = build('drive', 'v3', credentials=creds)
                    
                    final_q = f"({data['drive_query']}) and trashed = false"
                    
                    results = service.files().list(
                        pageSize=500,
                        fields="files(id, name, mimeType, size, modifiedTime, webViewLink, thumbnailLink)",
                        orderBy="modifiedTime desc",
                        q=final_q
                    ).execute()
                    
                    new_files = results.get('files', [])
                    data["new_files"] = new_files
                    data["selected_ids"] = [f["id"] for f in new_files]
                    
                    if new_files:
                        data["reply"] += f" (Am scanat cloud-ul și am extras {len(new_files)} rezultate relevante pe care le-am adus în listă)."
                    else:
                        data["reply"] += " (Nu am găsit nimic relevant în tot contul)."
                    
            except Exception as query_err:
                print(f"Eroare la Google API Query: {query_err}")
                data["reply"] += " (Eroare la construirea comenzii globale)."
                data["new_files"] = []
        else:
            data["new_files"] = []
            
        return data
        
    except Exception as e:
        print(f"Eroare la procesarea AI: {e}")
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
        
        async with httpx.AsyncClient() as client:
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
                    if not isinstance(resp, Exception) and getattr(resp, 'status_code', None) == 200:
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
        results = service.files().list(
            pageSize=500,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
            q="trashed = true"
        ).execute()
        
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
        service.files().emptyTrash().execute()
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
        
        async with httpx.AsyncClient() as client:
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
        
        results = service.users().messages().list(
            userId='me',
            q="-in:trash",
            maxResults=500
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return {"files": []}
            
        async with httpx.AsyncClient() as http_client:
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
        
        async with httpx.AsyncClient() as client:
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
                    if not isinstance(resp, Exception) and getattr(resp, 'status_code', None) == 200:
                        deleted_count += 1
                        
        return {
            "message": f"Successfully moved {deleted_count} emails to Trash.", 
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"Error trashing emails: {e}")
        raise HTTPException(status_code=500, detail="Eroare la stergerea emailurilor.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)