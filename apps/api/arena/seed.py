"""Demo seed.

Idempotent: only seeds if the regions table is empty. The set is chosen to
produce visible behavior: large solar farms in CA/TX, a wind-heavy nordic
region, a mid-sized hybrid AU region.
"""

from __future__ import annotations

import logging
import random
import uuid

from sqlalchemy import select

from arena.core.db import session_scope
from arena.models import (
    ComputeNode,
    NodeClass,
    Region,
    RenewableNode,
    Source,
    Workload,
    WorkloadKind,
)

log = logging.getLogger("arena.seed")


REGIONS: list[dict] = [
    {
        "id": "CA-NORTH",
        "name": "California North",
        "lat": 38.5,
        "lng": -121.5,
        "installed_solar": 1_800_000.0,  # kW
        "installed_wind": 600_000.0,
        "installed_hydro": 400_000.0,
    },
    {
        "id": "TX-WEST",
        "name": "Texas West",
        "lat": 31.9,
        "lng": -102.3,
        "installed_solar": 1_200_000.0,
        "installed_wind": 2_400_000.0,
        "installed_hydro": 100_000.0,
    },
    {
        "id": "EU-NORDIC",
        "name": "Nordic Grid",
        "lat": 60.1,
        "lng": 18.6,
        "installed_solar": 200_000.0,
        "installed_wind": 1_400_000.0,
        "installed_hydro": 800_000.0,
    },
    {
        "id": "AU-SE",
        "name": "Australia SE",
        "lat": -37.8,
        "lng": 144.9,
        "installed_solar": 700_000.0,
        "installed_wind": 500_000.0,
        "installed_hydro": 150_000.0,
    },
]


def _make_compute_nodes() -> list[ComputeNode]:
    nodes: list[ComputeNode] = []
    plan: list[tuple[str, NodeClass, int, float, float, float]] = [
        # region, class, count, power_draw_kw, tflops, hashrate_ths
        ("CA-NORTH", NodeClass.GPU_CLUSTER, 4, 320.0, 280.0, 0.0),
        ("CA-NORTH", NodeClass.EDGE_INFERENCE, 3, 80.0, 60.0, 0.0),
        ("TX-WEST", NodeClass.ASIC_FARM, 3, 480.0, 0.0, 1100.0),
        ("TX-WEST", NodeClass.GPU_CLUSTER, 2, 320.0, 280.0, 90.0),
        ("EU-NORDIC", NodeClass.CPU_GRID, 4, 140.0, 30.0, 0.0),
        ("EU-NORDIC", NodeClass.GPU_CLUSTER, 1, 320.0, 280.0, 0.0),
        ("AU-SE", NodeClass.GPU_CLUSTER, 1, 320.0, 280.0, 90.0),
        ("AU-SE", NodeClass.EDGE_INFERENCE, 2, 80.0, 60.0, 0.0),
    ]
    for region, cls, count, kw, tf, hs in plan:
        for i in range(count):
            suffix = f"{cls.value.lower().split('_')[0]}_{i+1:02d}"
            nodes.append(
                ComputeNode(
                    id=f"node_{region.lower()}_{suffix}",
                    region_id=region,
                    class_name=cls,
                    power_draw_kw=kw + random.uniform(-20, 20),
                    tflops=tf + random.uniform(-15, 15) if tf else 0.0,
                    hashrate_ths=hs + random.uniform(-50, 50) if hs else 0.0,
                    online=True,
                )
            )
    return nodes


def _make_renewable_nodes() -> list[RenewableNode]:
    out: list[RenewableNode] = []
    for r in REGIONS:
        # 3 farms per region, sized as fractions of installed capacity
        for src, total_kw in (
            (Source.SOLAR, r["installed_solar"]),
            (Source.WIND, r["installed_wind"]),
            (Source.HYDRO, r["installed_hydro"]),
        ):
            if total_kw <= 0:
                continue
            out.append(
                RenewableNode(
                    id=f"ren_{r['id'].lower()}_{src.value.lower()}",
                    region_id=r["id"],
                    source=src,
                    capacity_kw=total_kw,
                    online=True,
                )
            )
    return out


def _make_workloads() -> list[Workload]:
    seeds = [
        (WorkloadKind.AI_INFERENCE, 0.85, 220.0),
        (WorkloadKind.AI_INFERENCE, 0.65, 160.0),
        (WorkloadKind.AI_INFERENCE, 0.45, 90.0),
        (WorkloadKind.MINING, 0.30, 480.0),
        (WorkloadKind.MINING, 0.30, 480.0),
        (WorkloadKind.MINING, 0.20, 320.0),
        (WorkloadKind.DISTRIBUTED_COMPUTE, 0.75, 140.0),
        (WorkloadKind.DISTRIBUTED_COMPUTE, 0.55, 140.0),
        (WorkloadKind.DISTRIBUTED_COMPUTE, 0.40, 80.0),
    ]
    return [
        Workload(
            id="wl_" + uuid.uuid4().hex[:10],
            kind=kind,
            priority=pri,
            demand_kw=kw,
        )
        for kind, pri, kw in seeds
    ]


async def maybe_seed() -> None:
    """Seed if no regions exist. Idempotent."""
    async with session_scope() as s:
        existing = (await s.execute(select(Region.id))).scalars().first()
        if existing:
            return
        for r in REGIONS:
            s.add(Region(**r))
        for n in _make_renewable_nodes():
            s.add(n)
        for c in _make_compute_nodes():
            s.add(c)
        for w in _make_workloads():
            s.add(w)
        log.info("seeded demo data", extra={"ctx_regions": len(REGIONS)})
