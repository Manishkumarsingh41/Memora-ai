import json
from typing import Any, Dict, List

from config import get_settings
from logging_config import get_logger

settings = get_settings()
logger = get_logger("agent")
_client: Any = None

INTENT_PROMPT = """You are Memora AI. Respond with ONLY valid JSON:
{"intent": "list_files|retrieve_file|rag_query|summarize_file|chitchat", 
 "response_text": "...", 
 "file_query": null, 
 "file_number": null, 
 "rag_query": null}"""


def _get_client() -> Any:
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client

def detect_intent_and_respond(user_id: str, user_message: str, memory_context: str = "") -> Dict:
    try:
        client = _get_client()
        messages = [{"role": "user", "content": f"{memory_context}\n\nMessage: {user_message}"}]
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
        client = _get_client()
        context = "\n\n".join([f"[{c['file_name']}, page {c['page']}]: {c['text'][:200]}" for c in chunks])
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system="Answer based ONLY on provided context. Include citations.",
            messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Error generating answer"

def generate_summary(file_text: str, file_name: str) -> str:
    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system="Summarize in 5 bullet points",
            messages=[{"role": "user", "content": f"Summarize:\n{file_text[:8000]}"}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Error generating summary"
