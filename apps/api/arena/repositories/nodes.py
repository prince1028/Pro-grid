from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arena.models import ComputeNode


async def list_compute_nodes(session: AsyncSession) -> list[ComputeNode]:
    result = await session.execute(select(ComputeNode).order_by(ComputeNode.id))
    return list(result.scalars().all())


async def get_compute_node(session: AsyncSession, node_id: str) -> ComputeNode | None:
    return await session.get(ComputeNode, node_id)
