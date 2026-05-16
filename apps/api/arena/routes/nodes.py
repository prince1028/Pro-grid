from __future__ import annotations

from fastapi import APIRouter, HTTPException

from arena.schemas.compute import ComputeNodeDTO
from arena.services.state import get_state

router = APIRouter()


@router.get("", response_model=list[ComputeNodeDTO])
async def list_nodes() -> list[ComputeNodeDTO]:
    state = get_state()
    with state.lock():
        return [
            ComputeNodeDTO(
                id=n.id,
                region=n.region_id,
                class_name=n.class_name,  # type: ignore[arg-type]
                power_draw_kw=n.power_draw_kw,
                tflops=n.tflops,
                hashrate_ths=n.hashrate_ths,
                online=n.online,
                utilization=round(n.utilization, 3),
            )
            for n in state.nodes.values()
        ]


@router.get("/{node_id}", response_model=ComputeNodeDTO)
async def get_node(node_id: str) -> ComputeNodeDTO:
    state = get_state()
    with state.lock():
        n = state.nodes.get(node_id)
    if n is None:
        raise HTTPException(status_code=404, detail="node not found")
    return ComputeNodeDTO(
        id=n.id,
        region=n.region_id,
        class_name=n.class_name,  # type: ignore[arg-type]
        power_draw_kw=n.power_draw_kw,
        tflops=n.tflops,
        hashrate_ths=n.hashrate_ths,
        online=n.online,
        utilization=round(n.utilization, 3),
    )
