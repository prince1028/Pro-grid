from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arena.models import Workload, WorkloadState


async def list_workloads(
    session: AsyncSession,
    *,
    state: WorkloadState | None = None,
    limit: int = 200,
) -> list[Workload]:
    stmt = select(Workload).order_by(Workload.created_at.desc()).limit(limit)
    if state is not None:
        stmt = stmt.where(Workload.state == state)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_workload(session: AsyncSession, workload_id: str) -> Workload | None:
    return await session.get(Workload, workload_id)


async def add_workload(session: AsyncSession, w: Workload) -> Workload:
    session.add(w)
    await session.flush()
    return w
