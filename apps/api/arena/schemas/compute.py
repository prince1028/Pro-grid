from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from arena.models import NodeClass, WorkloadKind, WorkloadState


class WorkloadDTO(BaseModel):
    id: str
    kind: WorkloadKind
    priority: float
    demand_kw: float
    state: WorkloadState
    assigned_node: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    rationale: str | None = None


class WorkloadList(BaseModel):
    items: list[WorkloadDTO]
    total: int


class CreateWorkload(BaseModel):
    kind: WorkloadKind
    priority: float = Field(0.5, ge=0.0, le=1.0)
    demand_kw: float = Field(..., gt=0.0)


class CreatedWorkload(BaseModel):
    id: str
    state: WorkloadState


class ComputeNodeDTO(BaseModel):
    id: str
    region: str
    class_name: NodeClass
    power_draw_kw: float
    tflops: float
    hashrate_ths: float
    online: bool
    utilization: float = 0.0


class AllocatorExplain(BaseModel):
    workload_id: str
    decision: Literal["allocated", "deferred", "rejected"]
    chosen_node: str | None = None
    score: float
    rationale: str
    considered: list[dict] = Field(default_factory=list)
