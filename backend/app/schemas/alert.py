from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class AlertBase(BaseModel):
    alert_id: str
    alert_type: str
    severity: str
    bench: int
    block_id: str
    title: str
    description: str
    current_val: str
    threshold_val: str
    timestamp: datetime
    acknowledged: bool = False
    dismissed: bool = False
    assigned_role: str
    action_recommended: str


class AlertCreate(AlertBase):
    project_id: int


class AlertUpdate(BaseModel):
    acknowledged: Optional[bool] = None
    dismissed: Optional[bool] = None
    assigned_role: Optional[str] = None


class AlertResponse(AlertBase):
    id: int
    project_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
