import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload

from app.auth.audit import log_action
from app.auth.jwt_handler import decode_access_token
from app.auth.middleware import get_current_user, require_admin
from app.database import get_db
from app.models.service import Service
from app.models.task_step import TaskStep
from app.models.upgrade_package import UpgradePackage
from app.models.upgrade_task import UpgradeTask
from app.schemas.upgrade import UpgradeTaskCreate, UpgradeTaskResponse
from app.services.upgrade_engine import UpgradeEngine, get_queue

router = APIRouter(dependencies=[Depends(get_current_user)])

# WebSocket router without HTTPBearer auth — browser WebSocket API cannot send custom headers
ws_router = APIRouter()

engine = UpgradeEngine()


@router.get("/", response_model=list[UpgradeTaskResponse])
def list_tasks(environment_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(UpgradeTask).options(
        joinedload(UpgradeTask.steps)
        .joinedload(TaskStep.service),
        joinedload(UpgradeTask.steps)
        .joinedload(TaskStep.node),
    )
    if environment_id is not None:
        query = query.filter(UpgradeTask.environment_id == environment_id)
    return query.order_by(UpgradeTask.created_at.desc()).all()


@router.get("/{task_id}", response_model=UpgradeTaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = (
        db.query(UpgradeTask)
        .options(
            joinedload(UpgradeTask.steps)
            .joinedload(TaskStep.service),
            joinedload(UpgradeTask.steps)
            .joinedload(TaskStep.node),
        )
        .filter(UpgradeTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/", response_model=UpgradeTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    body: UpgradeTaskCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.service_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="service_ids must not be empty")

    services = db.query(Service).filter(Service.id.in_(body.service_ids)).all()
    if len(services) != len(body.service_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Some service_ids not found")

    env_ids = {s.environment_id for s in services}
    if len(env_ids) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All services must belong to the same environment")
    environment_id = env_ids.pop()
    if body.environment_id and body.environment_id != environment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="environment_id does not match services")

    for svc in services:
        if not svc.nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Service '{svc.name}' has no nodes configured",
            )

    if body.package_ids:
        packages = db.query(UpgradePackage).filter(UpgradePackage.id.in_(body.package_ids)).all()
        if len(packages) != len(body.package_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Some package_ids not found")

    strategy = body.failure_strategy
    if strategy not in ("stop", "continue", "rollback"):
        strategy = "stop"

    task = UpgradeTask(
        environment_id=environment_id,
        title=body.title,
        status="pending",
        failure_strategy=strategy,
        timeout_seconds=body.timeout_seconds,
        created_by=int(user.get("sub", 0)),
    )
    db.add(task)
    db.flush()

    engine.create_steps(db, task, body.service_ids, body.package_ids)

    db.refresh(task)
    log_action(
        db, int(user["sub"]), "create_upgrade_task", "upgrade_task", task.id,
        f"title={body.title} services={body.service_ids} strategy={strategy}",
    )
    return task


@router.post("/{task_id}/start")
async def start_task(task_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task status is '{task.status}', expected 'pending'")

    asyncio.create_task(engine.run_task(task_id))
    log_action(db, int(user["sub"]), "start_upgrade", "upgrade_task", task_id, f"title={task.title}")
    return {"message": "Task started", "task_id": task_id}


@router.post("/{task_id}/rollback")
async def rollback_task(task_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.rollback_status not in ("none",):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rollback already in progress (status: {task.rollback_status})")
    asyncio.create_task(engine.rollback_task(task_id))
    log_action(db, int(user["sub"]), "rollback_task", "upgrade_task", task_id, f"title={task.title}")
    return {"message": "Rollback started", "task_id": task_id}


@router.post("/{task_id}/pause")
def pause_task(task_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task status is '{task.status}', expected 'running'")
    engine.request_pause(task_id)
    log_action(db, int(user["sub"]), "pause_upgrade", "upgrade_task", task_id)
    return {"message": "Pause requested", "task_id": task_id}


@router.post("/{task_id}/resume")
def resume_task(task_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "paused":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task status is '{task.status}', expected 'paused'")
    engine.request_resume(task_id)
    log_action(db, int(user["sub"]), "resume_upgrade", "upgrade_task", task_id)
    return {"message": "Resume requested", "task_id": task_id}


@router.post("/{task_id}/stop")
def stop_task(task_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status not in ("running", "paused"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task status is '{task.status}', cannot stop")
    engine.request_stop(task_id)
    log_action(db, int(user["sub"]), "stop_upgrade", "upgrade_task", task_id)
    return {"message": "Stop requested", "task_id": task_id}


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task_title = task.title
    db.delete(task)
    db.commit()
    log_action(db, int(user["sub"]), "delete_upgrade_task", "upgrade_task", task_id, f"title={task_title}")


@router.post("/{task_id}/retry-step/{step_id}")
async def retry_step(task_id: int, step_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    step = db.query(TaskStep).filter(TaskStep.id == step_id, TaskStep.task_id == task_id).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="步骤不存在")
    if step.status != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能重试失败的步骤")

    # Reset step
    step.status = "pending"
    step.error_message = ""
    step.retry_count = (step.retry_count or 0) + 1
    step.log_output = (step.log_output or "") + f"\n--- 第{step.retry_count}次重试 ---\n"
    db.commit()

    # If task was failed, set back to running
    if task.status == "failed":
        task.status = "running"
        db.commit()

    # Launch retry in background
    asyncio.create_task(engine.retry_step(task_id, step_id))
    log_action(db, int(user["sub"]), "retry_step", "task_step", step_id, f"task_id={task_id}")
    return {"message": "步骤已开始重试"}


@ws_router.websocket("/ws/{task_id}")
async def websocket_task_logs(websocket: WebSocket, task_id: int, token: str = ""):
    # Browser WebSocket API cannot send Authorization header, so we accept token via query parameter
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return
    await websocket.accept()
    queue = get_queue(task_id)
    try:
        while True:
            msg = await queue.get()
            if msg is None:
                break
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
