from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.database import Base


class Drillhole(Base):
    __tablename__ = "drillholes"

    id = Column(Integer, primary_key=True, index=True)
    hole_id = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    hole_type = Column(String(30), nullable=False)  # DIAMOND_DDH, REVERSE_CIRCULATION_RC, BLASTHOLE_TRICONO
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    total_depth_m = Column(Float, nullable=False)
    azimuth = Column(Float, nullable=False)
    dip = Column(Float, nullable=False)
    date_drilled = Column(Date, nullable=False)

    project = relationship("Project", back_populates="drillholes")
    samples = relationship("DrillholeSample", back_populates="drillhole", cascade="all, delete-orphan")


class DrillholeSample(Base):
    __tablename__ = "drillhole_samples"

    id = Column(Integer, primary_key=True, index=True)
    drillhole_id = Column(Integer, ForeignKey("drillholes.id"), nullable=False, index=True)

    from_m = Column(Float, nullable=False)
    to_m = Column(Float, nullable=False)
    length_m = Column(Float, nullable=False)
    cu_pct = Column(Float, nullable=False)
    au_gpt = Column(Float, nullable=False)
    lithology = Column(String(50), nullable=False)
    alteration = Column(String(50), nullable=False)
    recovery_pct = Column(Float, nullable=False)
    rqd_pct = Column(Float, nullable=False)

    drillhole = relationship("Drillhole", back_populates="samples")
