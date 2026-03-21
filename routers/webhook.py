import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from config import get_settings
from logging_config import get_logger
from models.schemas import PendingUpload
from services import agent, database, drive, memory, rag, whatsapp
from services.pending_store import delete_pending, get_pending, set_pending


settings = get_settings()
logger = get_logger("webhook")
router = APIRouter()


def _extract_messages(body: Dict[str, Any]) -> List[Dict[str, Any]]:
	extracted: List[Dict[str, Any]] = []
	for entry in body.get("entry", []):
		for change in entry.get("changes", []):
			value = change.get("value", {})
			for message in value.get("messages", []):
				extracted.append(message)
	return extracted


def _detect_file_type(message_type: str, mime_type: str) -> str:
	if message_type == "video":
		return "video"
	if "pdf" in (mime_type or "").lower():
		return "pdf"
	return "image"


def _parse_message(message: Dict[str, Any]) -> Dict[str, Any]:
	message_type = message.get("type", "")
	parsed: Dict[str, Any] = {
		"from_number": message.get("from"),
		"message_id": message.get("id"),
		"message_type": message_type,
		"text": None,
		"media_id": None,
		"mime_type": None,
		"filename": None,
		"button_reply_id": None,
		"button_reply_title": None,
	}

	if message_type == "text":
		parsed["text"] = message.get("text", {}).get("body", "")
	elif message_type in {"document", "image", "video"}:
		media = message.get(message_type, {})
		parsed["media_id"] = media.get("id")
		parsed["mime_type"] = media.get("mime_type", "")
		parsed["filename"] = media.get("filename") or f"upload.{message_type}"
	elif message_type == "interactive":
		interactive = message.get("interactive", {})
		if interactive.get("type") == "button_reply":
			reply = interactive.get("button_reply", {})
			parsed["button_reply_id"] = reply.get("id")
			parsed["button_reply_title"] = reply.get("title")
		elif interactive.get("type") == "list_reply":
			reply = interactive.get("list_reply", {})
			parsed["button_reply_id"] = reply.get("id")
			parsed["button_reply_title"] = reply.get("title")

	return parsed


async def _send_and_store_assistant(user_id: str, text: str) -> None:
	memory.add_memory(user_id, "assistant", text)
	await whatsapp.send_text(user_id, text)


def _build_file_list_text(files: List[Dict[str, Any]]) -> str:
	lines = [f"{idx}. {f['file_name']}" for idx, f in enumerate(files, start=1)]
	return "Your files:\n" + "\n".join(lines)


def _build_list_rows(files: List[Dict[str, Any]]) -> List[Dict[str, str]]:
	return [
		{
			"id": f"file_{f['id']}",
			"title": f["file_name"][:24],
			"description": f"Type: {f.get('file_type', 'file')}",
		}
		for f in files[:10]
	]


async def _handle_action_save(user_id: str) -> Optional[str]:
	pending = await get_pending(user_id)
	if not pending:
		await _send_and_store_assistant(user_id, "No pending file found.")
		return "No pending file found."

	local_path = os.path.join("./temp_files", f"{user_id}_{pending.original_filename}")
	try:
		await whatsapp.download_media(pending.media_id, local_path)
		drive_file_id = drive.upload_file(user_id, local_path, pending.original_filename, pending.file_type)
		database.save_file_metadata(user_id, pending.original_filename, pending.file_type, drive_file_id, pending.file_type)
		if pending.file_type == "pdf":
			rag.index_pdf(user_id, pending.original_filename, local_path)
		await _send_and_store_assistant(user_id, f"Saved {pending.original_filename}.")
		return f"Saved {pending.original_filename}."
	finally:
		await delete_pending(user_id)
		if os.path.exists(local_path):
			os.remove(local_path)


async def _handle_action_rename(user_id: str) -> Optional[str]:
	pending = await get_pending(user_id)
	if not pending:
		await _send_and_store_assistant(user_id, "No pending file found.")
		return "No pending file found."

	pending.awaiting = "rename"
	await set_pending(user_id, pending)
	await _send_and_store_assistant(user_id, "Send me the new filename")
	return "Send me the new filename"


async def _handle_action_analyze(user_id: str) -> Optional[str]:
	pending = await get_pending(user_id)
	if not pending:
		await _send_and_store_assistant(user_id, "No pending file found.")
		return "No pending file found."
	if pending.file_type != "pdf":
		await _send_and_store_assistant(user_id, "Analyze is currently available for PDF files only.")
		return "Analyze is currently available for PDF files only."

	local_path = os.path.join("./temp_files", f"{user_id}_{pending.original_filename}")
	try:
		await whatsapp.download_media(pending.media_id, local_path)
		chunks = rag.extract_pdf_chunks(local_path)
		joined_text = "\n\n".join(chunk for chunk, _ in chunks)
		summary = agent.generate_summary(joined_text, pending.original_filename)
		await _send_and_store_assistant(user_id, summary)
		drive_file_id = drive.upload_file(user_id, local_path, pending.original_filename, pending.file_type)
		database.save_file_metadata(user_id, pending.original_filename, pending.file_type, drive_file_id, pending.file_type)
		rag.index_pdf(user_id, pending.original_filename, local_path)
		return summary
	finally:
		await delete_pending(user_id)
		if os.path.exists(local_path):
			os.remove(local_path)


async def _handle_file_selection(user_id: str, selected_id: str) -> Optional[str]:
	try:
		file_id = int(selected_id.split("_", 1)[1])
	except Exception:
		await _send_and_store_assistant(user_id, "Invalid file selection.")
		return "Invalid file selection."

	record = database.get_file_by_id(file_id, user_id)
	if not record:
		await _send_and_store_assistant(user_id, "File not found.")
		return "File not found."

	local_path = os.path.join("./temp_files", f"{user_id}_{record['file_name']}")
	try:
		drive.download_file(record["drive_file_id"], local_path)
		await whatsapp.send_document(user_id, local_path, record["file_name"], "Requested file")
		response = f"Sent {record['file_name']}."
		memory.add_memory(user_id, "assistant", response)
		return response
	finally:
		if os.path.exists(local_path):
			os.remove(local_path)


async def _handle_text_message(user_id: str, text: str) -> Optional[str]:
	pending = await get_pending(user_id)
	if pending and pending.awaiting == "rename":
		pending.original_filename = text.strip()
		pending.awaiting = "action"
		await set_pending(user_id, pending)
		await _send_and_store_assistant(user_id, f"Filename updated to {pending.original_filename}. Tap Save to continue.")
		return f"Filename updated to {pending.original_filename}. Tap Save to continue."

	memory.add_memory(user_id, "user", text)
	rag_context = ""
	lowered = text.lower()
	if any(word in lowered for word in ["document", "pdf", "file", "notes", "what does", "find"]):
		prefetched = rag.query_documents(user_id, text, top_k=3)
		if prefetched:
			rag_context = "\n".join(
				[f"[{c['file_name']} p.{c['page']}] {c['text'][:180]}" for c in prefetched]
			)

	detected = agent.detect_intent_and_respond(user_id, text, rag_context)
	intent = detected.get("intent", "chitchat")

	if intent == "list_files":
		files = database.list_files(user_id)
		if not files:
			await _send_and_store_assistant(user_id, "You have no saved files yet.")
			return "You have no saved files yet."
		response = _build_file_list_text(files)
		await _send_and_store_assistant(user_id, response)
		return response

	if intent == "retrieve_file":
		file_number = detected.get("file_number")
		if file_number:
			file_obj = database.get_file_by_id(int(file_number), user_id)
			if file_obj:
				local_path = os.path.join("./temp_files", f"{user_id}_{file_obj['file_name']}")
				try:
					drive.download_file(file_obj["drive_file_id"], local_path)
					await whatsapp.send_document(user_id, local_path, file_obj["file_name"], "Here is your file")
					response = f"Sent {file_obj['file_name']}."
					memory.add_memory(user_id, "assistant", response)
					return response
				finally:
					if os.path.exists(local_path):
						os.remove(local_path)

		file_query = detected.get("file_query") or text
		matches = database.find_files_by_name(user_id, file_query)
		if not matches:
			await _send_and_store_assistant(user_id, "No files matched your request.")
			return "No files matched your request."
		if len(matches) > 1:
			await whatsapp.send_list_message(user_id, "Select a file", _build_list_rows(matches))
			reply = "I found multiple files. Please select one from the list."
			memory.add_memory(user_id, "assistant", reply)
			return reply

		only = matches[0]
		local_path = os.path.join("./temp_files", f"{user_id}_{only['file_name']}")
		try:
			drive.download_file(only["drive_file_id"], local_path)
			await whatsapp.send_document(user_id, local_path, only["file_name"], "Here is your file")
		finally:
			if os.path.exists(local_path):
				os.remove(local_path)
		response = f"Sent {only['file_name']}."
		memory.add_memory(user_id, "assistant", response)
		return response

	if intent == "rag_query":
		rag_query = detected.get("rag_query") or text
		docs = rag.query_documents(user_id, rag_query, top_k=5)
		if not docs:
			await _send_and_store_assistant(user_id, "I could not find relevant passages in your documents.")
			return "I could not find relevant passages in your documents."
		answer = agent.generate_rag_answer(user_id, rag_query, docs)
		await _send_and_store_assistant(user_id, answer)
		return answer

	if intent == "summarize_file":
		query = detected.get("file_query") or text
		matches = database.find_files_by_name(user_id, query)
		if not matches:
			await _send_and_store_assistant(user_id, "I could not find that file to summarize.")
			return "I could not find that file to summarize."
		if len(matches) > 1:
			await whatsapp.send_list_message(user_id, "Select a file to summarize", _build_list_rows(matches))
			reply = "I found multiple files. Please select one from the list."
			memory.add_memory(user_id, "assistant", reply)
			return reply

		target = matches[0]
		local_path = os.path.join("./temp_files", f"{user_id}_{target['file_name']}")
		try:
			drive.download_file(target["drive_file_id"], local_path)
			if target.get("file_type") == "pdf":
				chunks = rag.extract_pdf_chunks(local_path)
				joined = "\n\n".join(chunk for chunk, _ in chunks)
				summary = agent.generate_summary(joined, target["file_name"])
			else:
				summary = "Summaries are currently optimized for PDF files."
			await _send_and_store_assistant(user_id, summary)
			return summary
		finally:
			if os.path.exists(local_path):
				os.remove(local_path)

	response_text = detected.get("response_text") or "Okay."
	await _send_and_store_assistant(user_id, response_text)
	return response_text


async def process_message(message: Dict[str, Any]) -> None:
	parsed = _parse_message(message)
	user_id = parsed["from_number"]
	if not user_id:
		return

	message_type = parsed["message_type"]
	if message_type == "text":
		text = (parsed.get("text") or "").strip()
		if text:
			await _handle_text_message(user_id, text)
		return

	if message_type in {"document", "image", "video"}:
		pending = PendingUpload(
			user_id=user_id,
			media_id=parsed.get("media_id") or "",
			media_mime_type=parsed.get("mime_type") or "",
			original_filename=parsed.get("filename") or "upload.bin",
			file_type=_detect_file_type(message_type, parsed.get("mime_type") or ""),
			awaiting="action",
		)
		await set_pending(user_id, pending)
		await whatsapp.send_buttons(
			user_id,
			f"Received {pending.original_filename}. Choose an action:",
			[
				{"type": "reply", "reply": {"id": "action_save", "title": "Save"}},
				{"type": "reply", "reply": {"id": "action_rename", "title": "Rename"}},
				{"type": "reply", "reply": {"id": "action_analyze", "title": "Analyze"}},
			],
		)
		return

	if message_type == "interactive":
		action_id = parsed.get("button_reply_id") or ""
		if action_id == "action_save":
			await _handle_action_save(user_id)
			return
		if action_id == "action_rename":
			await _handle_action_rename(user_id)
			return
		if action_id == "action_analyze":
			await _handle_action_analyze(user_id)
			return
		if action_id.startswith("file_"):
			await _handle_file_selection(user_id, action_id)
			return
		await _send_and_store_assistant(user_id, "Unknown action selected.")


@router.get("/webhook")
async def verify_webhook(request: Request):
	mode = request.query_params.get("hub.mode")
	token = request.query_params.get("hub.verify_token")
	challenge = request.query_params.get("hub.challenge", "")
	if mode == "subscribe" and token == settings.whatsapp_verify_token:
		return PlainTextResponse(challenge)
	raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
	try:
		body = await request.json()
	except Exception:
		logger.exception("Invalid JSON body for webhook")
		return {"status": "ok"}

	try:
		for message in _extract_messages(body):
			background_tasks.add_task(process_message, message)
	except Exception:
		logger.exception("Failed to schedule webhook background processing")

	return {"status": "ok"}

