"""In-memory state cache for the simulation engine.

The simulation engine is the single writer for this cache. REST endpoints
read it freely. Mutation outside the engine is forbidden.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any


@dataclass(slots=True)
class RegionRuntime:
    id: str
    name: str
    lat: float
    lng: float
    installed_solar_kw: float
    installed_wind_kw: float
    installed_hydro_kw: float
    generation_mw: float = 0.0
    demand_mw: float = 0.0
    surplus_mw: float = 0.0
    renewable_share: float = 1.0


@dataclass(slots=True)
class NodeRuntime:
    id: str
    region_id: str
    class_name: str
    power_draw_kw: float
    tflops: float
    hashrate_ths: float
    online: bool = True
    utilization: float = 0.0


@dataclass(slots=True)
class WorkloadRuntime:
    id: str
    kind: str
    priority: float
    demand_kw: float
    state: str = "QUEUED"
    assigned_node: str | None = None
    rationale: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None


class SimState:
    """Mutable, in-process source of truth between ticks."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.regions: dict[str, RegionRuntime] = {}
        self.nodes: dict[str, NodeRuntime] = {}
        self.workloads: dict[str, WorkloadRuntime] = {}
        self.last_tick_at: datetime | None = None
        self.tick_count: int = 0
        # Rolling history of region-level surplus, used by forecaster.
        # 1 sample per second, capped.
        self.surplus_history: dict[str, deque[float]] = {}
        self.carbon_avoided_kg_total: float = 0.0
        # Per-tick blockchain stats (computed by mining_sim)
        self.hashrate_ths: float = 0.0
        self.difficulty: float = 1_000_000.0
        # Allocator decision trace for the most recent allocation per workload
        self.allocator_traces: dict[str, dict[str, Any]] = {}

    def lock(self) -> RLock:
        return self._lock

    def snapshot(self) -> dict:
        """Cheap, immutable view of current world state."""
        with self._lock:
            return {
                "ts": self.last_tick_at.isoformat() if self.last_tick_at else None,
                "tick": self.tick_count,
                "regions": [r.__dict__.copy() for r in self.regions.values()],
                "nodes": [n.__dict__.copy() for n in self.nodes.values()],
                "workloads": [w.__dict__.copy() for w in self.workloads.values()],
                "hashrate_ths": self.hashrate_ths,
                "difficulty": self.difficulty,
                "carbon_avoided_kg_total": self.carbon_avoided_kg_total,
            }


_state = SimState()


def get_state() -> SimState:
    return _state
