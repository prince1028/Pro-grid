from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegionSnapshot(BaseModel):
    region: str
    name: str
    lat: float
    lng: float
    generation_mw: float
    demand_mw: float
    surplus_mw: float
    renewable_share: float


class EnergySnapshot(BaseModel):
    timestamp: datetime
    generation_mw: float
    demand_mw: float
    surplus_mw: float
    renewable_share: float
    carbon_avoided_kg: float = 0.0
    by_region: list[RegionSnapshot] = Field(default_factory=list)


class SeriesPoint(BaseModel):
    t: datetime
    gen: float
    dem: float
    sur: float


class SeriesResponse(BaseModel):
    bucket_s: int
    points: list[SeriesPoint]


class RegionMeta(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    installed_solar_kw: float
    installed_wind_kw: float
    installed_hydro_kw: float
