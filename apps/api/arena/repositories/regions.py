from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arena.models import Region, RenewableNode


async def list_regions(session: AsyncSession) -> list[Region]:
    result = await session.execute(select(Region).order_by(Region.id))
    return list(result.scalars().all())


async def list_renewable_nodes(session: AsyncSession) -> list[RenewableNode]:
    result = await session.execute(select(RenewableNode).order_by(RenewableNode.id))
    return list(result.scalars().all())
