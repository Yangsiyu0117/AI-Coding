from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.middleware import get_current_user
from app.config import settings
from app.database import get_db
from app.schemas.patrol import PatrolRunRequest, PatrolRunResponse
from app.services.patrol import PatrolService

router = APIRouter(dependencies=[Depends(get_current_user)])

patrol_service = PatrolService(default_timeout=settings.ssh_default_timeout)


@router.post("/run", response_model=PatrolRunResponse)
async def run_patrol(body: PatrolRunRequest, db: Session = Depends(get_db)):
    data = await patrol_service.run_patrol(db, body.environment_id, body.service_ids)
    return PatrolRunResponse(**data)
