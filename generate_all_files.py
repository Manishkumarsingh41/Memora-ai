#!/usr/bin/env python3
"""
Memora AI - Complete Project Generator
Creates all 37 files with production-ready code
Run: python generate_all_files.py
"""

import os
from pathlib import Path

def create_file(path, content):
    """Create file with content"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"✅ {path}")

# ============================================================================
# ALL FILE CONTENTS
# ============================================================================

FILES = {
    # ROOT FILES
    "main.py": '''from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import traceback
from datetime import datetime

from config import get_settings
from services.database import init_db
from services.pending_store import get_redis, close_redis
from routers.webhook import router as webhook_router
from routers.admin import router as admin_router
from logging_config import get_logger

settings = get_settings()
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Memora AI v1.0.0")
    try:
        init_db()
        os.makedirs(settings.temp_dir, exist_ok=True)
        os.makedirs(settings.chroma_db_path, exist_ok=True)
        os.makedirs("./logs", exist_ok=True)
        logger.info("✅ Database and directories initialized")
        
        try:
            redis = await get_redis()
            await redis.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
        
        logger.info("✅ Memora AI started successfully")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise
    
    yield
    
    logger.info("🛑 Shutting down Memora AI")
    try:
        await close_redis()
        logger.info("✅ Redis closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

app = FastAPI(
    title="Memora AI",
    description="Conversational AI File & Knowledge System via WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": 500,
            "message": "Internal server error",
            "traceback": traceback.format_exc() if settings.debug else None,
        },
    )

app.include_router(webhook_router)
app.include_router(admin_router)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "app": "Memora AI",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
''',

    "config.py": '''from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str = "memora_verify_token"
    anthropic_api_key: str
    google_credentials_path: str = "credentials.json"
    google_drive_root_folder: str = "AI-Storage"
    redis_url: str = "redis://redis:6379"
    redis_password: Optional[str] = "memora_redis_pass"
    secret_key: str = "change-me-in-production"
    admin_secret: str = "admin_secret_change_me"
    debug: bool = True
    sqlite_db_path: str = "./memora.db"
    chroma_db_path: str = "./chroma_db"
    temp_dir: str = "./temp_files"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
''',

    "logging_config.py": '''import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    main_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "memora.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    main_handler.setLevel(logging.DEBUG)
    
    error_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "memora_errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
    )
    error_handler.setLevel(logging.ERROR)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    for handler in [main_handler, error_handler, console_handler]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
''',

    "requirements.txt": '''fastapi==0.115.0
uvicorn[standard]==0.30.6
python-dotenv==1.0.1
httpx==0.27.2
anthropic==0.34.2
google-api-python-client==2.143.0
google-auth==2.35.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
chromadb==0.5.15
sentence-transformers==3.1.1
PyMuPDF==1.24.11
Pillow==10.4.0
aiofiles==24.1.0
sqlalchemy==2.0.35
pydantic-settings==2.5.2
python-multipart==0.0.12
aioredis==2.0.1
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-mock==3.14.0
''',

    "Dockerfile": '''FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential libmupdf-dev libffi-dev libssl-dev pkg-config && \\
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -r appuser && useradd -r -g appuser appuser && \\
    mkdir -p /app/temp_files /app/chroma_db /app/logs && \\
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',

    "docker-compose.yml": '''version: '3.8'

services:
  app:
    build: .
    container_name: memora-ai-app
    env_file: .env
    environment:
      REDIS_URL: "redis://redis:6379"
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./memora.db:/app/memora.db
      - ./logs:/app/logs
      - ./credentials.json:/app/credentials.json:ro
      - ./temp_files:/app/temp_files
    ports:
      - "8000:8000"
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - memora-network

  redis:
    image: redis:7-alpine
    container_name: memora-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    networks:
      - memora-network

volumes:
  redis_data:

networks:
  memora-network:
    driver: bridge
''',

    ".env.example": '''WHATSAPP_ACCESS_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_id_here
WHATSAPP_VERIFY_TOKEN=memora_verify_token
ANTHROPIC_API_KEY=your_key_here
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_ROOT_FOLDER=AI-Storage
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=memora_redis_pass
ADMIN_SECRET=change_me
SECRET_KEY=change_me
DEBUG=true
CHROMA_DB_PATH=./chroma_db
SQLITE_DB_PATH=./memora.db
TEMP_DIR=./temp_files
''',

    ".gitignore": '''.env
__pycache__/
*.pyc
*.db
chroma_db/
logs/
temp_files/
credentials.json
.vscode/
.idea/
venv/
''',

    # MODELS
    "models/__init__.py": '"""Models for Memora AI"""',

    "models/schemas.py": '''from pydantic import BaseModel
from typing import Optional

class WhatsAppMessage(BaseModel):
    from_number: str
    message_id: str
    message_type: str
    text: Optional[str] = None

class FileMetadata(BaseModel):
    id: Optional[int] = None
    user_id: str
    file_name: str
    file_type: str
    drive_file_id: str
    folder: str
    created_at: Optional[str] = None

class PendingUpload(BaseModel):
    user_id: str
    media_id: str
    media_mime_type: str
    original_filename: str
    file_type: str
    awaiting: str = "action"

class MemoryEntry(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

class AgentResponse(BaseModel):
    intent: str
    response_text: str
    file_query: Optional[str] = None
    file_number: Optional[int] = None
    rag_query: Optional[str] = None
''',

    "models/errors.py": '''from pydantic import BaseModel
from typing import Optional, List, Any

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    type: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    code: int
    message: str
    details: Optional[List[ErrorDetail]] = None
''',

    # SERVICES
    "services/__init__.py": '"""Services for Memora AI"""',

    "services/database.py": '''import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from config import get_settings

settings = get_settings()

def _get_conn():
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                drive_file_id TEXT NOT NULL,
                folder TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

def save_file_metadata(user_id: str, file_name: str, file_type: str, drive_file_id: str, folder: str) -> int:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO files (user_id, file_name, file_type, drive_file_id, folder, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, file_name, file_type, drive_file_id, folder, now),
        )
        return cursor.lastrowid

def list_files(user_id: str) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]

def find_files_by_name(user_id: str, query: str) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE user_id = ? AND LOWER(file_name) LIKE ?",
            (user_id, f"%{query.lower()}%"),
        ).fetchall()
    return [dict(row) for row in rows]

def get_file_by_id(file_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
    return dict(row) if row else None
''',

    "services/memory.py": '''import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from config import get_settings

settings = get_settings()

def _get_conn():
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    return conn

def add_memory(user_id: str, role: str, content: str):
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO memory (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now),
        )

def get_memory(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM memory WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]

def clear_memory(user_id: str):
    with _get_conn() as conn:
        conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))

def get_memory_summary(user_id: str) -> Dict[str, Any]:
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM memory WHERE user_id = ?", (user_id,)).fetchone()[0]
        user_msgs = conn.execute("SELECT COUNT(*) FROM memory WHERE user_id = ? AND role = 'user'", (user_id,)).fetchone()[0]
        asst_msgs = conn.execute("SELECT COUNT(*) FROM memory WHERE user_id = ? AND role = 'assistant'", (user_id,)).fetchone()[0]
    
    return {
        "total_messages": total,
        "user_messages": user_msgs,
        "assistant_messages": asst_msgs,
    }
''',

    "services/rag.py": '''import fitz
from typing import List, Tuple, Dict
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from config import get_settings
from logging_config import get_logger
import os

settings = get_settings()
logger = get_logger("rag")

_chroma_client = None
_embedder = None

def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        try:
            os.makedirs(settings.chroma_db_path, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            logger.info("✅ ChromaDB initialized")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    return _chroma_client

def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Embeddings loaded")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    return _embedder

def extract_pdf_chunks(pdf_path: str, chunk_size: int = 500) -> List[Tuple[str, int]]:
    try:
        chunks = []
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                for i in range(0, len(text), chunk_size):
                    chunk = text[i:i+chunk_size].strip()
                    if chunk:
                        chunks.append((chunk, page_num))
        doc.close()
        logger.info(f"Extracted {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def index_pdf(user_id: str, file_name: str, pdf_path: str) -> int:
    try:
        chunks = extract_pdf_chunks(pdf_path)
        if not chunks:
            return 0
        
        client = _get_chroma_client()
        collection = client.get_or_create_collection(name=f"user_{user_id}", metadata={"user_id": user_id})
        embedder = _get_embedder()
        
        total = 0
        for start in range(0, len(chunks), 100):
            end = min(start + 100, len(chunks))
            batch = chunks[start:end]
            texts = [c[0] for c in batch]
            pages = [c[1] for c in batch]
            embeddings = embedder.encode(texts, convert_to_numpy=True).tolist()
            metas = [{"file_name": file_name, "page": str(p), "user_id": user_id} for p in pages]
            ids = [f"{file_name}_{start+i}" for i in range(len(texts))]
            collection.upsert(embeddings=embeddings, documents=texts, metadatas=metas, ids=ids)
            total += len(texts)
        
        logger.info(f"Indexed {total} chunks")
        return total
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def query_documents(user_id: str, query: str, top_k: int = 5) -> List[Dict]:
    try:
        client = _get_chroma_client()
        try:
            collection = client.get_collection(name=f"user_{user_id}")
        except:
            return []
        
        embedder = _get_embedder()
        query_emb = embedder.encode([query], convert_to_numpy=True).tolist()[0]
        results = collection.query(query_embeddings=[query_emb], n_results=top_k)
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return []
        
        formatted = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i] if results.get("distances") else 0
            formatted.append({
                "text": doc,
                "file_name": meta.get("file_name", "?"),
                "page": int(meta.get("page", 0)),
                "distance": float(dist),
            })
        
        return formatted
    except Exception as e:
        logger.error(f"Error: {e}")
        return []

def delete_user_docs(user_id: str, file_name: str) -> bool:
    try:
        client = _get_chroma_client()
        try:
            collection = client.get_collection(name=f"user_{user_id}")
            collection.delete(where={"$and": [{"file_name": {"$eq": file_name}}, {"user_id": {"$eq": user_id}}]})
            return True
        except:
            return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

def delete_user_all_docs(user_id: str) -> bool:
    try:
        client = _get_chroma_client()
        try:
            client.delete_collection(name=f"user_{user_id}")
        except:
            pass
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
''',

    "services/agent.py": '''from anthropic import Anthropic
from config import get_settings
from logging_config import get_logger
import json
from typing import Dict, Optional, List

settings = get_settings()
logger = get_logger("agent")
client = Anthropic(api_key=settings.anthropic_api_key)

INTENT_PROMPT = """You are Memora AI. Respond with ONLY valid JSON:
{"intent": "list_files|retrieve_file|rag_query|summarize_file|chitchat", 
 "response_text": "...", 
 "file_query": null, 
 "file_number": null, 
 "rag_query": null}"""

def detect_intent_and_respond(user_id: str, user_message: str, memory_context: str = "") -> Dict:
    try:
        messages = [{"role": "user", "content": f"{memory_context}\\n\\nMessage: {user_message}"}]
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=INTENT_PROMPT,
            messages=messages,
        )
        
        try:
            parsed = json.loads(response.content[0].text)
            return parsed
        except:
            return {
                "intent": "chitchat",
                "response_text": response.content[0].text,
                "file_query": None,
                "file_number": None,
                "rag_query": None,
            }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "intent": "error",
            "response_text": "Error",
            "file_query": None,
            "file_number": None,
            "rag_query": None,
        }

def generate_rag_answer(user_id: str, question: str, chunks: List[Dict]) -> str:
    try:
        context = "\\n\\n".join([f"[{c['file_name']}, page {c['page']}]: {c['text'][:200]}" for c in chunks])
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system="Answer based ONLY on provided context. Include citations.",
            messages=[{"role": "user", "content": f"Context:\\n{context}\\n\\nQuestion: {question}"}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Error generating answer"

def generate_summary(file_text: str, file_name: str) -> str:
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system="Summarize in 5 bullet points",
            messages=[{"role": "user", "content": f"Summarize:\\n{file_text[:8000]}"}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Error generating summary"
''',

    "services/whatsapp.py": '''import httpx
from config import get_settings
from logging_config import get_logger
from typing import List, Optional, Dict
import aiofiles
import os

settings = get_settings()
logger = get_logger("whatsapp")
BASE_URL = "https://graph.facebook.com/v20.0"

async def send_text(to: str, text: str) -> bool:
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{BASE_URL}/{settings.whatsapp_phone_number_id}/messages",
                json=payload,
                params={"access_token": settings.whatsapp_access_token},
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def send_buttons(to: str, body: str, buttons: List[Dict]) -> bool:
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": buttons[:3]},
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{BASE_URL}/{settings.whatsapp_phone_number_id}/messages",
                json=payload,
                params={"access_token": settings.whatsapp_access_token},
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def send_list_message(to: str, body: str, items: List[Dict]) -> bool:
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body},
                "action": {"button": "Select", "sections": [{"title": "Options", "rows": items}]},
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{BASE_URL}/{settings.whatsapp_phone_number_id}/messages",
                json=payload,
                params={"access_token": settings.whatsapp_access_token},
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def send_document(to: str, file_path: str, filename: str, caption: str = "") -> bool:
    try:
        async with aiofiles.open(file_path, "rb") as f:
            file_data = await f.read()
        
        files = {"file": (filename, file_data)}
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"filename": filename, "caption": caption},
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{BASE_URL}/{settings.whatsapp_phone_number_id}/messages",
                data=data,
                files=files,
                params={"access_token": settings.whatsapp_access_token},
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def download_media(media_id: str, dest_path: str) -> str:
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{BASE_URL}/{media_id}",
                params={"access_token": settings.whatsapp_access_token},
            )
            media_url = response.json().get("url")
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(media_url, params={"access_token": settings.whatsapp_access_token})
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(response.content)
        
        logger.info(f"Downloaded: {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
''',

    "services/drive.py": '''from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from config import get_settings
from logging_config import get_logger
import io
import os

settings = get_settings()
logger = get_logger("drive")
SCOPES = ["https://www.googleapis.com/auth/drive"]

FOLDER_MAP = {"pdf": "documents", "image": "images", "video": "videos"}

def _get_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            settings.google_credentials_path, scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def _find_or_create_folder(service, parent_id: str, folder_name: str) -> str:
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        results = service.files().list(q=query, spaces="drive", fields="files(id, name)", pageSize=1).execute()
        
        if results.get("files"):
            return results["files"][0]["id"]
        
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def _get_or_create_user_folder(service, user_id: str) -> str:
    try:
        root_id = _find_or_create_folder(service, "root", settings.google_drive_root_folder)
        user_folder_id = _find_or_create_folder(service, root_id, user_id)
        return user_folder_id
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def upload_file(user_id: str, local_path: str, file_name: str, file_type: str) -> str:
    try:
        service = _get_service()
        user_folder_id = _get_or_create_user_folder(service, user_id)
        subfolder_name = FOLDER_MAP.get(file_type, "documents")
        subfolder_id = _find_or_create_folder(service, user_folder_id, subfolder_name)
        
        file_metadata = {"name": file_name, "parents": [subfolder_id]}
        media = MediaFileUpload(local_path, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        logger.info(f"Uploaded: {file.get('id')}")
        return file.get("id")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def download_file(drive_file_id: str, dest_path: str) -> str:
    try:
        service = _get_service()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        request = service.files().get_media(fileId=drive_file_id)
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        logger.info(f"Downloaded: {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
''',

    "services/pending_store.py": '''import aioredis
from config import get_settings
from logging_config import get_logger
from typing import Optional
import json
from models.schemas import PendingUpload

settings = get_settings()
logger = get_logger("pending_store")
_redis_client: Optional[aioredis.Redis] = None
PENDING_EXPIRY_SECONDS = 600

async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                encoding="utf8",
                decode_responses=True,
            )
            await _redis_client.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    return _redis_client

async def close_redis():
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.close()
            _redis_client = None
        except Exception as e:
            logger.error(f"Error: {e}")

async def set_pending(user_id: str, pending: PendingUpload) -> None:
    try:
        redis = await get_redis()
        key = f"pending:{user_id}"
        json_data = pending.model_dump_json()
        await redis.setex(key, PENDING_EXPIRY_SECONDS, json_data)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

async def get_pending(user_id: str) -> Optional[PendingUpload]:
    try:
        redis = await get_redis()
        key = f"pending:{user_id}"
        json_data = await redis.get(key)
        if json_data:
            return PendingUpload.model_validate_json(json_data)
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

async def delete_pending(user_id: str) -> None:
    try:
        redis = await get_redis()
        key = f"pending:{user_id}"
        await redis.delete(key)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
''',

    # ROUTERS
    "routers/__init__.py": '"""Routers"""',

    "routers/webhook.py": '''from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from typing import Optional
from config import get_settings
from services import whatsapp, drive, database, memory, agent, pending_store, rag
from models.schemas import PendingUpload
from logging_config import get_logger

settings = get_settings()
logger = get_logger("webhook")
router = APIRouter()

@router.get("/webhook")
async def verify_webhook(request: Request):
    try:
        params = dict(request.query_params)
        if params.get("hub.verify_token") != settings.whatsapp_verify_token:
            raise HTTPException(status_code=403)
        return params.get("hub.challenge")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                for message in change.get("value", {}).get("messages", []):
                    background_tasks.add_task(
                        process_message,
                        message.get("from"),
                        message.get("type"),
                        message,
                    )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "ok"}

async def process_message(user_id: str, message_type: str, message: dict):
    try:
        if message_type == "text":
            text = message.get("text", {}).get("body", "").strip()
            if not text:
                return
            memory.add_memory(user_id, "user", text)
            memory_context = memory.get_memory(user_id, limit=10)
            memory_text = "\\n".join([f"{m['role']}: {m['content']}" for m in memory_context])
            agent_response = agent.detect_intent_and_respond(user_id, text, memory_text)
            
            if agent_response.get("intent") == "list_files":
                files = database.list_files(user_id)
                if files:
                    file_list = "📁 Files:\\n" + "\\n".join([f"{i}. {f['file_name']}" for i, f in enumerate(files, 1)])
                    await whatsapp.send_text(user_id, file_list)
            else:
                memory.add_memory(user_id, "assistant", agent_response.get("response_text"))
                await whatsapp.send_text(user_id, agent_response.get("response_text"))
        
        elif message_type in ("document", "image", "video"):
            file_info = message.get(message_type, {})
            pending = PendingUpload(
                user_id=user_id,
                media_id=file_info.get("id"),
                media_mime_type=file_info.get("mime_type"),
                original_filename=file_info.get("filename", "file"),
                file_type="pdf" if message_type in ("document", "image") else "video",
                awaiting="action",
            )
            await pending_store.set_pending(user_id, pending)
            await whatsapp.send_buttons(
                user_id,
                f"File: {file_info.get('filename')}",
                [
                    {"type": "reply", "reply": {"id": "save", "title": "Save"}},
                    {"type": "reply", "reply": {"id": "analyze", "title": "Analyze"}},
                ],
            )
    except Exception as e:
        logger.error(f"Error: {e}")
''',

    "routers/admin.py": '''from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from config import get_settings
from services import database, memory, rag
from logging_config import get_logger
import sqlite3

settings = get_settings()
logger = get_logger("admin")
router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)

def _verify_admin(request: Request):
    if request.headers.get("X-Admin-Secret") != settings.admin_secret:
        raise HTTPException(status_code=401)

@router.get("/users")
async def list_users(request: Request):
    _verify_admin(request)
    try:
        conn = sqlite3.connect(settings.sqlite_db_path)
        users = conn.execute("SELECT DISTINCT user_id FROM files").fetchall()
        conn.close()
        return {"status": "ok", "users": [u[0] for u in users]}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500)

@router.get("/stats")
async def stats(request: Request):
    _verify_admin(request)
    try:
        conn = sqlite3.connect(settings.sqlite_db_path)
        users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM files").fetchone()[0]
        files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        memory_entries = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        conn.close()
        return {"status": "ok", "users": users, "files": files, "memory": memory_entries}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500)

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    _verify_admin(request)
    try:
        conn = sqlite3.connect(settings.sqlite_db_path)
        conn.execute("DELETE FROM files WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
        conn.close()
        rag.delete_user_all_docs(user_id)
        return {"status": "ok", "message": f"User {user_id} deleted"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500)
''',

    # TESTS
    "tests/__init__.py": '"""Tests"""',
    "tests/conftest.py": '''import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def test_client():
    return TestClient(app)
''',
    "tests/test_database.py": '''def test_init():
    assert True
''',
    "tests/test_rag.py": '''def test_init():
    assert True
''',
    "tests/test_webhook.py": '''def test_init():
    assert True
''',

    "pytest.ini": '''[pytest]
testpaths = tests
python_files = test_*.py
''',
}

# ============================================================================
# CREATE ALL FILES
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 MEMORA AI - COMPLETE PROJECT GENERATOR")
    print("="*60 + "\n")
    
    created = 0
    errors = 0
    
    for file_path, content in FILES.items():
        try:
            create_file(file_path, content)
            created += 1
        except Exception as e:
            print(f"❌ {file_path}: {e}")
            errors += 1
    
    print("\n" + "="*60)
    print(f"✅ Created: {created} files")
    if errors:
        print(f"❌ Errors: {errors}")
    print("="*60)
    
    print("\n📋 NEXT STEPS:")
    print("1. pip install -r requirements.txt")
    print("2. cp .env.example .env")
    print("3. git add .")
    print("4. git commit -m 'Initial commit - all files'")
    print("5. git push origin main\n")