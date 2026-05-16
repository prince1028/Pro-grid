from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arena.deps import SessionDep
from arena.repositories import blocks as blocks_repo
from arena.schemas.analytics import BlockchainStats, BlockDTO
from arena.services.state import get_state

router = APIRouter()


@router.get("/blocks", response_model=list[BlockDTO])
async def list_blocks(
    session: Annotated[AsyncSession, SessionDep],
    limit: int = Query(20, ge=1, le=200),
) -> list[BlockDTO]:
    blocks = await blocks_repo.list_recent(session, limit=limit)
    return [
        BlockDTO(
            height=b.height,
            hash=b.hash,
            miner=b.miner,
            reward_tokens=b.reward_tokens,
            energy_kwh=b.energy_kwh,
            ts=b.ts.isoformat(),
        )
        for b in blocks
    ]


@router.get("/stats", response_model=BlockchainStats)
async def stats(session: Annotated[AsyncSession, SessionDep]) -> BlockchainStats:
    s = get_state()
    db = await blocks_repo.stats_24h(session)
    return BlockchainStats(
        hashrate_ths=s.hashrate_ths,
        difficulty=s.difficulty,
        blocks_24h=db["blocks_24h"],
        tokens_24h=db["tokens_24h"],
        energy_kwh_24h=db["energy_kwh_24h"],
    )
