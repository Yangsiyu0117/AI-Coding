from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class UpgradePackage(Base):
    __tablename__ = "upgrade_packages"
    __table_args__ = (UniqueConstraint("service_id", "version"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    version = Column(String(50), nullable=False)
    file_path = Column(String(500), default="")
    file_md5 = Column(String(64), default="")
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    service = relationship("Service", backref="packages")
