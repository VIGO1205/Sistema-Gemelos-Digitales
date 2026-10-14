from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.responses import StreamingResponse
import io

from app.database import get_db
from app.models import Block, Project
from app.services.bayesian_engine import compute_bench_reconciliation

router = APIRouter()


@router.get("/excel")
async def export_excel(
    project_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl no está instalado")

    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    result = await db.execute(select(Block).where(Block.project_id == project_id))
    blocks = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Modelo_Bloques_M6"

    headers = [
        "ID_BLOQUE", "BANCO_Z", "ESTE_X", "NORTE_Y", "TONELAJE",
        "LEY_CU_BASE_KRIG", "LEY_CU_BAYESIANA", "VARIANZA_TOTAL",
        "INCERT_EPISTEMICA", "INCERT_ALEATORIA", "INCERT_TOTAL",
        "P10", "P50", "P90", "CONFIANZA",
        "LITOLOGIA", "ALTERACION", "MINERAL_DOMINANTE", "CATEGORIA_JORC"
    ]
    ws.append(headers)

    for b in blocks:
        ws.append([
            b.block_id, b.z, b.x, b.y, b.tonnage,
            b.cu_base, b.cu_bayesian, b.cu_variance,
            b.epistemic_unc, b.aleatoric_unc, b.total_unc,
            b.p10, b.p50, b.p90, b.confidence_pct,
            b.lithology, b.alteration, b.dominant_mineral, b.category
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"M6_Reporte_Leyes_{project.project_id}_{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/summary")
async def get_summary(
    project_id: int = Query(...),
    bench: int = Query(None),
    db: AsyncSession = Depends(get_db)
):
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    query = select(Block).where(Block.project_id == project_id)
    if bench is not None:
        query = query.where(Block.bench == bench)
    result = await db.execute(query)
    blocks = result.scalars().all()

    blocks_data = [
        {"tonnage": b.tonnage, "cu_base": b.cu_base, "cu_bayesian": b.cu_bayesian, "category": b.category}
        for b in blocks
    ]
    recon = compute_bench_reconciliation(blocks_data)

    return {
        "project": {
            "id": project.project_id,
            "name": project.name,
            "mine_site": project.mine_site,
            "epsg_code": project.epsg_code,
            "cut_off_grade": project.cut_off_grade,
            "active_bench": project.active_bench,
        },
        "reconciliation": recon,
        "total_blocks_evaluated": len(blocks),
    }
