"""Energy sim is deterministic-ish: same region, same wall time → same range."""

from __future__ import annotations

from datetime import datetime, timezone

from arena.services.energy_sim import _demand_factor, _solar_factor, advance_region
from arena.services.state import RegionRuntime


def test_solar_factor_is_zero_at_night():
    assert _solar_factor(2.0) == 0.0
    assert _solar_factor(22.0) == 0.0


def test_solar_factor_peaks_midday():
    noon = _solar_factor(12.5)
    morning = _solar_factor(8.0)
    evening = _solar_factor(17.0)
    assert noon > morning
    assert noon > evening
    assert 0.0 < noon <= 1.0


def test_demand_factor_in_range():
    for h in range(0, 24):
        f = _demand_factor(float(h))
        assert 0.0 <= f <= 1.0


def test_advance_region_writes_consistent_values():
    r = RegionRuntime(
        id="TEST", name="Test", lat=0.0, lng=0.0,
        installed_solar_kw=1_000_000.0,
        installed_wind_kw=1_000_000.0,
        installed_hydro_kw=500_000.0,
    )
    now = datetime(2026, 5, 16, 18, 0, 0, tzinfo=timezone.utc)  # evening UTC
    advance_region(r, now)
    assert r.generation_mw >= 0
    assert r.demand_mw > 0
    assert abs((r.generation_mw - r.demand_mw) - r.surplus_mw) < 0.05
    assert 0.0 <= r.renewable_share <= 1.0
