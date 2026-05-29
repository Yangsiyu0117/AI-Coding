from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import TZAwareDatetime


class UpgradePackageCreate(BaseModel):
    service_id: int
    version: str


class UpgradePackageResponse(BaseModel):
    id: int
    service_id: int
    service_name: str = ""
    version: str
    file_path: str
    file_md5: str
    file_size: int
    created_at: TZAwareDatetime = None

    model_config = {"from_attributes": True}


class UpgradeTaskCreate(BaseModel):
    environment_id: int
    title: str
    service_ids: list[int] = []
    package_ids: list[int] = []
    failure_strategy: str = "stop"
    timeout_seconds: int | None = None


class TaskStepResponse(BaseModel):
    id: int
    task_id: int
    service_id: int
    node_id: int
    step_type: str
    step_order: int
    status: str
    rollback_status: str = "none"
    log_output: str
    error_message: str
    retry_count: int = 0
    started_at: TZAwareDatetime = None
    finished_at: TZAwareDatetime = None
    service_name: str = ""
    node_ip: str = ""

    model_config = {"from_attributes": True}


class UpgradeTaskResponse(BaseModel):
    id: int
    environment_id: int
    title: str
    status: str
    failure_strategy: str = "stop"
    rollback_status: str = "none"
    is_rollback: bool = False
    created_by: int | None = None
    timeout_seconds: int | None = None
    steps: list[TaskStepResponse] = []
    created_at: TZAwareDatetime = None
    started_at: TZAwareDatetime = None
    finished_at: TZAwareDatetime = None

    model_config = {"from_attributes": True}
