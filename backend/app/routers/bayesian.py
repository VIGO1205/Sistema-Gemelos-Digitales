from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models import Block
from app.schemas.bayesian import (
    BlockInferenceRequest,
    SimulationResult,
    BenchReconciliation,
    BayesianInferenceParams,
)
from app.services.bayesian_engine import run_monte_carlo_block_inference, compute_bench_reconciliation

router = APIRouter()


@router.post("/inference/{block_id}", response_model=SimulationResult)
async def run_inference(
    block_id: str,
    params: BayesianInferenceParams,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Block).where(Block.block_id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Bloque no encontrado")

    sim = run_monte_carlo_block_inference(
        cu_base=block.cu_base,
        cu_bayesian=block.cu_bayesian,
        epistemic_unc=block.epistemic_unc,
        aleatoric_unc=block.aleatoric_unc,
        nearest_drillhole_m=block.nearest_drillhole_m,
        tonnage=block.tonnage,
        mc_samples=params.mc_samples,
        spatial_matern_lengthscale=params.spatial_matern_lengthscale,
        epistemic_weight=params.epistemic_weight,
        aleatoric_base_noise=params.aleatoric_base_noise,
    )
    return SimulationResult(**sim)


@router.get("/reconciliation", response_model=BenchReconciliation)
async def get_reconciliation(
    project_id: int = Query(...),
    bench: int = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Block).where(Block.project_id == project_id)
    if bench is not None:
        query = query.where(Block.bench == bench)
    result = await db.execute(query)
    blocks = result.scalars().all()

    blocks_data = [
        {
            "tonnage": b.tonnage,
            "cu_base": b.cu_base,
            "cu_bayesian": b.cu_bayesian,
            "category": b.category,
        }
        for b in blocks
    ]

    recon = compute_bench_reconciliation(blocks_data)
    return BenchReconciliation(**recon)
