from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    role: str | None = None
    password: str | None = None
