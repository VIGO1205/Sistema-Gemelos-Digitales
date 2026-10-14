from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import ProcessControlPoint
from app.schemas.process_control import ProcessControlPointResponse

router = APIRouter()


@router.get("", response_model=List[ProcessControlPointResponse])
async def list_process_control(
    project_id: int = Query(None),
    bench: int = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(ProcessControlPoint).order_by(ProcessControlPoint.timestamp)
    if project_id:
        query = query.where(ProcessControlPoint.project_id == project_id)
    if bench is not None:
        query = query.where(ProcessControlPoint.bench == bench)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/export")
async def export_process_control(
    project_id: int = Query(...),
    bench: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta datos de control de procesos para entrenamiento del Motor IA.
    Formato: lista de diccionarios con features y target.
    """
    query = select(ProcessControlPoint).where(ProcessControlPoint.project_id == project_id)
    if bench is not None:
        query = query.where(ProcessControlPoint.bench == bench)
    query = query.order_by(ProcessControlPoint.timestamp)
    result = await db.execute(query)
    points = result.scalars().all()

    if not points:
        return {"success": False, "message": "No hay datos para los criterios seleccionados", "data": []}

    # Convertir a formato utilizable por el Motor IA
    data = []
    for p in points:
        data.append({
            "point_id": p.point_id,
            "blast_id": p.blast_id,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "bench": p.bench,
            "tonnage": p.tonnage,
            "plant_feed_grade": p.plant_feed_grade,
            "predicted_base_krig": p.predicted_base_krig,
            "predicted_bayesian": p.predicted_bayesian,
            "predicted_active_model": p.predicted_active_model,
            "residual_base": p.residual_base,
            "residual_bayesian": p.residual_bayesian,
            "residual_active": p.residual_active,
        })

    return {
        "success": True,
        "count": len(data),
        "bench": bench,
        "data": data
    }
