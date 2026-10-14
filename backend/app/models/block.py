from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(String(50), unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    bench = Column(Integer, nullable=False, index=True)

    dx = Column(Float, nullable=False, default=15.0)
    dy = Column(Float, nullable=False, default=15.0)
    dz = Column(Float, nullable=False, default=15.0)

    cu_base = Column(Float, nullable=False)
    cu_bayesian = Column(Float, nullable=False)
    cu_variance = Column(Float, nullable=False)
    au_base = Column(Float, nullable=False)
    au_bayesian = Column(Float, nullable=False)

    epistemic_unc = Column(Float, nullable=False)
    aleatoric_unc = Column(Float, nullable=False)
    total_unc = Column(Float, nullable=False)

    p10 = Column(Float, nullable=False)
    p50 = Column(Float, nullable=False)
    p90 = Column(Float, nullable=False)
    confidence_pct = Column(Float, nullable=False)

    tonnage = Column(Integer, nullable=False)
    density = Column(Float, nullable=False)

    lithology = Column(String(50), nullable=False)
    alteration = Column(String(50), nullable=False)
    hyperspectral_mineral = Column(String(100), nullable=False)
    dominant_mineral = Column(String(50), nullable=False)
    category = Column(String(20), nullable=False, index=True)  # Measured, Indicated, Inferred, Unclassified

    deviation_pct = Column(Float, nullable=False)
    nearest_drillhole_m = Column(Float, nullable=False)

    project = relationship("Project", back_populates="blocks")
