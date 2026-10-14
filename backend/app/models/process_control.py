from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ProcessControlPoint(Base):
    __tablename__ = "process_control_points"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    point_id = Column(String(50), nullable=False)
    blast_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    bench = Column(Integer, nullable=False)
    tonnage = Column(Float, nullable=False)
    plant_feed_grade = Column(Float, nullable=False)
    predicted_base_krig = Column(Float, nullable=False)
    predicted_bayesian = Column(Float, nullable=False)
    predicted_active_model = Column(Float, nullable=True)
    residual_base = Column(Float, nullable=False)
    residual_bayesian = Column(Float, nullable=False)
    residual_active = Column(Float, nullable=True)
    cusum_high = Column(Float, nullable=False)
    cusum_low = Column(Float, nullable=False)
    ewma_grade = Column(Float, nullable=False)
    ucl = Column(Float, nullable=False)
    lcl = Column(Float, nullable=False)
    target_grade = Column(Float, nullable=False)

    project = relationship("Project", back_populates="process_control_points")
