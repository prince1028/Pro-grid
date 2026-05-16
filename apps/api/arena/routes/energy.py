from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arena.deps import SessionDep
from arena.repositories import energy as energy_repo
from arena.schemas.energy import (
    EnergySnapshot,
    RegionMeta,
    RegionSnapshot,
    SeriesPoint,
    SeriesResponse,
)
from arena.services.state import get_state

router = APIRouter()

_WINDOWS: dict[str, timedelta] = {
    "5m": timedelta(minutes=5),
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
}


@router.get("/snapshot", response_model=EnergySnapshot)
async def snapshot() -> EnergySnapshot:
    state = get_state()
    with state.lock():
        regions = list(state.regions.values())
        ts = state.last_tick_at or datetime.now(timezone.utc)
        carbon = state.carbon_avoided_kg_total

    by_region = [
        RegionSnapshot(
            region=r.id,
            name=r.name,
            lat=r.lat,
            lng=r.lng,
            generation_mw=r.generation_mw,
            demand_mw=r.demand_mw,
            surplus_mw=r.surplus_mw,
            renewable_share=r.renewable_share,
        )
        for r in regions
    ]
    agg_gen = sum(r.generation_mw for r in regions)
    agg_dem = sum(r.demand_mw for r in regions)
    agg_share = (
        sum(r.renewable_share * r.generation_mw for r in regions) / agg_gen
        if agg_gen > 0
        else 0.0
    )
    return EnergySnapshot(
        timestamp=ts,
        generation_mw=round(agg_gen, 2),
        demand_mw=round(agg_dem, 2),
        surplus_mw=round(agg_gen - agg_dem, 2),
        renewable_share=round(agg_share, 3),
        carbon_avoided_kg=round(carbon, 2),
        by_region=by_region,
    )


@router.get("/series", response_model=SeriesResponse)
async def series(
    session: Annotated[AsyncSession, SessionDep],
    window: str = Query("1h", regex="^(5m|1h|24h)$"),
    bucket: int = Query(60, ge=1, le=3600, description="Bucket size in seconds"),
    region: str | None = None,
) -> SeriesResponse:
    pts = await energy_repo.series(
        session, window=_WINDOWS[window], bucket_s=bucket, region_id=region
    )
    return SeriesResponse(
        bucket_s=bucket,
        points=[SeriesPoint(t=t, gen=g, dem=d, sur=s) for (t, g, d, s) in pts],
    )


@router.get("/regions", response_model=list[RegionMeta])
async def regions() -> list[RegionMeta]:
    state = get_state()
    with state.lock():
        return [
            RegionMeta(
                id=r.id,
                name=r.name,
                lat=r.lat,
                lng=r.lng,
                installed_solar_kw=r.installed_solar_kw,
                installed_wind_kw=r.installed_wind_kw,
                installed_hydro_kw=r.installed_hydro_kw,
            )
            for r in state.regions.values()
        ]
