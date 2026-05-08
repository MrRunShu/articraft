import json
import redis.asyncio as redis
from typing import Optional

from app.config import settings

redis_client: Optional[redis.Redis] = None


async def init_redis():
    global redis_client
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def get_session(session_id: str) -> Optional[dict]:
    if not redis_client:
        return None
    data = await redis_client.get(_session_key(session_id))
    return json.loads(data) if data else None


async def set_session(session_id: str, data: dict, expire: Optional[int] = None):
    if not redis_client:
        return
    await redis_client.setex(
        _session_key(session_id),
        expire or settings.session_max_age,
        json.dumps(data),
    )


async def remove_session(session_id: str):
    if not redis_client:
        return
    await redis_client.delete(_session_key(session_id))
