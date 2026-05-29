from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.middleware import get_current_user, require_admin
from app.database import get_db
from app.models.environment import Environment
from app.models.service import Service
from app.models.service_node import ServiceNode
from app.schemas.service import (
    ServiceCreate,
    ServiceNodeCreate,
    ServiceNodeResponse,
    ServiceNodeUpdate,
    ServiceResponse,
    ServiceUpdate,
)
from pydantic import BaseModel

from app.services.crypto import encrypt_password
from app.services.service_types import (
    BUILTIN_TYPES,
    STEP_LABELS,
    delete_service_type,
    list_service_types,
    save_service_type,
)


class ServiceTypeBody(BaseModel):
    name: str
    label: str
    steps: list[str]
    rollbackable: list[str] = []


class ServiceTypeUpdate(BaseModel):
    label: str | None = None
    steps: list[str] | None = None
    rollbackable: list[str] | None = None

router = APIRouter(dependencies=[Depends(get_current_user)])


def _validate_environment(db: Session, environment_id: int):
    if not db.query(Environment).filter(Environment.id == environment_id).first():
        raise HTTPException(status_code=400, detail="Environment not found")


@router.get("/", response_model=list[ServiceResponse])
def list_services(environment_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Service)
    if environment_id is not None:
        query = query.filter(Service.environment_id == environment_id)
    return query.order_by(Service.upgrade_order).all()


@router.get("/types")
def get_service_types():
    return list_service_types()


@router.get("/types/step-labels")
def get_step_labels():
    return STEP_LABELS


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(body: ServiceCreate, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    _validate_environment(db, body.environment_id)
    service = Service(
        environment_id=body.environment_id,
        name=body.name,
        type=body.type,
        deploy_path=body.deploy_path,
        run_script=body.run_script,
        start_cmd=body.start_cmd,
        stop_cmd=body.stop_cmd,
        check_cmd=body.check_cmd,
        version_cmd=body.version_cmd,
        backup_pattern=body.backup_pattern,
        upgrade_order=body.upgrade_order,
        depends_on=body.depends_on,
        description=body.description,
    )
    for node_data in body.nodes:
        node = ServiceNode(
            host_ip=node_data.host_ip,
            ssh_port=node_data.ssh_port,
            ssh_user=node_data.ssh_user,
            ssh_password=encrypt_password(node_data.ssh_password),
        )
        service.nodes.append(node)
    db.add(service)
    db.commit()
    db.refresh(service)
    log_action(db, int(user["sub"]), "create_service", "service", service.id, f"name={body.name} type={body.type}")
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, body: ServiceUpdate, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    update_data = body.model_dump(exclude_unset=True)
    if "environment_id" in update_data:
        _validate_environment(db, update_data["environment_id"])
    for key, value in update_data.items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    log_action(db, int(user["sub"]), "update_service", "service", service.id, f"fields={list(update_data.keys())}")
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    svc_name = service.name
    db.delete(service)
    db.commit()
    log_action(db, int(user["sub"]), "delete_service", "service", service_id, f"name={svc_name}")


# ── Service type CRUD ──

@router.post("/types", status_code=status.HTTP_201_CREATED)
def create_service_type(body: ServiceTypeBody, user: dict = Depends(require_admin)):
    existing = {t["name"] for t in list_service_types()}
    if body.name in existing:
        raise HTTPException(status_code=400, detail=f"Service type '{body.name}' already exists")
    save_service_type(body.name, {"label": body.label, "steps": body.steps, "rollbackable": body.rollbackable})
    return {"name": body.name, "label": body.label, "steps": body.steps, "rollbackable": body.rollbackable}


@router.put("/types/{type_name}")
def update_service_type(type_name: str, body: ServiceTypeUpdate, user: dict = Depends(require_admin)):
    data = {t["name"]: t for t in list_service_types()}
    if type_name not in data:
        raise HTTPException(status_code=404, detail="Service type not found")
    current = data[type_name]
    info = {
        "label": body.label if body.label is not None else current["label"],
        "steps": body.steps if body.steps is not None else current["steps"],
        "rollbackable": body.rollbackable if body.rollbackable is not None else current["rollbackable"],
    }
    save_service_type(type_name, info)
    return {"name": type_name, **info}


@router.delete("/types/{type_name}", status_code=status.HTTP_204_NO_CONTENT)
def remove_service_type(type_name: str, user: dict = Depends(require_admin)):
    if type_name in BUILTIN_TYPES:
        raise HTTPException(status_code=400, detail=f"Cannot delete built-in type '{type_name}'")
    existing = {t["name"] for t in list_service_types()}
    if type_name not in existing:
        raise HTTPException(status_code=404, detail="Service type not found")
    delete_service_type(type_name)


@router.post("/import", response_model=list[ServiceResponse])
def import_services(
    body: list[ServiceCreate],
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body:
        raise HTTPException(status_code=400, detail="服务列表不能为空")

    created = []
    for svc_data in body:
        env = db.query(Environment).filter(Environment.id == svc_data.environment_id).first()
        if not env:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"环境 {svc_data.environment_id} 不存在")

        service = Service(
            environment_id=svc_data.environment_id,
            name=svc_data.name,
            type=svc_data.type,
            deploy_path=svc_data.deploy_path or "",
            run_script=svc_data.run_script or "run.sh",
            start_cmd=svc_data.start_cmd or "",
            stop_cmd=svc_data.stop_cmd or "",
            check_cmd=svc_data.check_cmd or "",
            version_cmd=svc_data.version_cmd or "",
            backup_pattern=svc_data.backup_pattern or "",
            upgrade_order=svc_data.upgrade_order or 0,
            depends_on=svc_data.depends_on or "",
            description=svc_data.description or "",
        )
        db.add(service)
        db.flush()

        for nd in svc_data.nodes:
            node = ServiceNode(
                service_id=service.id,
                host_ip=nd.host_ip,
                ssh_port=nd.ssh_port or 22,
                ssh_user=nd.ssh_user or "root",
                ssh_password=encrypt_password(nd.ssh_password) if nd.ssh_password else "",
            )
            db.add(node)

        db.commit()
        db.refresh(service)
        created.append(service)
        log_action(db, int(user["sub"]), "import_service", "service", service.id, f"name={svc_data.name} type={svc_data.type}")

    return created


# --- Node endpoints ---

@router.post("/{service_id}/nodes", response_model=ServiceNodeResponse, status_code=status.HTTP_201_CREATED)
def add_service_node(service_id: int, body: ServiceNodeCreate, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    node = ServiceNode(
        service_id=service_id,
        host_ip=body.host_ip,
        ssh_port=body.ssh_port,
        ssh_user=body.ssh_user,
        ssh_password=encrypt_password(body.ssh_password),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    log_action(db, int(user["sub"]), "add_node", "service_node", node.id, f"service={service.name} ip={body.host_ip}")
    return node


@router.put("/{service_id}/nodes/{node_id}", response_model=ServiceNodeResponse)
def update_service_node(service_id: int, node_id: int, body: ServiceNodeUpdate, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    node = db.query(ServiceNode).filter(ServiceNode.id == node_id, ServiceNode.service_id == service_id).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    data = body.model_dump(exclude_unset=True)
    if "ssh_password" in data:
        data["ssh_password"] = encrypt_password(data["ssh_password"])
    for key, value in data.items():
        setattr(node, key, value)
    db.commit()
    db.refresh(node)
    log_action(db, int(user["sub"]), "update_node", "service_node", node_id, f"ip={node.host_ip}")
    return node


@router.delete("/{service_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_node(service_id: int, node_id: int, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    node = db.query(ServiceNode).filter(ServiceNode.id == node_id, ServiceNode.service_id == service_id).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    ip_addr = node.host_ip
    db.delete(node)
    db.commit()
    log_action(db, int(user["sub"]), "delete_node", "service_node", node_id, f"ip={ip_addr}")
