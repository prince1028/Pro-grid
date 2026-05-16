"""Priority-aware workload allocator.

Each tick: drain queued workloads against the available regional surplus.
A workload is allocated to a node iff
  • the node is online, idle (utilization < 0.95), and class-compatible
  • the node's region has enough surplus to cover the workload's demand_kw
Workloads are dispatched in descending priority * urgency_age order.

Allocator emits a structured "trace" per workload so the UI can explain
the decision.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from arena.services.state import NodeRuntime, SimState, WorkloadRuntime


# Workload-kind → preferred node classes (highest preference first)
PREFERRED_NODE_CLASS: dict[str, tuple[str, ...]] = {
    "AI_INFERENCE": ("GPU_CLUSTER", "EDGE_INFERENCE", "CPU_GRID"),
    "MINING": ("ASIC_FARM", "GPU_CLUSTER"),
    "DISTRIBUTED_COMPUTE": ("CPU_GRID", "GPU_CLUSTER", "EDGE_INFERENCE"),
}


def _class_score(workload_kind: str, node_class: str) -> float:
    pref = PREFERRED_NODE_CLASS.get(workload_kind, ())
    if node_class in pref:
        # rank within preference list → higher = better
        idx = pref.index(node_class)
        return 1.0 - idx * 0.25
    return 0.0


def _node_idle(node: NodeRuntime) -> bool:
    return node.online and node.utilization < 0.95


def _region_surplus_kw(state: SimState) -> dict[str, float]:
    return {r.id: max(0.0, r.surplus_mw) * 1000.0 for r in state.regions.values()}


def allocate(state: SimState) -> list[dict[str, Any]]:
    """Run one allocation pass. Returns the per-workload decision traces."""
    now = datetime.now(timezone.utc)
    traces: list[dict[str, Any]] = []

    with state.lock():
        surplus_by_region = _region_surplus_kw(state)
        # Index nodes by region for fast lookup
        nodes_by_region: dict[str, list[NodeRuntime]] = defaultdict(list)
        for n in state.nodes.values():
            nodes_by_region[n.region_id].append(n)

        # Order queued workloads: higher priority first; ties broken by age.
        queued: list[WorkloadRuntime] = [w for w in state.workloads.values() if w.state == "QUEUED"]
        queued.sort(key=lambda w: (-w.priority, w.created_at))

        for w in queued:
            trace = _try_allocate(w, nodes_by_region, surplus_by_region, now)
            traces.append(trace)
            state.allocator_traces[w.id] = trace

        # Mark long-running workloads complete based on simulated effort.
        _advance_running(state, now)

    return traces


def _try_allocate(
    w: WorkloadRuntime,
    nodes_by_region: dict[str, list[NodeRuntime]],
    surplus_by_region: dict[str, float],
    now: datetime,
) -> dict[str, Any]:
    considered: list[dict[str, Any]] = []
    best: tuple[float, NodeRuntime] | None = None

    for region, nodes in nodes_by_region.items():
        avail_kw = surplus_by_region.get(region, 0.0)
        if avail_kw < w.demand_kw:
            considered.append({"region": region, "skipped": "insufficient_surplus", "avail_kw": avail_kw})
            continue
        for node in nodes:
            if not _node_idle(node):
                continue
            cls = _class_score(w.kind, node.class_name)
            if cls <= 0:
                continue
            # Score: class fit weighted by surplus headroom and node power-fit.
            headroom = avail_kw / max(1.0, w.demand_kw)
            power_fit = 1.0 - abs(node.power_draw_kw - w.demand_kw) / max(node.power_draw_kw, w.demand_kw)
            score = cls * (0.6 + 0.2 * min(2.0, headroom)) * (0.5 + 0.5 * max(0.0, power_fit))
            considered.append(
                {
                    "node": node.id,
                    "region": region,
                    "class_score": round(cls, 3),
                    "power_fit": round(power_fit, 3),
                    "score": round(score, 3),
                }
            )
            if best is None or score > best[0]:
                best = (score, node)

    if best is None:
        # Defer if no fit; rejected only if structurally impossible.
        rationale = "No node matched class/surplus constraints this tick. Re-queued."
        w.state = "DEFERRED"
        w.rationale = rationale
        return {
            "workload_id": w.id,
            "decision": "deferred",
            "score": 0.0,
            "rationale": rationale,
            "considered": considered[:6],
        }

    score, node = best
    # Commit assignment
    surplus_by_region[node.region_id] -= w.demand_kw
    node.utilization = min(1.0, node.utilization + w.demand_kw / max(1.0, node.power_draw_kw))
    w.state = "RUNNING"
    w.assigned_node = node.id
    w.started_at = now
    w.rationale = (
        f"Allocated to {node.id} in {node.region_id}: class_score={_class_score(w.kind, node.class_name):.2f}, "
        f"score={score:.2f}. Surplus before={surplus_by_region[node.region_id]+w.demand_kw:.0f}kW."
    )

    return {
        "workload_id": w.id,
        "decision": "allocated",
        "chosen_node": node.id,
        "region": node.region_id,
        "score": round(score, 3),
        "rationale": w.rationale,
        "considered": considered[:6],
    }


# Coarse model: workloads run for a duration proportional to demand & inverse priority.
def _advance_running(state: SimState, now: datetime) -> None:
    completed_ids: list[str] = []
    for w in state.workloads.values():
        if w.state != "RUNNING" or w.started_at is None:
            continue
        # AI inference completes fast (~30s); mining loops indefinitely; dist-compute medium (~120s).
        budget_s = {"AI_INFERENCE": 30.0, "MINING": 9999.0, "DISTRIBUTED_COMPUTE": 120.0}[w.kind]
        # Faster nodes finish quicker — scale by class
        cls_speed = {"GPU_CLUSTER": 1.5, "ASIC_FARM": 1.2, "CPU_GRID": 0.8, "EDGE_INFERENCE": 1.0}
        if w.assigned_node and w.assigned_node in state.nodes:
            node = state.nodes[w.assigned_node]
            budget_s /= cls_speed.get(node.class_name, 1.0)
        elapsed = (now - w.started_at).total_seconds()
        if elapsed >= budget_s:
            w.state = "COMPLETED"
            completed_ids.append(w.id)
            if w.assigned_node and w.assigned_node in state.nodes:
                node = state.nodes[w.assigned_node]
                node.utilization = max(0.0, node.utilization - w.demand_kw / max(1.0, node.power_draw_kw))
            w.assigned_node = None

    # Reset deferred → queued each tick so they retry next allocation pass.
    for w in state.workloads.values():
        if w.state == "DEFERRED":
            w.state = "QUEUED"
