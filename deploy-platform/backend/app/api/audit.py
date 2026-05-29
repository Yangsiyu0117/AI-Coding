from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.middleware import get_current_user
from app.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.common import TZAwareDatetime

router = APIRouter(dependencies=[Depends(get_current_user)])


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    target_type: str
    target_id: int | None
    detail: str
    ip_address: str
    created_at: TZAwareDatetime = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditLogResponse])
@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    user_id: int | None = None,
    action: str | None = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
