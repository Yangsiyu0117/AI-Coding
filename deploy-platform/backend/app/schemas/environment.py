from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TZAwareDatetime


class EnvironmentCreate(BaseModel):
    name: str
    description: str = ""
    ssh_default_port: int = 22


class EnvironmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    ssh_default_port: int | None = None


class EnvironmentResponse(BaseModel):
    id: int
    name: str
    description: str
    ssh_default_port: int
    created_at: TZAwareDatetime = None
    updated_at: TZAwareDatetime = None

    model_config = {"from_attributes": True}
