"""In-process WebSocket broadcast hub.

Subscribers register and receive an asyncio.Queue of pending frames; the
broadcaster fan-outs each event by pushing into every queue. Slow consumers
that fill their queue are dropped — we never block the simulation tick on
a stalled client.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import orjson

log = logging.getLogger("arena.ws.hub")


class Subscriber:
    __slots__ = ("queue",)

    def __init__(self, maxsize: int = 64) -> None:
        self.queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=maxsize)


class Hub:
    def __init__(self) -> None:
        self._subs: set[Subscriber] = set()
        self._lock = asyncio.Lock()

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)

    async def register(self) -> Subscriber:
        sub = Subscriber()
        async with self._lock:
            self._subs.add(sub)
        return sub

    async def unregister(self, sub: Subscriber) -> None:
        async with self._lock:
            self._subs.discard(sub)

    async def broadcast(self, event: dict[str, Any]) -> None:
        if not self._subs:
            return
        frame = orjson.dumps(event)
        drop: list[Subscriber] = []
        for sub in list(self._subs):
            try:
                sub.queue.put_nowait(frame)
            except asyncio.QueueFull:
                log.warning("dropping slow subscriber")
                drop.append(sub)
        if drop:
            async with self._lock:
                for s in drop:
                    self._subs.discard(s)


_hub: Hub | None = None


def get_hub() -> Hub:
    global _hub
    if _hub is None:
        _hub = Hub()
    return _hub
