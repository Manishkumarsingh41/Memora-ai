import json
from typing import Any, Optional

from fastapi import HTTPException

from config import get_settings
from logging_config import get_logger
from models.schemas import PendingUpload


settings = get_settings()
logger = get_logger("pending_store")

PENDING_TTL_SECONDS = 600


_redis: Optional[Any] = None


async def get_redis() -> Any:
	global _redis
	if _redis is None:
		import aioredis

		_redis = await aioredis.from_url(
			settings.redis_url,
			password=settings.redis_password,
			encoding="utf-8",
			decode_responses=True,
		)
	return _redis


async def set_pending(user_id: str, pending: PendingUpload) -> None:
	key = f"pending:{user_id}"
	try:
		redis = await get_redis()
		json_string = json.dumps(pending.model_dump())
		await redis.setex(key, PENDING_TTL_SECONDS, json_string)
	except Exception as exc:
		logger.error("Failed to set pending upload for %s: %s", user_id, exc)
		raise HTTPException(status_code=503, detail="Pending store unavailable")


async def get_pending(user_id: str) -> Optional[PendingUpload]:
	key = f"pending:{user_id}"
	try:
		redis = await get_redis()
		raw = await redis.get(key)
		if raw is None:
			return None
		payload = json.loads(raw)
		return PendingUpload(**payload)
	except Exception as exc:
		logger.warning("Failed to get pending upload for %s: %s", user_id, exc)
		return None


async def delete_pending(user_id: str) -> None:
	key = f"pending:{user_id}"
	try:
		redis = await get_redis()
		await redis.delete(key)
	except Exception as exc:
		logger.warning("Failed to delete pending upload for %s: %s", user_id, exc)


async def close_redis() -> None:
	global _redis
	if _redis is None:
		return
	try:
		await _redis.close()
	except Exception as exc:
		logger.warning("Failed closing Redis connection: %s", exc)
	finally:
		_redis = None

