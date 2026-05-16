"""Renewable generation + demand model.

Diurnal solar curve, noise-driven wind, gentle hydro baseline, against a
demand profile that loosely tracks the work-hours/evening peak. Numbers
are dimensioned in MW at the region level. Capacity is dimensioned in kW
in the seed data and converted on the fly.
"""

from __future__ import annotations

import math
import random
from collections import deque
from datetime import datetime, timezone

from arena.services.state import RegionRuntime, SimState


# Region-local "solar hour" offsets (hours from UTC) — used to keep the
# diurnal curve appropriate per region.
REGION_LOCAL_OFFSET_H: dict[str, float] = {
    "CA-NORTH": -8.0,
    "TX-WEST": -6.0,
    "EU-NORDIC": 1.0,
    "AU-SE": 10.0,
}


def _solar_factor(local_hour: float) -> float:
    """A bell-curve-ish solar factor in [0, 1] peaking at 12:30 local."""
    if local_hour < 5 or local_hour > 20:
        return 0.0
    # Sin curve, then squared for a flatter midday plateau.
    s = math.sin(math.pi * (local_hour - 5) / 15.0)
    return max(0.0, s) ** 1.2


def _demand_factor(local_hour: float) -> float:
    """Typical grid demand: morning ramp, midday lull, evening peak."""
    base = 0.55
    morning = 0.20 * math.exp(-((local_hour - 8) ** 2) / 4.0)
    evening = 0.35 * math.exp(-((local_hour - 19) ** 2) / 6.0)
    return min(1.0, base + morning + evening)


def _wind_factor(seed: float, t: float) -> float:
    """Pseudo-stochastic wind, smooth on the second-scale."""
    # Two slow sinusoids + a slow random walk for variability.
    a = 0.45 + 0.25 * math.sin(seed + t / 600.0)
    b = 0.15 * math.sin(seed * 1.7 + t / 137.0)
    jitter = 0.05 * (random.random() - 0.5)
    return max(0.0, min(1.0, a + b + jitter))


def _hydro_factor() -> float:
    """Hydro is roughly steady, modulated by season — keep ~0.6–0.7."""
    return 0.60 + 0.05 * random.random()


def advance_region(region: RegionRuntime, now: datetime) -> None:
    """Mutate `region` in place with the next tick's generation/demand."""
    offset = REGION_LOCAL_OFFSET_H.get(region.id, 0.0)
    local_hour = (now.hour + now.minute / 60.0 + offset) % 24.0
    t_epoch = now.timestamp()

    # Convert installed capacities kW → MW
    cap_solar_mw = region.installed_solar_kw / 1000.0
    cap_wind_mw = region.installed_wind_kw / 1000.0
    cap_hydro_mw = region.installed_hydro_kw / 1000.0

    seed = hash(region.id) % 1000 / 100.0

    solar_mw = cap_solar_mw * _solar_factor(local_hour)
    wind_mw = cap_wind_mw * _wind_factor(seed, t_epoch)
    hydro_mw = cap_hydro_mw * _hydro_factor()

    total_gen_mw = solar_mw + wind_mw + hydro_mw

    # Demand is a fraction of nameplate capacity — keeps surplus realistic.
    nameplate = cap_solar_mw + cap_wind_mw + cap_hydro_mw
    demand_mw = nameplate * (0.55 + 0.30 * _demand_factor(local_hour))

    region.generation_mw = round(total_gen_mw, 2)
    region.demand_mw = round(demand_mw, 2)
    region.surplus_mw = round(total_gen_mw - demand_mw, 2)
    # Single-source mix here: all renewable. In a more complex sim we'd model
    # fossil fill-in for deficit hours; for now share is 1 when surplus>=0,
    # otherwise drops linearly with the deficit.
    if total_gen_mw <= 0:
        region.renewable_share = 0.0
    elif region.surplus_mw >= 0:
        region.renewable_share = 1.0
    else:
        deficit = -region.surplus_mw
        region.renewable_share = max(0.0, 1.0 - deficit / max(1.0, demand_mw))


def advance(state: SimState) -> None:
    now = datetime.now(timezone.utc)
    with state.lock():
        for region in state.regions.values():
            advance_region(region, now)
            # Append to rolling history (keep last hour @ 1Hz)
            buf = state.surplus_history.setdefault(region.id, deque(maxlen=3600))
            buf.append(region.surplus_mw)
        state.last_tick_at = now
        state.tick_count += 1
