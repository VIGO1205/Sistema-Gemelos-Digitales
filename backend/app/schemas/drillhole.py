from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import List, Optional


class DrillholeSampleBase(BaseModel):
    from_m: float
    to_m: float
    length_m: float
    cu_pct: float
    au_gpt: float
    lithology: str
    alteration: str
    recovery_pct: float
    rqd_pct: float


class DrillholeSampleCreate(DrillholeSampleBase):
    pass


class DrillholeSampleResponse(DrillholeSampleBase):
    id: int
    drillhole_id: int

    model_config = ConfigDict(from_attributes=True)


class DrillholeBase(BaseModel):
    hole_id: str
    hole_type: str
    x: float
    y: float
    z: float
    total_depth_m: float
    azimuth: float
    dip: float
    date_drilled: date


class DrillholeCreate(DrillholeBase):
    project_id: int
    samples: Optional[List[DrillholeSampleCreate]] = []


class DrillholeResponse(DrillholeBase):
    id: int
    project_id: int
    samples: List[DrillholeSampleResponse] = []

    model_config = ConfigDict(from_attributes=True)
