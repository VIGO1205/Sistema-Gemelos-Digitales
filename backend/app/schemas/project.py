from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ProjectBase(BaseModel):
    project_id: str
    name: str
    mine_site: str
    country: str
    epsg_code: str
    primary_commodity: str
    secondary_commodity: str
    cut_off_grade: float = 0.35
    high_grade_threshold: float = 0.80
    density_t_m3: float = 2.72
    total_blocks: int = 0
    active_bench: int = 3170
    last_model_run: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    mine_site: Optional[str] = None
    country: Optional[str] = None
    epsg_code: Optional[str] = None
    primary_commodity: Optional[str] = None
    secondary_commodity: Optional[str] = None
    cut_off_grade: Optional[float] = None
    high_grade_threshold: Optional[float] = None
    density_t_m3: Optional[float] = None
    total_blocks: Optional[int] = None
    active_bench: Optional[int] = None
    last_model_run: Optional[datetime] = None


class ProjectResponse(ProjectBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
