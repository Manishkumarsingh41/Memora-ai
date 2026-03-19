import httpx
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
