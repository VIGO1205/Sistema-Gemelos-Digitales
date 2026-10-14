from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional


class SpectralPoint(BaseModel):
    wavelength: float
    reflectance: float


class HyperspectralSignatureBase(BaseModel):
    mineral: str
    code: str
    color: str
    spectrum: List[SpectralPoint]


class HyperspectralSignatureCreate(HyperspectralSignatureBase):
    project_id: int


class HyperspectralSignatureResponse(HyperspectralSignatureBase):
    id: int
    project_id: int

    model_config = ConfigDict(from_attributes=True)
