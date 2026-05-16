"""WebSocket endpoint: /ws/sim — streams simulation events to clients."""

from __future__ import annotations

import asyncio
import logging

import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from arena.ws.hub import get_hub

router = APIRouter()
log = logging.getLogger("arena.ws.routes")


@router.websocket("/ws/sim")
async def sim_stream(ws: WebSocket) -> None:
    await ws.accept()
    hub = get_hub()
    sub = await hub.register()
    try:
        # Send hello frame so the client can confirm the channel
        await ws.send_bytes(orjson.dumps({"type": "hello", "v": 1}))

        sender = asyncio.create_task(_pump(ws, sub))
        receiver = asyncio.create_task(_drain_client(ws))
        done, pending = await asyncio.wait(
            {sender, receiver}, return_when=asyncio.FIRST_COMPLETED
        )
        for p in pending:
            p.cancel()
        for d in done:
            exc = d.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, asyncio.CancelledError)):
                log.warning("ws task error: %s", exc)
    finally:
        await hub.unregister(sub)


async def _pump(ws: WebSocket, sub) -> None:
    while True:
        frame = await sub.queue.get()
        await ws.send_bytes(frame)


async def _drain_client(ws: WebSocket) -> None:
    # We accept subscribe messages but they're informational — the hub doesn't
    # actually shard channels in the MVP.
    while True:
        await ws.receive_text()
