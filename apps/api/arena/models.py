"""SQLAlchemy ORM mirror of prisma/schema.prisma.

Keep this in sync with the Prisma schema by hand. Field names use snake_case
in Python; Prisma camelCase fields are mapped explicitly.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arena.core.db import Base


# ─── Enums ────────────────────────────────────────────────────────────


class Source(str, enum.Enum):
    SOLAR = "SOLAR"
    WIND = "WIND"
    HYDRO = "HYDRO"


class NodeClass(str, enum.Enum):
    GPU_CLUSTER = "GPU_CLUSTER"
    ASIC_FARM = "ASIC_FARM"
    EDGE_INFERENCE = "EDGE_INFERENCE"
    CPU_GRID = "CPU_GRID"


class WorkloadKind(str, enum.Enum):
    AI_INFERENCE = "AI_INFERENCE"
    MINING = "MINING"
    DISTRIBUTED_COMPUTE = "DISTRIBUTED_COMPUTE"


class WorkloadState(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DEFERRED = "DEFERRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── Tables ───────────────────────────────────────────────────────────


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    installed_solar: Mapped[float] = mapped_column(Float, default=0)
    installed_wind: Mapped[float] = mapped_column(Float, default=0)
    installed_hydro: Mapped[float] = mapped_column(Float, default=0)


class RenewableNode(Base):
    __tablename__ = "renewable_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), index=True)
    source: Mapped[Source] = mapped_column(SAEnum(Source), nullable=False)
    capacity_kw: Mapped[float] = mapped_column(Float, nullable=False)
    online: Mapped[bool] = mapped_column(Boolean, default=True)


class ComputeNode(Base):
    __tablename__ = "compute_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), index=True)
    class_name: Mapped[NodeClass] = mapped_column(SAEnum(NodeClass), nullable=False)
    power_draw_kw: Mapped[float] = mapped_column(Float, nullable=False)
    tflops: Mapped[float] = mapped_column(Float, default=0)
    hashrate_ths: Mapped[float] = mapped_column(Float, default=0)
    online: Mapped[bool] = mapped_column(Boolean, default=True)


class Workload(Base):
    __tablename__ = "workloads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[WorkloadKind] = mapped_column(SAEnum(WorkloadKind), nullable=False)
    priority: Mapped[float] = mapped_column(Float, nullable=False)
    demand_kw: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[WorkloadState] = mapped_column(
        SAEnum(WorkloadState), default=WorkloadState.QUEUED
    )
    assigned_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("compute_nodes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)


class EnergyTick(Base):
    __tablename__ = "energy_ticks"
    __table_args__ = (
        Index("ix_energy_ticks_ts", "ts"),
        Index("ix_energy_ticks_region_ts", "region_id", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"))
    generation_mw: Mapped[float] = mapped_column(Float, nullable=False)
    demand_mw: Mapped[float] = mapped_column(Float, nullable=False)
    surplus_mw: Mapped[float] = mapped_column(Float, nullable=False)
    renewable_share: Mapped[float] = mapped_column(Float, nullable=False)
    carbon_avoided_kg: Mapped[float] = mapped_column(Float, default=0)


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    height: Mapped[int] = mapped_column(unique=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hash: Mapped[str] = mapped_column(String, nullable=False)
    miner: Mapped[str] = mapped_column(String, nullable=False)
    reward_tokens: Mapped[float] = mapped_column(Float, nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)
