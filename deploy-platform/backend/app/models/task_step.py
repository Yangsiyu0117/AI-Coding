from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("upgrade_tasks.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("service_nodes.id"), nullable=False)
    step_type = Column(String(30), default="")
    step_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), default="pending")
    rollback_status = Column(String(20), default="none")
    log_output = Column(Text, default="")
    error_message = Column(Text, default="")
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    task = relationship("UpgradeTask", back_populates="steps")
    service = relationship("Service")
    node = relationship("ServiceNode")

    @property
    def service_name(self) -> str:
        return self.service.name if self.service else ""

    @property
    def node_ip(self) -> str:
        return self.node.host_ip if self.node else ""
