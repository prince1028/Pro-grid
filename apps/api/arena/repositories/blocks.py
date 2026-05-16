from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from arena.models import Block


async def list_recent(session: AsyncSession, limit: int = 20) -> list[Block]:
    stmt = select(Block).order_by(desc(Block.height)).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def add_block(session: AsyncSession, b: Block) -> Block:
    session.add(b)
    await session.flush()
    return b


async def stats_24h(session: AsyncSession) -> dict[str, float]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    row = (
        await session.execute(
            select(
                func.coalesce(func.count(Block.id), 0),
                func.coalesce(func.sum(Block.reward_tokens), 0),
                func.coalesce(func.sum(Block.energy_kwh), 0),
            ).where(Block.ts >= cutoff)
        )
    ).one()
    return {
        "blocks_24h": int(row[0]),
        "tokens_24h": float(row[1]),
        "energy_kwh_24h": float(row[2]),
    }


async def max_height(session: AsyncSession) -> int:
    row = (await session.execute(select(func.coalesce(func.max(Block.height), 0)))).scalar_one()
    return int(row or 0)
