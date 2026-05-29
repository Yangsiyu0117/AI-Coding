from fastapi import APIRouter, Depends

from app.auth.middleware import get_current_user, require_admin
from app.config import settings
from app.services.platform_settings import get as ps_get, load as ps_load, save as ps_save

router = APIRouter()


@router.get("/upload")
def get_upload_config():
    return {
        "max_upload_size_mb": ps_get("max_upload_size_mb", settings.max_upload_size_mb),
        "allowed_extensions": ps_get("allowed_upload_extensions", settings.allowed_upload_extensions),
    }


@router.get("/app")
def get_app_config():
    return {
        "app_name": settings.app_name,
        "app_brand": ps_get("app_brand", settings.app_brand),
        "app_title": ps_get("app_title", settings.app_title),
        "version": settings.app_version,
    }


@router.get("/platform", dependencies=[Depends(get_current_user)])
def get_platform_settings():
    return ps_load()


@router.put("/platform", dependencies=[Depends(require_admin)])
def save_platform_settings(body: dict):
    ps_save(body)
    return {"status": "ok"}

