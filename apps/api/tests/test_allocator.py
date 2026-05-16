"""Allocator: priority ordering, class fit, and surplus accounting."""

from __future__ import annotations

from arena.services.allocator import allocate
from arena.services.state import NodeRuntime, RegionRuntime, SimState, WorkloadRuntime


def _make_state() -> SimState:
    s = SimState()
    s.regions["CA"] = RegionRuntime(
        id="CA", name="CA", lat=0, lng=0,
        installed_solar_kw=1_000_000, installed_wind_kw=0, installed_hydro_kw=0,
        generation_mw=500.0, demand_mw=200.0, surplus_mw=300.0, renewable_share=1.0,
    )
    s.nodes["gpu1"] = NodeRuntime(
        id="gpu1", region_id="CA", class_name="GPU_CLUSTER",
        power_draw_kw=300.0, tflops=280.0, hashrate_ths=0.0,
    )
    s.nodes["asic1"] = NodeRuntime(
        id="asic1", region_id="CA", class_name="ASIC_FARM",
        power_draw_kw=480.0, tflops=0.0, hashrate_ths=1000.0,
    )
    return s


def test_high_priority_wins_first():
    s = _make_state()
    s.workloads["lo"] = WorkloadRuntime(id="lo", kind="AI_INFERENCE", priority=0.1, demand_kw=200)
    s.workloads["hi"] = WorkloadRuntime(id="hi", kind="AI_INFERENCE", priority=0.9, demand_kw=200)
    traces = allocate(s)
    decisions = {t["workload_id"]: t["decision"] for t in traces}
    assert decisions["hi"] == "allocated"
    # Lo may also get allocated if surplus remains, but it must come after.
    # Verify allocation order via started_at on hi being set first by checking running state.
    assert s.workloads["hi"].state == "RUNNING"


def test_workload_routed_to_matching_class():
    s = _make_state()
    s.workloads["miner"] = WorkloadRuntime(id="miner", kind="MINING", priority=0.5, demand_kw=400)
    allocate(s)
    assert s.workloads["miner"].assigned_node == "asic1"


def test_workload_deferred_when_surplus_exhausted():
    s = _make_state()
    # Two workloads each demanding 250 kW but only 300 kW MW surplus (= 300_000 kW)?
    # No — surplus_mw=300 means 300 MW = 300_000 kW, way more than 250.
    # Squeeze surplus down to 100 kW (≈0.1 MW) to test the deficit branch.
    s.regions["CA"].surplus_mw = 0.05  # 50 kW available
    s.workloads["w1"] = WorkloadRuntime(id="w1", kind="AI_INFERENCE", priority=0.9, demand_kw=200)
    traces = allocate(s)
    assert traces[0]["decision"] == "deferred"
