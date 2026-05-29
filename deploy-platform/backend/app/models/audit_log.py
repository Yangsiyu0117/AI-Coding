from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), default="")
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, default="")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now())
