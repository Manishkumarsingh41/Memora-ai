import sys
import types
from unittest.mock import MagicMock

# Mock heavy libraries before any import
sys.modules['sentence_transformers'] = MagicMock()

try:
    import chromadb as _real_chromadb
    import chromadb.config as _real_chromadb_config
    sys.modules['chromadb'] = _real_chromadb
    sys.modules['chromadb.config'] = _real_chromadb_config
except Exception:
    chromadb_mock = types.ModuleType('chromadb')
    chromadb_mock.PersistentClient = MagicMock()
    chromadb_mock.config = types.ModuleType('chromadb.config')
    chromadb_mock.config.Settings = MagicMock()
    sys.modules['chromadb'] = chromadb_mock
    sys.modules['chromadb.config'] = chromadb_mock.config

sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.service_account'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()
sys.modules['aioredis'] = MagicMock()
sys.modules['anthropic'] = MagicMock()

import os
from typing import List

import pytest
from fastapi.testclient import TestClient


os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test_token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test_phone")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("ADMIN_SECRET", "test_admin_secret")

from main import app
from services import database, memory, rag


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_memora.db"
    monkeypatch.setattr(database.settings, "sqlite_db_path", str(db_path))
    monkeypatch.setattr(memory.settings, "sqlite_db_path", str(db_path))
    database.init_db()
    return str(db_path)


@pytest.fixture
def tmp_chroma(tmp_path, monkeypatch):
    import chromadb

    real_client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    monkeypatch.setattr(rag, "_chroma_client", real_client)
    monkeypatch.setattr(rag, "_embedder", None)
    yield real_client


@pytest.fixture
def sample_pdf(tmp_path):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="This is page one test content about cyclones.", ln=True)
    pdf.cell(200, 10, txt="Cyclones cause sudden draft drops in pressure systems.", ln=True)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="This is page two about spigot size optimization.", ln=True)
    pdf.cell(200, 10, txt="The optimal spigot size allows underflow solids.", ln=True)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="This is page three about general engineering topics.", ln=True)
    path = tmp_path / "test_document.pdf"
    pdf.output(str(path))
    return str(path)


@pytest.fixture
def mock_embedder(monkeypatch):
    class DummyEmbeddings(list):
        def tolist(self):
            return list(self)

    class DummyModel:
        def encode(self, texts: List[str], convert_to_numpy: bool = True):
            vectors = []
            for text in texts:
                seed = float((len(text) % 10) + 1)
                vectors.append([seed, seed + 1.0, seed + 2.0])
            return DummyEmbeddings(vectors)

    model = DummyModel()
    monkeypatch.setattr(rag, "_embedder", model)
    monkeypatch.setattr(rag, "_get_embedder", lambda: model)
    return model
