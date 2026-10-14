from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    timestamp = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(String(50), nullable=False)
    user_name = Column(String(100), nullable=False)
    user_role = Column(String(30), nullable=False)
    action = Column(String(50), nullable=False)
    module = Column(String(50), nullable=False)
    details = Column(String(1000), nullable=False)
    ip_address = Column(String(50), nullable=False)
    status = Column(String(10), nullable=False)  # SUCCESS, WARNING, BLOCKED

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="audit_logs")
