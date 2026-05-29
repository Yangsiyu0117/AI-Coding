from datetime import datetime
from pydantic import BaseModel, field_validator

from app.schemas.common import TZAwareDatetime
from app.services.service_types import list_service_types


def _valid_type_names() -> set:
    return {t["name"] for t in list_service_types()}


class ServiceNodeCreate(BaseModel):
    host_ip: str
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_password: str = ""


class ServiceNodeUpdate(BaseModel):
    host_ip: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    ssh_password: str | None = None


class ServiceNodeResponse(BaseModel):
    id: int
    service_id: int
    host_ip: str
    ssh_port: int
    ssh_user: str
    status: str
    created_at: TZAwareDatetime = None

    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    environment_id: int
    name: str
    type: str
    deploy_path: str = ""
    run_script: str = "run.sh"
    start_cmd: str = ""
    stop_cmd: str = ""
    check_cmd: str = ""
    version_cmd: str = ""
    backup_pattern: str = ""
    upgrade_order: int = 0
    depends_on: str = ""
    description: str = ""
    nodes: list[ServiceNodeCreate] = []

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid = _valid_type_names()
        if v not in valid:
            raise ValueError(f"Invalid service type '{v}'. Valid types: {', '.join(sorted(valid))}")
        return v


class ServiceUpdate(BaseModel):
    environment_id: int | None = None
    name: str | None = None
    type: str | None = None
    deploy_path: str | None = None
    run_script: str | None = None
    start_cmd: str | None = None
    stop_cmd: str | None = None
    check_cmd: str | None = None
    version_cmd: str | None = None
    backup_pattern: str | None = None
    upgrade_order: int | None = None
    depends_on: str | None = None
    description: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is not None and v not in _valid_type_names():
            valid = _valid_type_names()
            raise ValueError(f"Invalid service type '{v}'. Valid types: {', '.join(sorted(valid))}")
        return v


class ServiceResponse(BaseModel):
    id: int
    environment_id: int
    name: str
    type: str
    deploy_path: str
    run_script: str
    start_cmd: str
    stop_cmd: str
    check_cmd: str
    version_cmd: str
    backup_pattern: str
    upgrade_order: int
    depends_on: str
    description: str
    nodes: list[ServiceNodeResponse] = []
    created_at: TZAwareDatetime = None
    updated_at: TZAwareDatetime = None

    model_config = {"from_attributes": True}
