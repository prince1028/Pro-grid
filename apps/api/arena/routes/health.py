from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from arena import __version__
from arena.services.state import get_state
from arena.ws.hub import get_hub

router = APIRouter()
_BOOTED = time.time()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "uptime_s": round(time.time() - _BOOTED, 1),
        "version": __version__,
    }


@router.get("/health/sim")
async def sim_health() -> dict:
    state = get_state()
    last = state.last_tick_at
    age_ms = None
    if last is not None:
        age_ms = (datetime.now(timezone.utc) - last).total_seconds() * 1000
    return {
        "ticking": last is not None,
        "last_tick_at": last.isoformat() if last else None,
        "last_tick_age_ms": round(age_ms, 1) if age_ms is not None else None,
        "tick_count": state.tick_count,
        "ws_subscribers": get_hub().subscriber_count,
    }
