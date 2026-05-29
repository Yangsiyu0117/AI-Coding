from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class UpgradeTask(Base):
    __tablename__ = "upgrade_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(30), default="pending")
    failure_strategy = Column(String(20), default="stop")
    rollback_status = Column(String(20), default="none")
    is_rollback = Column(Boolean, default=False)
    timeout_seconds = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    environment = relationship("Environment", backref="upgrade_tasks")
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")
