from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.database import Base


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, default="")
    ssh_default_port = Column(Integer, default=22)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
