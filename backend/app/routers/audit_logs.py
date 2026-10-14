from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import AuditLog
from app.schemas.audit_log import AuditLogResponse

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    project_id: int = Query(None),
    user_role: str = Query(None),
    action: str = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if project_id:
        query = query.where(AuditLog.project_id == project_id)
    if user_role:
        query = query.where(AuditLog.user_role == user_role)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()
