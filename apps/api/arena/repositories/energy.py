from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from arena.models import EnergyTick


async def insert_tick(session: AsyncSession, tick: EnergyTick) -> EnergyTick:
    session.add(tick)
    await session.flush()
    return tick


async def latest_per_region(session: AsyncSession) -> list[EnergyTick]:
    """Return one row per region, the most recent tick."""
    # Window-functions vary by backend; do a two-step pull instead.
    subq = (
        select(EnergyTick.region_id, func.max(EnergyTick.ts).label("max_ts"))
        .group_by(EnergyTick.region_id)
        .subquery()
    )
    stmt = select(EnergyTick).join(
        subq, (EnergyTick.region_id == subq.c.region_id) & (EnergyTick.ts == subq.c.max_ts)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def series(
    session: AsyncSession,
    *,
    window: timedelta,
    bucket_s: int,
    region_id: str | None = None,
) -> list[tuple[datetime, float, float, float]]:
    """Return downsampled (ts, gen, dem, sur) points across the window.

    For SQLite + MVP simplicity we pull raw points and bucket in Python.
    A production Postgres deployment should use date_trunc / time_bucket.
    """
    cutoff = datetime.now(timezone.utc) - window
    stmt = (
        select(
            EnergyTick.ts,
            EnergyTick.generation_mw,
            EnergyTick.demand_mw,
            EnergyTick.surplus_mw,
        )
        .where(EnergyTick.ts >= cutoff)
        .order_by(EnergyTick.ts.asc())
    )
    if region_id is not None:
        stmt = stmt.where(EnergyTick.region_id == region_id)
    rows = (await session.execute(stmt)).all()
    if not rows:
        return []

    buckets: dict[int, list[tuple[float, float, float]]] = {}
    start = int(rows[0][0].timestamp())
    for ts, gen, dem, sur in rows:
        key = (int(ts.timestamp()) - start) // bucket_s
        buckets.setdefault(key, []).append((gen, dem, sur))

    points = []
    for key in sorted(buckets):
        vals = buckets[key]
        g = sum(v[0] for v in vals) / len(vals)
        d = sum(v[1] for v in vals) / len(vals)
        s = sum(v[2] for v in vals) / len(vals)
        ts = datetime.fromtimestamp(start + key * bucket_s, tz=timezone.utc)
        points.append((ts, g, d, s))
    return points


async def recent_aggregate(session: AsyncSession, window: timedelta) -> dict[str, float]:
    cutoff = datetime.now(timezone.utc) - window
    stmt = select(
        func.coalesce(func.avg(EnergyTick.generation_mw), 0),
        func.coalesce(func.avg(EnergyTick.demand_mw), 0),
        func.coalesce(func.avg(EnergyTick.surplus_mw), 0),
        func.coalesce(func.sum(EnergyTick.carbon_avoided_kg), 0),
        func.coalesce(func.avg(EnergyTick.renewable_share), 0),
    ).where(EnergyTick.ts >= cutoff)
    row = (await session.execute(stmt)).one()
    return {
        "avg_gen_mw": float(row[0]),
        "avg_dem_mw": float(row[1]),
        "avg_sur_mw": float(row[2]),
        "carbon_avoided_kg": float(row[3]),
        "avg_renewable_share": float(row[4]),
    }


async def latest_tick(session: AsyncSession) -> EnergyTick | None:
    stmt = select(EnergyTick).order_by(desc(EnergyTick.ts)).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()
