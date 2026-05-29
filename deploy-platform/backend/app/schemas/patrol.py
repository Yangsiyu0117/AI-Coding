from datetime import datetime
from pydantic import BaseModel


class NodePatrolResult(BaseModel):
    node_id: int
    host_ip: str
    service_name: str
    status: str
    detail: str
    checked_at: datetime | None = None


class PatrolRunRequest(BaseModel):
    environment_id: int
    service_ids: list[int] | None = None


class PatrolRunResponse(BaseModel):
    environment_id: int
    total_nodes: int
    healthy_nodes: int
    unhealthy_nodes: int
    results: list[NodePatrolResult]
    checked_at: datetime
