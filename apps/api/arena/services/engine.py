"""The simulation engine — owns the tick loop.

Each tick (~1 Hz):
  1. energy_sim.advance(state)       — update region generation & demand
  2. allocator.allocate(state)       — drain workload priority queue
  3. mining_sim.tick(state)          — maybe emit a block
  4. compute carbon + utilization    — scoring
  5. persist a row per region        — durable analytics
  6. broadcast a TickEvent over WS   — operator dashboard
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from arena.core.db import session_scope
from arena.core.redis import CH_TICK, RedisLike, publish_json
from arena.models import Block, EnergyTick
from arena.repositories import blocks as blocks_repo
from arena.repositories import energy as energy_repo
from arena.services import allocator, energy_sim, mining_sim
from arena.services.forecaster import aggregate_renewable_utilization
from arena.services.state import SimState, get_state
from arena.ws.hub import Hub

log = logging.getLogger("arena.engine")


# Carbon intensity displaced per kWh of renewable energy (US grid avg ≈ 0.4 kg CO₂/kWh).
CARBON_KG_PER_KWH = 0.40


class SimulationEngine:
    def __init__(self, *, hub: Hub, redis: RedisLike, tick_s: float = 1.0) -> None:
        self.hub = hub
        self.redis = redis
        self.tick_s = tick_s
        self.state: SimState = get_state()

    async def run(self) -> None:
        # Hydrate cache from DB on startup
        await self._hydrate()

        log.info("engine entering tick loop")
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("tick failed; continuing")
            await asyncio.sleep(self.tick_s)

    async def tick(self) -> None:
        # Drain pending workload submissions from Redis queue
        await self._drain_submissions()

        # 1. Energy
        energy_sim.advance(self.state)

        # 2. Allocator
        traces = allocator.allocate(self.state)

        # 3. Mining
        block_payload = mining_sim.tick(self.state)

        # 4. Carbon: tick increment = workloads consuming surplus * kg/kWh
        carbon_inc = 0.0
        with self.state.lock():
            for n in self.state.nodes.values():
                if n.online and n.utilization > 0:
                    # kWh consumed this tick = kW * (tick_s / 3600)
                    kwh = n.power_draw_kw * n.utilization * (self.tick_s / 3600.0)
                    carbon_inc += kwh * CARBON_KG_PER_KWH
            self.state.carbon_avoided_kg_total += carbon_inc

        renewable_util_pct = aggregate_renewable_utilization(self.state)

        # 5. Persist (best-effort: don't fail the tick if DB is sad)
        await self._persist(block_payload, carbon_inc)

        # 6. Broadcast
        event = self._build_event(traces, block_payload, renewable_util_pct, carbon_inc)
        await self.hub.broadcast(event)
        await publish_json(CH_TICK, event)

    # ─── helpers ─────────────────────────────────────────────────────

    async def _hydrate(self) -> None:
        """Load regions, nodes, and active workloads from DB into the state cache."""
        from arena.repositories import nodes as nodes_repo
        from arena.repositories import regions as regions_repo
        from arena.repositories import workloads as workloads_repo
        from arena.services.state import NodeRuntime, RegionRuntime, WorkloadRuntime

        async with session_scope() as s:
            regions = await regions_repo.list_regions(s)
            nodes = await nodes_repo.list_compute_nodes(s)
            wls = await workloads_repo.list_workloads(s)

        with self.state.lock():
            for r in regions:
                self.state.regions[r.id] = RegionRuntime(
                    id=r.id,
                    name=r.name,
                    lat=r.lat,
                    lng=r.lng,
                    installed_solar_kw=r.installed_solar,
                    installed_wind_kw=r.installed_wind,
                    installed_hydro_kw=r.installed_hydro,
                )
            for n in nodes:
                self.state.nodes[n.id] = NodeRuntime(
                    id=n.id,
                    region_id=n.region_id,
                    class_name=n.class_name.value if hasattr(n.class_name, "value") else str(n.class_name),
                    power_draw_kw=n.power_draw_kw,
                    tflops=n.tflops,
                    hashrate_ths=n.hashrate_ths,
                    online=n.online,
                )
            for w in wls:
                self.state.workloads[w.id] = WorkloadRuntime(
                    id=w.id,
                    kind=w.kind.value if hasattr(w.kind, "value") else str(w.kind),
                    priority=w.priority,
                    demand_kw=w.demand_kw,
                    state=w.state.value if hasattr(w.state, "value") else str(w.state),
                    assigned_node=w.assigned_node_id,
                    created_at=w.created_at or datetime.now(timezone.utc),
                    started_at=w.started_at,
                    rationale=w.rationale,
                )

        log.info(
            "hydrated cache",
            extra={
                "ctx_regions": len(self.state.regions),
                "ctx_nodes": len(self.state.nodes),
                "ctx_workloads": len(self.state.workloads),
            },
        )

    async def _drain_submissions(self) -> None:
        """Pull newly-submitted workloads off the Redis queue into state."""
        from arena.core.redis import Q_WORKLOAD_SUBMIT
        from arena.services.state import WorkloadRuntime
        import orjson

        for _ in range(50):  # bounded drain per tick
            raw = await self.redis.rpop(Q_WORKLOAD_SUBMIT)
            if raw is None:
                break
            try:
                msg = orjson.loads(raw)
            except Exception:
                log.warning("invalid workload submission: %r", raw[:80])
                continue
            with self.state.lock():
                self.state.workloads[msg["id"]] = WorkloadRuntime(
                    id=msg["id"],
                    kind=msg["kind"],
                    priority=float(msg["priority"]),
                    demand_kw=float(msg["demand_kw"]),
                )

    async def _persist(self, block_payload: dict | None, carbon_inc: float) -> None:
        try:
            async with session_scope() as s:
                # Per-region tick row
                with self.state.lock():
                    rows = [
                        EnergyTick(
                            region_id=r.id,
                            generation_mw=r.generation_mw,
                            demand_mw=r.demand_mw,
                            surplus_mw=r.surplus_mw,
                            renewable_share=r.renewable_share,
                            carbon_avoided_kg=carbon_inc / max(1, len(self.state.regions)),
                        )
                        for r in self.state.regions.values()
                    ]
                for row in rows:
                    await energy_repo.insert_tick(s, row)

                if block_payload is not None:
                    height = await blocks_repo.max_height(s) + 1
                    await blocks_repo.add_block(
                        s,
                        Block(
                            height=height,
                            hash=block_payload["hash"],
                            miner=block_payload["miner"],
                            reward_tokens=block_payload["reward_tokens"],
                            energy_kwh=block_payload["energy_kwh"],
                        ),
                    )
        except Exception:
            log.exception("persist failed; tick still broadcast")

    def _build_event(
        self,
        traces: list[dict],
        block_payload: dict | None,
        renewable_util_pct: float,
        carbon_inc: float,
    ) -> dict:
        snap = self.state.snapshot()
        # Normalize region dicts: rename `id` → `region` so REST and WS share a shape.
        regions = []
        for r in snap["regions"]:
            rr = dict(r)
            rr["region"] = rr.pop("id")
            regions.append(rr)
        # Normalize node dicts similarly.
        nodes = []
        for n in snap["nodes"]:
            nn = dict(n)
            nn["region"] = nn.pop("region_id", "")
            nodes.append(nn)
        workloads = snap["workloads"][:50]

        agg_gen = sum(r["generation_mw"] for r in regions)
        agg_dem = sum(r["demand_mw"] for r in regions)
        agg_sur = sum(r["surplus_mw"] for r in regions)
        # Renewable share = weighted by generation
        if agg_gen > 0:
            agg_share = sum(r["renewable_share"] * r["generation_mw"] for r in regions) / agg_gen
        else:
            agg_share = 0.0
        return {
            "type": "tick",
            "payload": {
                "timestamp": snap["ts"],
                "tick": snap["tick"],
                "generation_mw": round(agg_gen, 2),
                "demand_mw": round(agg_dem, 2),
                "surplus_mw": round(agg_sur, 2),
                "renewable_share": round(agg_share, 3),
                "renewable_utilization_pct": renewable_util_pct,
                "carbon_inc_kg": round(carbon_inc, 4),
                "carbon_total_kg": round(snap["carbon_avoided_kg_total"], 2),
                "hashrate_ths": snap["hashrate_ths"],
                "difficulty": round(snap["difficulty"], 2),
                "by_region": regions,
                "nodes": nodes,
                "workloads": workloads,
                "block": block_payload and {
                    "hash": block_payload["hash"],
                    "miner": block_payload["miner"],
                    "reward_tokens": block_payload["reward_tokens"],
                    "energy_kwh": block_payload["energy_kwh"],
                    "ts": block_payload["ts"].isoformat(),
                },
                "decisions": [t for t in traces if t["decision"] == "allocated"][:10],
            },
        }
