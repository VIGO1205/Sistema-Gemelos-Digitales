from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models import Alert
from app.schemas.alert import AlertResponse, AlertUpdate

router = APIRouter()


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    project_id: int = Query(None),
    severity: str = Query(None),
    acknowledged: bool = Query(None),
    dismissed: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert)
    filters = []
    if project_id:
        filters.append(Alert.project_id == project_id)
    if severity:
        filters.append(Alert.severity == severity)
    if acknowledged is not None:
        filters.append(Alert.acknowledged == acknowledged)
    filters.append(Alert.dismissed == dismissed)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(Alert.timestamp.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alert


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alert.acknowledged = True
    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alert.dismissed = True
    await db.commit()
    await db.refresh(alert)
    return alert
