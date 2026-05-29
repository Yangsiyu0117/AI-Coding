from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class ServiceNode(Base):
    __tablename__ = "service_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    host_ip = Column(String(50), nullable=False)
    ssh_port = Column(Integer, default=22)
    ssh_user = Column(String(50), default="root")
    ssh_password = Column(String(255), default="")
    status = Column(String(20), default="unknown")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    service = relationship("Service", back_populates="nodes")
