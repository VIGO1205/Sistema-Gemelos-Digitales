from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    mine_site = Column(String(200), nullable=False)
    country = Column(String(100), nullable=False)
    epsg_code = Column(String(50), nullable=False)
    primary_commodity = Column(String(10), nullable=False)
    secondary_commodity = Column(String(10), nullable=False)
    cut_off_grade = Column(Float, nullable=False, default=0.35)
    high_grade_threshold = Column(Float, nullable=False, default=0.80)
    density_t_m3 = Column(Float, nullable=False, default=2.72)
    total_blocks = Column(Integer, nullable=False, default=0)
    active_bench = Column(Integer, nullable=False, default=3170)
    last_model_run = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    blocks = relationship("Block", back_populates="project")
    drillholes = relationship("Drillhole", back_populates="project")
    hyperspectral_signatures = relationship("HyperspectralSignature", back_populates="project")
    alerts = relationship("Alert", back_populates="project")
    audit_logs = relationship("AuditLog", back_populates="project")
    process_control_points = relationship("ProcessControlPoint", back_populates="project")
    training_history = relationship("TrainingLossHistory", back_populates="project")
