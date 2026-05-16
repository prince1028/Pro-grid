"""Optimization recommendations + plain-English explanations.

This is intentionally rule-based, not an LLM call — the recommendations
read off live sim state via small, transparent heuristics. The 'AI'
framing is honest: these are exactly the suggestions a forecaster +
allocator would surface, formatted for the operator.
"""

from __future__ import annotations

import uuid

from arena.services.state import SimState


def recommendations(state: SimState) -> list[dict]:
    with state.lock():
        regions = list(state.regions.values())
        nodes = list(state.nodes.values())
        workloads = list(state.workloads.values())

    recs: list[dict] = []

    # 1. Find regions with high surplus but low local utilization
    for r in regions:
        if r.surplus_mw <= 0:
            continue
        region_nodes = [n for n in nodes if n.region_id == r.id]
        avg_util = (
            sum(n.utilization for n in region_nodes) / len(region_nodes) if region_nodes else 0.0
        )
        if avg_util < 0.4 and r.surplus_mw > 100:
            recs.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "title": f"Redirect mining workloads to {r.id}",
                    "rationale": (
                        f"{r.name} has {r.surplus_mw:.0f} MW of surplus and only "
                        f"{avg_util*100:.0f}% fleet utilization — net curtailment risk."
                    ),
                    "projected_impact_kg": round(r.surplus_mw * 1000 * 0.45, 1),
                    "confidence": 0.78,
                }
            )

    # 2. Workloads queued > 5 — recommend priority boost or scale-up
    queued = [w for w in workloads if w.state == "QUEUED"]
    if len(queued) > 5:
        recs.append(
            {
                "id": uuid.uuid4().hex[:8],
                "title": f"Backlog growing: {len(queued)} workloads queued",
                "rationale": (
                    "Allocator is supply-bound. Either raise priority on time-critical jobs "
                    "or admit more compute nodes in the surplus regions."
                ),
                "projected_impact_kg": round(len(queued) * 12.0, 1),
                "confidence": 0.65,
            }
        )

    # 3. Any region in deficit
    for r in regions:
        if r.surplus_mw < -50:
            recs.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "title": f"Defer non-critical compute in {r.id}",
                    "rationale": (
                        f"{r.name} is in deficit ({r.surplus_mw:.0f} MW). Defer mining and "
                        "low-priority distributed-compute until surplus returns."
                    ),
                    "projected_impact_kg": round(abs(r.surplus_mw) * 800.0, 1),
                    "confidence": 0.82,
                }
            )

    # Fallback so the UI always has something useful to show
    if not recs:
        recs.append(
            {
                "id": uuid.uuid4().hex[:8],
                "title": "Grid is well-balanced",
                "rationale": (
                    "No region is in deficit and no workloads are queued > priority threshold. "
                    "Continue current allocation policy."
                ),
                "projected_impact_kg": 0.0,
                "confidence": 0.9,
            }
        )

    return recs


def explain(state: SimState, *, subject: str, target_id: str) -> str:
    """Plain-English rationale for an allocation, a workload, or a recommendation."""
    if subject == "allocation":
        trace = state.allocator_traces.get(target_id)
        if not trace:
            return "No allocation trace exists for this workload yet."
        if trace["decision"] == "allocated":
            return (
                f"Workload {target_id} was allocated to node {trace['chosen_node']} in "
                f"{trace.get('region', 'unknown')} with a fitness score of {trace['score']:.2f}. "
                f"{trace['rationale']}"
            )
        if trace["decision"] == "deferred":
            return (
                f"Workload {target_id} was deferred this tick: {trace['rationale']} "
                "It will be retried automatically on the next tick once surplus or capacity opens up."
            )
        return f"Workload {target_id}: {trace.get('rationale', 'no rationale')}"

    if subject == "workload":
        with state.lock():
            w = state.workloads.get(target_id)
        if not w:
            return f"Workload {target_id} not found."
        return (
            f"Workload {target_id} is a {w.kind.lower()} job at priority {w.priority:.2f} drawing "
            f"{w.demand_kw:.0f} kW. Current state: {w.state}."
            + (f" Assigned to {w.assigned_node}." if w.assigned_node else "")
        )

    return f"No explanation available for subject={subject}, id={target_id}."
