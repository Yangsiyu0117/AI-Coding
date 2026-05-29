from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.middleware import get_current_user, require_admin
from app.config import settings
from app.database import get_db
from app.models.environment import Environment
from app.schemas.environment import EnvironmentCreate, EnvironmentResponse, EnvironmentUpdate
from app.services.ssh_executor import SSHExecutor


class SSHTestRequest(BaseModel):
    host: str
    port: int = 22
    user: str = "root"
    password: str | None = None


class SSHTestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int = 0


router = APIRouter(dependencies=[Depends(get_current_user)])


def _check_duplicate_name(db: Session, name: str, exclude_id: int | None = None):
    q = db.query(Environment).filter(Environment.name == name)
    if exclude_id is not None:
        q = q.filter(Environment.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=409, detail="Environment name already exists")


@router.get("/", response_model=list[EnvironmentResponse])
def list_environments(db: Session = Depends(get_db)):
    return db.query(Environment).all()


@router.get("/{env_id}", response_model=EnvironmentResponse)
def get_environment(env_id: int, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    return env


@router.post("/", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
def create_environment(body: EnvironmentCreate, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    _check_duplicate_name(db, body.name)
    env = Environment(name=body.name, description=body.description, ssh_default_port=body.ssh_default_port)
    db.add(env)
    db.commit()
    db.refresh(env)
    log_action(db, int(user["sub"]), "create_environment", "environment", env.id, f"name={body.name}")
    return env


@router.put("/{env_id}", response_model=EnvironmentResponse)
def update_environment(env_id: int, body: EnvironmentUpdate, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        _check_duplicate_name(db, data["name"], exclude_id=env_id)
    for key, value in data.items():
        setattr(env, key, value)
    db.commit()
    db.refresh(env)
    log_action(db, int(user["sub"]), "update_environment", "environment", env_id, f"fields={list(data.keys())}")
    return env


@router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment(env_id: int, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")
    env_name = env.name
    db.delete(env)
    db.commit()
    log_action(db, int(user["sub"]), "delete_environment", "environment", env_id, f"name={env_name}")


@router.post("/test-ssh", response_model=SSHTestResponse)
async def test_ssh_connection(body: SSHTestRequest, _: dict = Depends(require_admin)):
    executor = SSHExecutor(default_timeout=settings.ssh_default_timeout)
    result = await executor.test_connection(
        host=body.host,
        port=body.port,
        user=body.user,
        password=body.password,
    )
    return SSHTestResponse(success=result.success, message=result.message, latency_ms=result.latency_ms)
