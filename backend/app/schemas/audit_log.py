from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class AuditLogBase(BaseModel):
    log_id: str
    timestamp: datetime
    user_id: str
    user_name: str
    user_role: str
    action: str
    module: str
    details: str
    ip_address: str
    status: str


class AuditLogCreate(AuditLogBase):
    project_id: Optional[int] = None


class AuditLogResponse(AuditLogBase):
    id: int
    project_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
