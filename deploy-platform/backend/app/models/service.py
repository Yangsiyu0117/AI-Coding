from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)
    deploy_path = Column(String(255), default="")
    run_script = Column(String(50), default="run.sh")
    start_cmd = Column(String(255), default="")
    stop_cmd = Column(String(255), default="")
    check_cmd = Column(String(255), default="")
    version_cmd = Column(String(255), default="")
    backup_pattern = Column(String(255), default="")
    upgrade_order = Column(Integer, default=0)
    depends_on = Column(String(500), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    environment = relationship("Environment", backref="services")
    nodes = relationship("ServiceNode", back_populates="service", cascade="all, delete-orphan")
