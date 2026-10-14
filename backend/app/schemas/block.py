from pydantic import BaseModel, ConfigDict
from typing import Optional


class BlockBase(BaseModel):
    block_id: str
    x: float
    y: float
    z: float
    bench: int
    dx: float = 15.0
    dy: float = 15.0
    dz: float = 15.0
    cu_base: float
    cu_bayesian: float
    cu_variance: float
    au_base: float
    au_bayesian: float
    epistemic_unc: float
    aleatoric_unc: float
    total_unc: float
    p10: float
    p50: float
    p90: float
    confidence_pct: float
    tonnage: int
    density: float
    lithology: str
    alteration: str
    hyperspectral_mineral: str
    dominant_mineral: str
    category: str
    deviation_pct: float
    nearest_drillhole_m: float


class BlockCreate(BlockBase):
    project_id: int


class BlockUpdate(BaseModel):
    cu_base: Optional[float] = None
    cu_bayesian: Optional[float] = None
    cu_variance: Optional[float] = None
    au_base: Optional[float] = None
    au_bayesian: Optional[float] = None
    epistemic_unc: Optional[float] = None
    aleatoric_unc: Optional[float] = None
    total_unc: Optional[float] = None
    p10: Optional[float] = None
    p50: Optional[float] = None
    p90: Optional[float] = None
    confidence_pct: Optional[float] = None
    category: Optional[str] = None
    deviation_pct: Optional[float] = None
    nearest_drillhole_m: Optional[float] = None


class BlockResponse(BlockBase):
    id: int
    project_id: int

    model_config = ConfigDict(from_attributes=True)


class BlockFilter(BaseModel):
    project_id: Optional[int] = None
    bench: Optional[int] = None
    min_cu_bayesian: Optional[float] = None
    max_epistemic_unc: Optional[float] = None
    category: Optional[str] = None
