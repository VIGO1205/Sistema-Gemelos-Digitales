from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi.responses import StreamingResponse
import io
import csv

from app.database import get_db
from app.models import Block
from app.schemas.block import BlockResponse, BlockFilter

router = APIRouter()


@router.get("", response_model=List[BlockResponse])
async def list_blocks(
    project_id: int = Query(None),
    bench: int = Query(None),
    min_cu_bayesian: float = Query(None),
    max_epistemic_unc: float = Query(None),
    category: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Block)
    filters = []
    if project_id:
        filters.append(Block.project_id == project_id)
    if bench is not None:
        filters.append(Block.bench == bench)
    if min_cu_bayesian is not None:
        filters.append(Block.cu_bayesian >= min_cu_bayesian)
    if max_epistemic_unc is not None:
        filters.append(Block.epistemic_unc <= max_epistemic_unc)
    if category:
        filters.append(Block.category == category)
    if filters:
        query = query.where(and_(*filters))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{block_id}", response_model=BlockResponse)
async def get_block(block_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.block_id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    return block


@router.get("/export/csv")
async def export_blocks_csv(
    project_id: int = Query(...),
    bench: int = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Exporta modelo de bloques a CSV compatible con Leapfrog, Surpac y Datamine."""
    query = select(Block).where(Block.project_id == project_id)
    if bench is not None:
        query = query.where(Block.bench == bench)
    result = await db.execute(query)
    blocks = result.scalars().all()

    if not blocks:
        raise HTTPException(status_code=404, detail="No hay bloques para exportar")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header compatible con software minero estándar
    writer.writerow([
        "BLOCK_ID", "BENCH", "EASTING_X", "NORTHING_Y", "ELEVATION_Z",
        "TONNAGE", "CU_BAYESIAN_PCT", "CU_BASE_KRIG_PCT", "AU_BAYESIAN_GPT",
        "AU_BASE_KRIG_GPT", "DENSITY", "LITHOLOGY", "ALTERATION",
        "DOMINANT_MINERAL", "CATEGORY_JORC", "EPistemic_UNC", "ALEATORIC_UNC",
        "TOTAL_UNC", "P10", "P50", "P90", "CONFIDENCE_PCT", "DEVIATION_PCT",
        "NEAREST_DRILLHOLE_M"
    ])

    for b in blocks:
        writer.writerow([
            b.block_id, b.bench, b.x, b.y, b.z,
            b.tonnage, b.cu_bayesian, b.cu_base, b.au_bayesian,
            b.au_base, b.density, b.lithology, b.alteration,
            b.dominant_mineral, b.category, b.epistemic_unc, b.aleatoric_unc,
            b.total_unc, b.p10, b.p50, b.p90, b.confidence_pct, b.deviation_pct,
            b.nearest_drillhole_m
        ])

    output.seek(0)
    stream = io.BytesIO(output.getvalue().encode("utf-8-sig"))

    bench_suffix = f"_BANCO_{bench}" if bench else ""
    filename = f"M6_Modelo_Bloques{bench_suffix}_{project_id}.csv"

    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
