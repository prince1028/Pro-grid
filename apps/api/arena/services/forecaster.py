"""Rolling-EWMA surplus forecaster.

A real model would use a small SARIMA / Prophet. For the MVP we project
forward using:
  • the diurnal solar/wind shape baked into energy_sim
  • an EWMA of recent surplus to correct against current conditions
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean

from arena.services.energy_sim import advance_region
from arena.services.state import RegionRuntime, SimState


def _ewma(values: list[float], alpha: float = 0.2) -> float:
    if not values:
        return 0.0
    s = values[0]
    for v in values[1:]:
        s = alpha * v + (1 - alpha) * s
    return s


def forecast(state: SimState, *, horizon_min: int = 60) -> list[dict]:
    """Return projected surplus per region for the next horizon_min minutes.

    The horizon is sampled at 5-minute intervals.
    """
    with state.lock():
        regions_copy = [RegionRuntime(**r.__dict__) for r in state.regions.values()]
        history = {rid: list(buf) for rid, buf in state.surplus_history.items()}

    points: list[dict] = []
    now = datetime.now(timezone.utc)

    for region in regions_copy:
        recent = history.get(region.id, [])[-300:]  # last 5 minutes @ 1Hz
        baseline_correction = _ewma(recent) - region.surplus_mw if recent else 0.0

        for offset_min in range(5, horizon_min + 1, 5):
            future = now + timedelta(minutes=offset_min)
            # Roll the deterministic part of the energy model forward
            r_copy = RegionRuntime(**region.__dict__)
            advance_region(r_copy, future)
            expected = r_copy.surplus_mw + baseline_correction
            # Confidence decays with horizon
            conf = max(0.3, 1.0 - offset_min / (horizon_min * 2.0))
            points.append(
                {
                    "region": region.id,
                    "t_offset_min": offset_min,
                    "expected_surplus_mw": round(expected, 2),
                    "confidence": round(conf, 3),
                }
            )

    return points


def aggregate_renewable_utilization(state: SimState) -> float:
    """Fleet renewable-utilization %: served demand / total generation."""
    with state.lock():
        gen = sum(r.generation_mw for r in state.regions.values())
        served = sum(min(r.generation_mw, r.demand_mw) for r in state.regions.values())
        # Add load served by allocated workloads against surplus
        node_demand_mw = sum(
            n.power_draw_kw * n.utilization for n in state.nodes.values() if n.online
        ) / 1000.0
        served += node_demand_mw
        if gen <= 0:
            return 0.0
        return round(100.0 * min(1.0, served / gen), 2)
