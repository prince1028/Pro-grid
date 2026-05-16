"""FastAPI app entrypoint.

Wires routes, CORS, the WebSocket hub, and the background simulation task.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arena import __version__
from arena.config import get_settings
from arena.core.db import init_db
from arena.core.logging import configure_logging, get_logger
from arena.core.redis import close_redis, get_redis
from arena.routes import ai, analytics, blockchain, compute, energy, health, nodes
from arena.services.engine import SimulationEngine
from arena.seed import maybe_seed
from arena.ws.hub import Hub, get_hub
from arena.ws.routes import router as ws_router

log = get_logger("arena.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.api_log_level)
    log.info("starting arena-grid api", extra={"ctx_version": __version__})

    await init_db()
    if settings.sim_autoseed:
        await maybe_seed()

    hub: Hub = get_hub()
    engine = SimulationEngine(hub=hub, redis=get_redis(), tick_s=settings.sim_tick_seconds)
    app.state.engine = engine
    app.state.hub = hub

    task = asyncio.create_task(engine.run(), name="arena.sim")
    log.info("simulation engine started", extra={"ctx_tick_s": settings.sim_tick_seconds})
    try:
        yield
    finally:
        log.info("shutting down")
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ARENA-GRID API",
        version=__version__,
        description="Renewable-powered compute simulation engine.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(energy.router, prefix="/api/energy", tags=["energy"])
    app.include_router(compute.router, prefix="/api/compute", tags=["compute"])
    app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])
    app.include_router(blockchain.router, prefix="/api/blockchain", tags=["blockchain"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
    app.include_router(ws_router)
    return app


app = create_app()
