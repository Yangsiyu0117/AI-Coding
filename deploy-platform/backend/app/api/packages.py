from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.middleware import get_current_user
from app.database import get_db
from app.models.service import Service
from app.schemas.upgrade import UpgradePackageResponse
from app.services.package_manager import PackageManager

router = APIRouter(dependencies=[Depends(get_current_user)])


def _package_response(pkg) -> UpgradePackageResponse:
    return UpgradePackageResponse(
        id=pkg.id,
        service_id=pkg.service_id,
        service_name=pkg.service.name if pkg.service else "",
        version=pkg.version,
        file_path=pkg.file_path,
        file_md5=pkg.file_md5,
        file_size=pkg.file_size,
        created_at=pkg.created_at,
    )


@router.get("/", response_model=list[UpgradePackageResponse])
def list_packages(service_id: int | None = None, db: Session = Depends(get_db)):
    manager = PackageManager(db)
    return [_package_response(p) for p in manager.list_all(service_id)]


@router.get("/{package_id}", response_model=UpgradePackageResponse)
def get_package(package_id: int, db: Session = Depends(get_db)):
    manager = PackageManager(db)
    return _package_response(manager.get(package_id))


@router.post("/upload", response_model=UpgradePackageResponse, status_code=status.HTTP_201_CREATED)
async def upload_package(
    service_id: int = Form(...),
    version: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    content = await file.read()
    manager = PackageManager(db)
    package = manager.save(
        content=content,
        filename=file.filename or "package",
        service_id=service_id,
        version=version,
        service_name=service.name,
    )
    log_action(db, int(user["sub"]), "upload_package", "package", package.id, f"service={service.name} version={version}")
    return _package_response(package)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    manager = PackageManager(db)
    pkg = manager.get(package_id)
    pkg_info = f"version={pkg.version}" if pkg else ""
    manager.delete(package_id)
    log_action(db, int(user["sub"]), "delete_package", "package", package_id, pkg_info)
