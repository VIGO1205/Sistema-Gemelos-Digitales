from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ProcessControlPointBase(BaseModel):
    point_id: str
    blast_id: str
    timestamp: datetime
    bench: int
    tonnage: float
    plant_feed_grade: float
    predicted_base_krig: float
    predicted_bayesian: float
    predicted_active_model: Optional[float] = None
    residual_base: float
    residual_bayesian: float
    residual_active: Optional[float] = None
    cusum_high: float
    cusum_low: float
    ewma_grade: float
    ucl: float
    lcl: float
    target_grade: float


class ProcessControlPointCreate(ProcessControlPointBase):
    project_id: int


class ProcessControlPointResponse(ProcessControlPointBase):
    id: int
    project_id: int

    model_config = ConfigDict(from_attributes=True)
