from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    alert_type = Column(String(30), nullable=False)  # HIGH_UNCERTAINTY, GRADE_DEVIATION, DILUTION_RISK, ORE_LOSS_RISK, CALIBRATION_DRIFT
    severity = Column(String(10), nullable=False)  # CRITICAL, WARNING, INFO
    bench = Column(Integer, nullable=False)
    block_id = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=False)
    current_val = Column(String(50), nullable=False)
    threshold_val = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
    dismissed = Column(Boolean, default=False, nullable=False)
    assigned_role = Column(String(30), nullable=False)
    action_recommended = Column(String(500), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="alerts")
