import json
import logging
from functools import lru_cache

from redis import Redis

from ..config import settings

logger = logging.getLogger(__name__)


@lru_cache
def redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)


def get_json(key: str):
    try:
        value = redis_client().get(key)
        return json.loads(value) if value else None
    except Exception as exc:
        logger.debug("redis_cache_get_failed", extra={"key": key, "error": str(exc)})
        return None


def set_json(key: str, value, ttl: int = 60) -> None:
    try:
        redis_client().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("redis_cache_set_failed", extra={"key": key, "error": str(exc)})


def delete(*keys: str) -> None:
    if not keys:
        return
    try:
        redis_client().delete(*keys)
    except Exception as exc:
        logger.debug("redis_cache_delete_failed", extra={"error": str(exc)})


def healthy() -> bool:
    try:
        return bool(redis_client().ping())
    except Exception:
        return False
