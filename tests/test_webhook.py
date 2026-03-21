from unittest.mock import AsyncMock

import pytest

from models.schemas import PendingUpload
from routers import webhook


def _verification_query(token: str):
    return f"/webhook?hub.mode=subscribe&hub.verify_token={token}&hub.challenge=abc123"


def _wrap_message(message):
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def test_webhook_verification_success(test_client):
    response = test_client.get(_verification_query("memora_verify_token"))
    assert response.status_code == 200
    assert response.text == "abc123"


def test_webhook_verification_wrong_token(test_client):
    response = test_client.get(_verification_query("wrong"))
    assert response.status_code == 403


def test_webhook_returns_200_immediately(test_client, monkeypatch):
    monkeypatch.setattr(webhook, "process_message", AsyncMock())
    payload = _wrap_message({"from": "u1", "id": "m1", "type": "text", "text": {"body": "hello"}})
    response = test_client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_text_message_saves_to_memory(monkeypatch):
    add_mock = monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    calls = []

    def add_capture(user_id, role, content):
        calls.append((user_id, role, content))

    monkeypatch.setattr(webhook.memory, "add_memory", add_capture)
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.rag, "query_documents", lambda *args, **kwargs: [])
    monkeypatch.setattr(webhook.agent, "detect_intent_and_respond", lambda *args, **kwargs: {"intent": "chitchat", "response_text": "hi"})
    monkeypatch.setattr(webhook.whatsapp, "send_text", AsyncMock(return_value=True))
    await webhook.process_message({"from": "u1", "id": "m1", "type": "text", "text": {"body": "hello"}})
    assert ("u1", "user", "hello") in calls
    assert ("u1", "assistant", "hi") in calls


@pytest.mark.asyncio
async def test_file_upload_sends_buttons(monkeypatch):
    set_pending_mock = AsyncMock()
    send_buttons_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(webhook, "set_pending", set_pending_mock)
    monkeypatch.setattr(webhook.whatsapp, "send_buttons", send_buttons_mock)
    await webhook.process_message(
        {
            "from": "u1",
            "id": "m2",
            "type": "document",
            "document": {"id": "media1", "mime_type": "application/pdf", "filename": "doc.pdf"},
        }
    )
    assert set_pending_mock.await_count == 1
    assert send_buttons_mock.await_count == 1


@pytest.mark.asyncio
async def test_action_save_uploads_to_drive(monkeypatch):
    pending = PendingUpload(
        user_id="u1",
        media_id="media1",
        media_mime_type="application/pdf",
        original_filename="save.pdf",
        file_type="pdf",
        awaiting="action",
    )
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=pending))
    monkeypatch.setattr(webhook.whatsapp, "download_media", AsyncMock(return_value="./temp_files/u1_save.pdf"))
    monkeypatch.setattr(webhook.drive, "upload_file", lambda *args, **kwargs: "drive-file")
    monkeypatch.setattr(webhook.database, "save_file_metadata", lambda *args, **kwargs: 10)
    monkeypatch.setattr(webhook.rag, "index_pdf", lambda *args, **kwargs: 1)
    monkeypatch.setattr(webhook, "delete_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.whatsapp, "send_text", AsyncMock(return_value=True))
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    response = await webhook._handle_action_save("u1")
    assert "Saved" in response


@pytest.mark.asyncio
async def test_action_rename_asks_for_name(monkeypatch):
    pending = PendingUpload(
        user_id="u1",
        media_id="media1",
        media_mime_type="application/pdf",
        original_filename="rename.pdf",
        file_type="pdf",
        awaiting="action",
    )
    set_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=pending))
    monkeypatch.setattr(webhook, "set_pending", set_mock)
    monkeypatch.setattr(webhook.whatsapp, "send_text", AsyncMock(return_value=True))
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    response = await webhook._handle_action_rename("u1")
    assert response == "Send me the new filename"
    assert set_mock.await_count == 1


@pytest.mark.asyncio
async def test_action_analyze_sends_summary(monkeypatch):
    pending = PendingUpload(
        user_id="u1",
        media_id="media1",
        media_mime_type="application/pdf",
        original_filename="analyze.pdf",
        file_type="pdf",
        awaiting="action",
    )
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=pending))
    monkeypatch.setattr(webhook.whatsapp, "download_media", AsyncMock(return_value="./temp_files/u1_analyze.pdf"))
    monkeypatch.setattr(webhook.rag, "extract_pdf_chunks", lambda *args, **kwargs: [("chunk text", 1)])
    monkeypatch.setattr(webhook.agent, "generate_summary", lambda *args, **kwargs: "summary text")
    monkeypatch.setattr(webhook.drive, "upload_file", lambda *args, **kwargs: "drive-file")
    monkeypatch.setattr(webhook.database, "save_file_metadata", lambda *args, **kwargs: 11)
    monkeypatch.setattr(webhook.rag, "index_pdf", lambda *args, **kwargs: 1)
    monkeypatch.setattr(webhook, "delete_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.whatsapp, "send_text", AsyncMock(return_value=True))
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    response = await webhook._handle_action_analyze("u1")
    assert response == "summary text"


@pytest.mark.asyncio
async def test_list_files_intent(monkeypatch):
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.agent, "detect_intent_and_respond", lambda *args, **kwargs: {"intent": "list_files", "response_text": ""})
    monkeypatch.setattr(webhook.database, "list_files", lambda *args, **kwargs: [{"id": 1, "file_name": "a.pdf"}])
    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(webhook.whatsapp, "send_text", send_mock)
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    monkeypatch.setattr(webhook.rag, "query_documents", lambda *args, **kwargs: [])
    await webhook._handle_text_message("u1", "list my files")
    assert send_mock.await_count == 1


@pytest.mark.asyncio
async def test_retrieve_file_intent(monkeypatch):
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.agent, "detect_intent_and_respond", lambda *args, **kwargs: {"intent": "retrieve_file", "file_query": "a.pdf", "file_number": None, "response_text": ""})
    monkeypatch.setattr(webhook.database, "find_files_by_name", lambda *args, **kwargs: [{"id": 1, "file_name": "a.pdf", "drive_file_id": "d1", "file_type": "pdf"}])
    monkeypatch.setattr(webhook.drive, "download_file", lambda *args, **kwargs: "./temp_files/u1_a.pdf")
    doc_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(webhook.whatsapp, "send_document", doc_mock)
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    monkeypatch.setattr(webhook.rag, "query_documents", lambda *args, **kwargs: [])
    await webhook._handle_text_message("u1", "send a.pdf")
    assert doc_mock.await_count == 1


@pytest.mark.asyncio
async def test_rag_query_intent(monkeypatch):
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.agent, "detect_intent_and_respond", lambda *args, **kwargs: {"intent": "rag_query", "rag_query": "what is memora", "response_text": ""})
    monkeypatch.setattr(webhook.rag, "query_documents", lambda *args, **kwargs: [{"text": "memora info", "file_name": "a.pdf", "page": 1, "distance": 0.2}])
    monkeypatch.setattr(webhook.agent, "generate_rag_answer", lambda *args, **kwargs: "rag answer")
    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(webhook.whatsapp, "send_text", send_mock)
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    await webhook._handle_text_message("u1", "question")
    assert send_mock.await_count == 1


@pytest.mark.asyncio
async def test_multiple_file_matches_sends_list(monkeypatch):
    monkeypatch.setattr(webhook, "get_pending", AsyncMock(return_value=None))
    monkeypatch.setattr(webhook.agent, "detect_intent_and_respond", lambda *args, **kwargs: {"intent": "retrieve_file", "file_query": "report", "file_number": None, "response_text": ""})
    monkeypatch.setattr(
        webhook.database,
        "find_files_by_name",
        lambda *args, **kwargs: [
            {"id": 1, "file_name": "report-1.pdf", "drive_file_id": "d1", "file_type": "pdf"},
            {"id": 2, "file_name": "report-2.pdf", "drive_file_id": "d2", "file_type": "pdf"},
        ],
    )
    list_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(webhook.whatsapp, "send_list_message", list_mock)
    monkeypatch.setattr(webhook.memory, "add_memory", lambda *args, **kwargs: None)
    monkeypatch.setattr(webhook.rag, "query_documents", lambda *args, **kwargs: [])
    await webhook._handle_text_message("u1", "send report")
    assert list_mock.await_count == 1
