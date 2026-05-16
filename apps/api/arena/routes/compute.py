from __future__ import annotations

import uuid

import orjson
from fastapi import APIRouter, HTTPException, Query, status

from arena.core.redis import Q_WORKLOAD_SUBMIT, get_redis
from arena.schemas.compute import (
    AllocatorExplain,
    CreatedWorkload,
    CreateWorkload,
    WorkloadDTO,
    WorkloadList,
)
from arena.services.state import get_state

router = APIRouter()


@router.get("/workloads", response_model=WorkloadList)
async def list_workloads(state_filter: str | None = Query(None, alias="state")) -> WorkloadList:
    state = get_state()
    with state.lock():
        wls = list(state.workloads.values())
    if state_filter:
        wls = [w for w in wls if w.state.upper() == state_filter.upper()]
    items = [
        WorkloadDTO(
            id=w.id,
            kind=w.kind,
            priority=w.priority,
            demand_kw=w.demand_kw,
            state=w.state,
            assigned_node=w.assigned_node,
            created_at=w.created_at,
            started_at=w.started_at,
            rationale=w.rationale,
        )
        for w in sorted(wls, key=lambda x: x.created_at, reverse=True)[:200]
    ]
    return WorkloadList(items=items, total=len(wls))


@router.post("/workloads", response_model=CreatedWorkload, status_code=status.HTTP_201_CREATED)
async def create_workload(req: CreateWorkload) -> CreatedWorkload:
    wid = "wl_" + uuid.uuid4().hex[:10]
    msg = {
        "id": wid,
        "kind": req.kind.value if hasattr(req.kind, "value") else str(req.kind),
        "priority": req.priority,
        "demand_kw": req.demand_kw,
    }
    await get_redis().lpush(Q_WORKLOAD_SUBMIT, orjson.dumps(msg).decode())
    return CreatedWorkload(id=wid, state="QUEUED")  # type: ignore[arg-type]


@router.get("/allocator/explain", response_model=AllocatorExplain)
async def explain(workload_id: str = Query(..., alias="workload_id")) -> AllocatorExplain:
    state = get_state()
    trace = state.allocator_traces.get(workload_id)
    if not trace:
        raise HTTPException(status_code=404, detail="no allocator trace for workload")
    return AllocatorExplain(
        workload_id=workload_id,
        decision=trace["decision"],
        chosen_node=trace.get("chosen_node"),
        score=float(trace.get("score", 0.0)),
        rationale=trace.get("rationale", ""),
        considered=trace.get("considered", []),
    )
