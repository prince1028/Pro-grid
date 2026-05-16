from __future__ import annotations

from fastapi import APIRouter, Query

from arena.schemas.analytics import (
    ExplainReq,
    ExplainResp,
    Forecast,
    ForecastPoint,
    Recommendation,
)
from arena.services.forecaster import forecast as run_forecast
from arena.services.recommender import explain, recommendations
from arena.services.state import get_state

router = APIRouter()


@router.get("/recommendations", response_model=list[Recommendation])
async def list_recommendations() -> list[Recommendation]:
    return [Recommendation(**r) for r in recommendations(get_state())]


@router.get("/forecast", response_model=Forecast)
async def forecast(horizon: str = Query("60m", regex="^(15m|30m|60m|2h)$")) -> Forecast:
    horizon_min = {"15m": 15, "30m": 30, "60m": 60, "2h": 120}[horizon]
    pts = run_forecast(get_state(), horizon_min=horizon_min)
    return Forecast(
        horizon_min=horizon_min,
        points=[ForecastPoint(**p) for p in pts],
    )


@router.post("/explain", response_model=ExplainResp)
async def explain_route(req: ExplainReq) -> ExplainResp:
    text = explain(get_state(), subject=req.subject, target_id=req.id)
    return ExplainResp(subject=req.subject, id=req.id, explanation=text)
