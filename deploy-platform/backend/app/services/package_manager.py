import hashlib
import logging
import os

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.upgrade_package import UpgradePackage

logger = logging.getLogger("deploy_platform")


class PackageManager:
    """升级包管理 — 所有包操作的单一切入点"""

    def __init__(self, db: Session):
        self.db = db

    def check_duplicate_version(self, service_id: int, version: str) -> None:
        exists = (
            self.db.query(UpgradePackage)
            .filter(UpgradePackage.service_id == service_id, UpgradePackage.version == version)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail=f"Version '{version}' already exists for this service")

    def validate_extension(self, filename: str) -> None:
        lower = filename.lower()
        # Allow files without extension (e.g. Go binaries)
        if "." not in lower:
            return
        from app.services.platform_settings import get as ps_get
        extensions = ps_get("allowed_upload_extensions", settings.allowed_upload_extensions)
        for ext in extensions:
            if lower.endswith(ext):
                return
        allowed = ", ".join(extensions) + ", 或无后缀的二进制文件"
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {allowed}")

    def validate_file_size(self, file_size: int) -> None:
        limit = settings.max_upload_size_mb * 1024 * 1024
        if file_size > limit:
            raise HTTPException(status_code=413, detail=f"File too large. Max: {settings.max_upload_size_mb} MB")

    def save(self, content: bytes, filename: str, service_id: int, version: str, service_name: str) -> UpgradePackage:
        self.check_duplicate_version(service_id, version)
        self.validate_extension(filename)

        file_size = len(content)
        self.validate_file_size(file_size)

        file_md5 = hashlib.md5(content).hexdigest()
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, filename)

        with open(file_path, "wb") as f:
            f.write(content)

        package = UpgradePackage(
            service_id=service_id,
            version=version,
            file_path=file_path,
            file_md5=file_md5,
            file_size=file_size,
        )
        self.db.add(package)
        try:
            self.db.commit()
        except Exception:
            logger.exception(f"Failed to save package: file={file_path}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            raise

        self.db.refresh(package)
        return package

    def get(self, package_id: int) -> UpgradePackage:
        package = (
            self.db.query(UpgradePackage)
            .options(joinedload(UpgradePackage.service))
            .filter(UpgradePackage.id == package_id)
            .first()
        )
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        return package

    def list_all(self, service_id: int | None = None) -> list[UpgradePackage]:
        query = self.db.query(UpgradePackage).options(joinedload(UpgradePackage.service))
        if service_id is not None:
            query = query.filter(UpgradePackage.service_id == service_id)
        return query.order_by(UpgradePackage.created_at.desc()).all()

    def delete(self, package_id: int) -> None:
        package = self.get(package_id)
        if package.file_path and os.path.exists(package.file_path):
            os.remove(package.file_path)
        self.db.delete(package)
        self.db.commit()
