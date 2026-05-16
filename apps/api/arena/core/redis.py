"""Redis client with an in-memory fallback for zero-dep dev mode.

Both backends expose the same minimal pub/sub + list API used by the rest
of the codebase. We deliberately do not paper over the differences — if you
need Redis features beyond what's here, switch from `memory://` to a real
Redis URL.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis

from arena.config import get_settings


class _MemoryBackend:
    """A drop-in async backend that mimics the slice of Redis we use."""

    def __init__(self) -> None:
        self._lists: dict[str, deque[str]] = defaultdict(deque)
        self._channels: dict[str, list[asyncio.Queue[str]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def lpush(self, key: str, value: str) -> int:
        async with self._lock:
            self._lists[key].appendleft(value)
            return len(self._lists[key])

    async def rpop(self, key: str) -> str | None:
        async with self._lock:
            if self._lists[key]:
                return self._lists[key].pop()
            return None

    async def llen(self, key: str) -> int:
        return len(self._lists[key])

    async def publish(self, channel: str, message: str) -> int:
        subs = list(self._channels.get(channel, ()))
        for q in subs:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass
        return len(subs)

    async def subscribe(self, channel: str) -> AsyncIterator[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1024)
        self._channels[channel].append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._channels[channel].remove(q)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


class RedisLike:
    """Uniform façade over either real Redis or the in-memory backend."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._memory: _MemoryBackend | None = None
        self._real: aioredis.Redis | None = None
        if url.startswith("memory://"):
            self._memory = _MemoryBackend()
        else:
            self._real = aioredis.from_url(url, decode_responses=True)

    @property
    def kind(self) -> str:
        return "memory" if self._memory else "redis"

    async def lpush(self, key: str, value: str) -> int:
        if self._memory:
            return await self._memory.lpush(key, value)
        assert self._real
        return await self._real.lpush(key, value)

    async def rpop(self, key: str) -> str | None:
        if self._memory:
            return await self._memory.rpop(key)
        assert self._real
        return await self._real.rpop(key)

    async def llen(self, key: str) -> int:
        if self._memory:
            return await self._memory.llen(key)
        assert self._real
        return await self._real.llen(key)

    async def publish(self, channel: str, message: str) -> int:
        if self._memory:
            return await self._memory.publish(channel, message)
        assert self._real
        return await self._real.publish(channel, message)

    async def subscribe(self, channel: str) -> AsyncIterator[str]:
        if self._memory:
            async for msg in self._memory.subscribe(channel):
                yield msg
            return
        assert self._real
        pubsub = self._real.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for msg in pubsub.listen():
                if msg.get("type") == "message":
                    yield msg["data"]
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def ping(self) -> bool:
        if self._memory:
            return True
        assert self._real
        try:
            return bool(await self._real.ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._real:
            await self._real.close()


_client: RedisLike | None = None


def get_redis() -> RedisLike:
    global _client
    if _client is None:
        _client = RedisLike(get_settings().redis_url)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# Channel + queue key constants
CH_TICK = "arena:ch:tick"
Q_WORKLOAD_SUBMIT = "arena:q:workload_submit"


# Helpers used by services
async def publish_json(channel: str, payload: dict[str, Any]) -> int:
    import orjson

    return await get_redis().publish(channel, orjson.dumps(payload).decode())
