from __future__ import annotations

from pydantic import BaseModel


class Sustainability(BaseModel):
    window: str
    renewable_utilization_pct: float
    energy_waste_reduction_pct: float
    carbon_avoided_kg: float
    grid_efficiency_delta_pct: float


class Conversion(BaseModel):
    window: str
    tflops_per_kwh: float
    tokens_per_kwh: float
    jobs_per_mwh: float


class BlockDTO(BaseModel):
    height: int
    hash: str
    miner: str
    reward_tokens: float
    energy_kwh: float
    ts: str


class BlockchainStats(BaseModel):
    hashrate_ths: float
    difficulty: float
    blocks_24h: int
    tokens_24h: float
    energy_kwh_24h: float


class Recommendation(BaseModel):
    id: str
    title: str
    rationale: str
    projected_impact_kg: float
    confidence: float


class ForecastPoint(BaseModel):
    region: str
    t_offset_min: int
    expected_surplus_mw: float
    confidence: float


class Forecast(BaseModel):
    horizon_min: int
    points: list[ForecastPoint]


class ExplainReq(BaseModel):
    subject: str
    id: str


class ExplainResp(BaseModel):
    subject: str
    id: str
    explanation: str
