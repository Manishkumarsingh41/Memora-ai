# 🧠 Memora AI

Chat with your files on WhatsApp using AI

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![Tests](https://img.shields.io/badge/Tests-28%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 1. PROJECT TITLE & DESCRIPTION

# 🧠 Memora AI

Chat with your files on WhatsApp using AI

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![Tests](https://img.shields.io/badge/Tests-28%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 2. WHAT IT DOES

- Send PDF, image, or video on WhatsApp
- AI asks: Save, Rename, or Analyze
- Ask questions about your documents
- AI answers with citations (Source: file, page X)
- Remembers your past conversations
- Files are stored on Google Drive

## 3. TECH STACK

| What | Technology |
|------|------------|
| AI Brain | Claude Sonnet (Anthropic) |
| Backend | FastAPI |
| File Storage | Google Drive |
| Smart Search | ChromaDB + sentence-transformers |
| Memory | SQLite |
| Cache | Redis |
| Messaging | WhatsApp Business API |
| Container | Docker |

## 4. PREREQUISITES

- WhatsApp Business Account
- Anthropic API Key (console.anthropic.com)
- Google Cloud Service Account + credentials.json
- Ngrok account (ngrok.com) - free
- Python 3.11 OR Google Colab (no install needed)

## 5. OPTION A — RUN ON LOCAL (Windows/Mac/Linux)

### Step 1 - Clone the repo

```bash
git clone https://github.com/Manishkumarsingh41/Memora-ai.git
cd Memora-ai
```

### Step 2 - Install Python 3.11

Download from https://python.org

⚠️ Check Add Python to PATH during install

### Step 3 - Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 - Setup environment

Copy .env.example to .env
Fill in your API keys

### Step 5 - Run the app

```bash
uvicorn main:app --reload
```

### Step 6 - Expose to internet (for WhatsApp)

```bash
ngrok http 8000
```

Copy the HTTPS URL and paste it in Meta Developer Console

## 6. OPTION B — RUN ON GOOGLE COLAB (easiest, no install)

### Step 1 - Open new Colab notebook

👉 https://colab.research.google.com

### Step 2 - Clone and install

```python
!git clone https://github.com/Manishkumarsingh41/Memora-ai.git
%cd Memora-ai
!pip install -r requirements.txt -q
```

### Step 3 - Install Redis

```python
!apt-get install -y redis-server -q
!redis-server --daemonize yes
```

### Step 4 - Create .env file

```python
%%writefile .env
WHATSAPP_ACCESS_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=memora_verify_token
ANTHROPIC_API_KEY=your_key_here
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_ROOT_FOLDER=AI-Storage
REDIS_URL=redis://localhost:6379
ADMIN_SECRET=admin123
SECRET_KEY=mysecretkey
DEBUG=true
SQLITE_DB_PATH=./memora.db
CHROMA_DB_PATH=./chroma_db
TEMP_DIR=./temp_files
```

### Step 5 - Upload credentials.json

```python
from google.colab import files
uploaded = files.upload()  # upload your credentials.json here
```

### Step 6 - Initialize database

```python
!python -c "from services.database import init_db; init_db()"
```

### Step 7 - Install ngrok

```python
!pip install pyngrok -q
from pyngrok import ngrok
ngrok.set_auth_token("your_ngrok_token_here")
```

### Step 8 - Start the app

```python
import subprocess, threading, time
def run():
    subprocess.run(["uvicorn", "main:app",
                   "--host", "0.0.0.0", "--port", "8000"])
threading.Thread(target=run, daemon=True).start()
time.sleep(3)
url = ngrok.connect(8000)
print(f"✅ App running at: {url}")
print(f"📌 Webhook URL: {url}/webhook")
print("👆 Copy webhook URL → paste in Meta Developer Console")
```

⚠️ Note: Colab disconnects after about 1 hour of inactivity

✅ Best for: testing and development

## 7. WHATSAPP SETUP

1. Go to developers.facebook.com
2. Create App and add WhatsApp product
3. Get Access Token and Phone Number ID
4. Set Webhook URL: your ngrok or server URL + /webhook
5. Set Verify Token: same as WHATSAPP_VERIFY_TOKEN in .env
6. Subscribe to: messages

## 8. GOOGLE DRIVE SETUP

1. Go to console.cloud.google.com
2. Create project
3. Enable Google Drive API
4. Create Service Account
5. Download JSON key and save as credentials.json
6. Share your Drive folder with service account email

## 9. WHATSAPP COMMANDS

| Command | What happens |
|---------|--------------|
| Send any PDF | Bot asks Save/Rename/Analyze |
| show my files | Lists all your files |
| send resume.pdf | Bot sends the file |
| file 2 bhejo | Sends file number 2 |
| summarize this doc | AI gives summary |
| is pdf me kya hai | Searches document |
| maine kal kya bola | Shows past chat |

## 10. RUNNING TESTS

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock httpx fpdf2

# Run all tests
py -3.11 -m pytest -v

# Expected result:
28 passed in ~8 seconds ✅
```

Test coverage:

- test_database.py → 10 tests (file storage, memory)
- test_rag.py → 6 tests (PDF search, indexing)
- test_webhook.py → 12 tests (WhatsApp flow)

## 11. PROJECT STRUCTURE

```text
Memora-ai/
├── main.py              → App entry point
├── config.py            → All settings
├── logging_config.py    → Log rotation
├── Dockerfile           → Container setup
├── docker-compose.yml   → App + Redis
├── requirements.txt     → Dependencies
├── .env.example         → Environment template
├── models/
│   ├── schemas.py       → Data models
│   └── errors.py        → Error responses
├── routers/
│   ├── webhook.py       → WhatsApp handler
│   └── admin.py         → Admin panel
├── services/
│   ├── whatsapp.py      → WhatsApp API
│   ├── drive.py         → Google Drive
│   ├── rag.py           → Smart search
│   ├── agent.py         → Claude AI
│   ├── database.py      → SQLite
│   ├── memory.py        → Chat memory
│   └── pending_store.py → Redis cache
└── tests/
    ├── test_database.py
    ├── test_rag.py
    └── test_webhook.py
```

## 12. DOCKER SETUP

```bash
docker-compose up --build
```

App runs on http://localhost:8000

## 13. TROUBLESHOOTING

Q: WhatsApp not receiving messages?
A: Check ngrok is running and webhook URL is HTTPS.

Q: Files not uploading to Drive?
A: Check credentials.json exists and Drive API is enabled.

Q: Redis connection failed?
A: Run: docker-compose up redis

Q: Tests failing?
A: Run: py -3.11 -m pytest -v (use Python 3.11, not 3.14).

Q: Pillow install error?
A: Use Python 3.11, not 3.14.

## 14. AUTHOR

Made by Manish Kumar Singh
GitHub: @Manishkumarsingh41

## 15. LICENSE

MIT - free to use and modify
