from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Drillhole
from app.schemas.drillhole import DrillholeResponse, DrillholeCreate

router = APIRouter()


@router.get("", response_model=List[DrillholeResponse])
async def list_drillholes(project_id: int = None, db: AsyncSession = Depends(get_db)):
    query = select(Drillhole).options(selectinload(Drillhole.samples))
    if project_id:
        query = query.where(Drillhole.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{hole_id}", response_model=DrillholeResponse)
async def get_drillhole(hole_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Drillhole).options(selectinload(Drillhole.samples)).where(Drillhole.hole_id == hole_id)
    )
    drillhole = result.scalar_one_or_none()
    if not drillhole:
        raise HTTPException(status_code=404, detail="Sondaje no encontrado")
    return drillhole


@router.post("", response_model=DrillholeResponse, status_code=201)
async def create_drillhole(data: DrillholeCreate, db: AsyncSession = Depends(get_db)):
    from app.models import DrillholeSample
    drillhole = Drillhole(
        hole_id=data.hole_id,
        project_id=data.project_id,
        hole_type=data.hole_type,
        x=data.x,
        y=data.y,
        z=data.z,
        total_depth_m=data.total_depth_m,
        azimuth=data.azimuth,
        dip=data.dip,
        date_drilled=data.date_drilled,
    )
    db.add(drillhole)
    await db.flush()
    for s in data.samples or []:
        sample = DrillholeSample(drillhole_id=drillhole.id, **s.model_dump())
        db.add(sample)
    await db.commit()
    await db.refresh(drillhole)
    return drillhole
