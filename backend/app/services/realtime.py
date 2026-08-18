from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Callable

from redis import asyncio as aioredis

from ..config import settings


class DistributedSocketManager:
    """Local WebSocket fan-out backed by Redis pub/sub for multi-instance use."""

    def __init__(self, namespace: str, on_user_offline: Callable[[int], None] | None = None):
        self.namespace = namespace
        self.instance_id = f"{namespace}-{uuid.uuid4().hex}"
        self.active = {}
        self.on_user_offline = on_user_offline
        self._listener = None
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def connect(self, user_id, ws):
        await ws.accept()
        self.active.setdefault(user_id, set()).add(ws)
        await self._presence(user_id, True)
        if self._listener is None or self._listener.done():
            self._listener = asyncio.create_task(self._listen())

    def disconnect(self, user_id, ws):
        sockets = self.active.get(user_id, set())
        sockets.discard(ws)
        if not sockets:
            self.active.pop(user_id, None)
            asyncio.create_task(self._presence(user_id, False))
            if self.on_user_offline:
                self.on_user_offline(user_id)

    async def touch(self, user_id: int):
        try:
            await self._redis.zadd(f"presence:{user_id}", {self.instance_id: time.time()})
            await self._redis.expire(f"presence:{user_id}", 180)
        except Exception:
            pass

    async def _presence(self, user_id: int, online: bool):
        try:
            key = f"presence:{user_id}"
            if online:
                await self.touch(user_id)
            else:
                await self._redis.zrem(key, self.instance_id)
        except Exception:
            pass

    async def _send_local(self, user_id: int, payload: dict):
        dead = []
        for ws in list(self.active.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def send_user(self, user_id: int, payload: dict):
        await self._send_local(user_id, payload)
        try:
            envelope = json.dumps({"source": self.instance_id, "payload": payload}, default=str)
            await self._redis.publish(f"socialn:{self.namespace}:{user_id}", envelope)
        except Exception:
            pass

    async def send(self, user_id: int, payload: dict):
        await self.send_user(user_id, payload)

    async def _listen(self):
        while True:
            pubsub = self._redis.pubsub()
            try:
                await pubsub.psubscribe(f"socialn:{self.namespace}:*")
                async for message in pubsub.listen():
                    if message.get("type") != "pmessage":
                        continue
                    envelope = json.loads(message["data"])
                    if envelope.get("source") == self.instance_id:
                        continue
                    user_id = int(message["channel"].rsplit(":", 1)[-1])
                    await self._send_local(user_id, envelope["payload"])
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(2)
            finally:
                await pubsub.aclose()


async def user_is_online(user_id: int) -> bool:
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        key = f"presence:{user_id}"
        await client.zremrangebyscore(key, 0, time.time() - 150)
        return bool(await client.zcard(key))
    except Exception:
        return False
    finally:
        await client.aclose()
