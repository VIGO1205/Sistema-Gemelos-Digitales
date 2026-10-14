from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class HyperspectralSignature(Base):
    __tablename__ = "hyperspectral_signatures"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    mineral = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)
    color = Column(String(20), nullable=False)
    spectrum = Column(JSON, nullable=False)  # [{"wavelength": 450, "reflectance": 0.18}, ...]

    project = relationship("Project", back_populates="hyperspectral_signatures")
