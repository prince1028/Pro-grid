from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arena.deps import SessionDep
from arena.repositories import energy as energy_repo
from arena.schemas.analytics import Conversion, Sustainability
from arena.services.forecaster import aggregate_renewable_utilization
from arena.services.state import get_state

router = APIRouter()


@router.get("/sustainability", response_model=Sustainability)
async def sustainability(
    session: Annotated[AsyncSession, SessionDep],
    window: str = Query("24h", regex="^(1h|24h)$"),
) -> Sustainability:
    td = timedelta(hours=1) if window == "1h" else timedelta(hours=24)
    agg = await energy_repo.recent_aggregate(session, td)
    util_pct = aggregate_renewable_utilization(get_state())
    # Waste reduction ≈ renewable utilization vs. naïve baseline of 60%
    waste_reduction = max(0.0, util_pct - 60.0)
    grid_delta = round(waste_reduction * 0.15, 2)
    return Sustainability(
        window=window,
        renewable_utilization_pct=util_pct,
        energy_waste_reduction_pct=round(waste_reduction, 2),
        carbon_avoided_kg=round(agg["carbon_avoided_kg"], 2),
        grid_efficiency_delta_pct=grid_delta,
    )


@router.get("/conversion", response_model=Conversion)
async def conversion(window: str = Query("1h", regex="^(1h|24h)$")) -> Conversion:
    state = get_state()
    with state.lock():
        nodes = list(state.nodes.values())
    # kWh used per second across the fleet, plus useful work generated
    fleet_kw = sum(n.power_draw_kw * n.utilization for n in nodes if n.online) or 1.0
    fleet_tflops = sum(n.tflops * n.utilization for n in nodes if n.online)
    fleet_hashrate = sum(n.hashrate_ths * n.utilization for n in nodes if n.online)
    tflops_per_kwh = round(fleet_tflops / (fleet_kw / 1.0), 2) if fleet_kw else 0.0
    tokens_per_kwh = round(fleet_hashrate * 0.0008, 4)
    jobs_per_mwh = round(60.0 * (fleet_tflops + 1.0) / max(fleet_kw, 1.0), 2)
    return Conversion(
        window=window,
        tflops_per_kwh=tflops_per_kwh,
        tokens_per_kwh=tokens_per_kwh,
        jobs_per_mwh=jobs_per_mwh,
    )
