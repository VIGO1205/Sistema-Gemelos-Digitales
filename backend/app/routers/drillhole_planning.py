from typing import List, Optional
from datetime import datetime
from math import cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Block, Project
from app.schemas.drillhole_planning import (
    DrillTargetRequest,
    DrillTargetResult,
    DrillholePlanningResponse,
    DrillholeRecommendation,
)

router = APIRouter(prefix="/api/drillhole-planning", tags=["Planificación de Sondajes"])


def compute_priority_score(block) -> float:
    """Calcula una puntuación de prioridad de 0 a 100 para un bloque."""
    score = 0.0

    # 1. Incertidumbre epistémica (30 pts) — mayor incertidumbre = mayor prioridad
    unc = block.epistemic_unc or 0
    score += min(30, unc * 150)  # σ=0.20 → 30 pts

    # 2. Distancia al sondaje más cercano (25 pts) — lejos = poco muestreado
    dist = block.nearest_drillhole_m or 0
    score += min(25, dist * 0.25)  # 100m → 25 pts

    # 3. Etiqueta interna del escenario (25 pts)
    cat_bonus = {
        'Inferred': 25,
        'Indicated': 10,
        'Measured': 2,
        'Unclassified': 15,
    }
    score += cat_bonus.get(block.category, 0)

    # 4. Ley Cu interesante (15 pts) — ni muy baja ni ya bien conocida
    cu = block.cu_bayesian or 0
    if 0.40 <= cu <= 1.50:
        score += 15
    elif 0.20 <= cu < 0.40:
        score += 8
    else:
        score += 3

    # 5. Tamaño del bloque / tonelaje (5 pts)
    ton = block.tonnage or 0
    score += min(5, ton / 5000)

    return round(min(100, score), 2)


def suggest_drillhole_type(depth_m: int) -> str:
    if depth_m <= 30:
        return "RC (Circulación Reversa)"
    elif depth_m <= 100:
        return "DDH Diamantino"
    else:
        return "DDH Diamantino Extendido"


def suggest_depth(category: str, nearest_dist: float) -> int:
    base = 60
    if category == 'Inferred':
        base += 20
    if nearest_dist > 150:
        base += 15
    return min(200, base)


def target_category(current: str) -> str:
    upgrades = {
        'Inferred': 'Indicado',
        'Indicated': 'Medido',
        'Measured': 'Medido',
        'Unclassified': 'Inferido',
    }
    return upgrades.get(current, current)


@router.get("", response_model=DrillholePlanningResponse)
async def get_drillhole_planning(
    project_id: int = Query(...),
    bench: int = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
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

    if not blocks:
        raise HTTPException(status_code=404, detail="No hay bloques para analizar")

    # Calcular estadísticas globales
    avg_unc = sum(b.epistemic_unc or 0 for b in blocks) / len(blocks)
    avg_dist = sum(b.nearest_drillhole_m or 0 for b in blocks) / len(blocks)
    inferred_count = sum(1 for b in blocks if b.category == 'Inferred')

    # Scorear todos los bloques
    scored = []
    for b in blocks:
        score = compute_priority_score(b)
        scored.append((score, b))

    # Ordenar por score descendente
    scored.sort(key=lambda x: x[0], reverse=True)

    recommendations: List[DrillholeRecommendation] = []
    for rank, (score, b) in enumerate(scored[:limit], start=1):
        depth = suggest_depth(b.category, b.nearest_drillhole_m or 0)
        dh_type = suggest_drillhole_type(depth)
        tgt_cat = target_category(b.category)

        # Justificación personalizada
        reasons = []
        if b.epistemic_unc and b.epistemic_unc > 0.15:
            reasons.append(f"alta incertidumbre epistémica (σ={b.epistemic_unc:.2f}% Cu)")
        if b.nearest_drillhole_m and b.nearest_drillhole_m > 100:
            reasons.append(f"el sondaje más cercano está a {b.nearest_drillhole_m:.0f}m")
        if b.category == 'Inferred':
            reasons.append("etiqueta interna 'Inferido' y poca cobertura de sondajes")
        elif b.category == 'Indicated':
            reasons.append("etiqueta interna 'Indicado' con cobertura mejorable")

        if not reasons:
            reasons.append("buen balance de ley e incertidumbre para confirmar el modelo")

        justification = (
            f"El bloque {b.block_id} en el banco {b.bench}m presenta {', '.join(reasons)}. "
            f"Se propone evaluar un {dh_type} de ~{depth}m en las coordenadas indicadas. "
            f"Una mejora de cobertura sería hipotética hasta disponer de nuevas muestras; '{tgt_cat}' es solo una etiqueta de escenario."
        )

        recommendations.append(DrillholeRecommendation(
            rank=rank,
            block_id=b.block_id,
            bench=b.bench,
            easting_x=round(b.x, 1),
            northing_y=round(b.y, 1),
            elevation_z=round(b.z, 1),
            cu_bayesian=round(b.cu_bayesian, 3),
            epistemic_unc=round(b.epistemic_unc, 3),
            nearest_drillhole_m=round(b.nearest_drillhole_m, 1),
            current_category=b.category,
            target_category=tgt_cat,
            suggested_depth_m=depth,
            suggested_type=dh_type,
            priority_score=score,
            justification=justification,
        ))

    return DrillholePlanningResponse(
        project_name=project.name,
        total_blocks_analyzed=len(blocks),
        recommendations=recommendations,
        summary={
            "avg_epistemic_uncertainty": round(avg_unc, 3),
            "avg_nearest_drillhole_m": round(avg_dist, 1),
            "inferred_blocks_count": inferred_count,
            "inferred_blocks_pct": round(inferred_count / len(blocks) * 100, 1),
        },
    )


def bench_index(bench: int) -> int:
    return max(0, (3200 - bench) // 15)


def distance_to_proposed_hole(block: Block, collar: Block, depth_m: float, azimuth: float, dip: float) -> float:
    """Distancia del centro del bloque al segmento 3D del sondaje propuesto."""
    az = radians(azimuth)
    inclination = radians(dip)
    direction = (cos(inclination) * sin(az), cos(inclination) * cos(az), sin(inclination))
    offset = (block.x - collar.x, block.y - collar.y, block.z - collar.z)
    along = sum(offset[i] * direction[i] for i in range(3))
    along = max(0.0, min(float(depth_m), along))
    return sqrt(sum((offset[i] - along * direction[i]) ** 2 for i in range(3)))


def projected_block_state(block: Block, distance_m: float) -> tuple[float, str, bool]:
    """Proyecta un cambio hipotético de cobertura sin modificar el bloque."""
    original_unc = block.epistemic_unc or 0.0
    nearest = block.nearest_drillhole_m
    if nearest is not None and distance_m >= nearest:
        return original_unc, block.category, False

    b_idx = bench_index(block.bench)
    modeled_unc = round(0.04 + (distance_m / 100) * 0.22 + (b_idx * 0.02), 3)
    projected_unc = min(original_unc, modeled_unc) if original_unc > 0 else modeled_unc
    if distance_m <= 25 and projected_unc < 0.08:
        category = "Measured"
    elif distance_m <= 50 and projected_unc < 0.16:
        category = "Indicated"
    elif distance_m <= 90:
        category = "Inferred"
    else:
        category = "Unclassified"
    rank = {"Unclassified": 0, "Inferred": 1, "Indicated": 2, "Measured": 3}
    if rank.get(category, 0) < rank.get(block.category, 0):
        category = block.category
    return projected_unc, category, True


@router.post("/drill", response_model=DrillTargetResult)
async def drill_recommended_hole(
    payload: DrillTargetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Simula un sondaje propuesto; no crea ensayos ni modifica la base de datos."""
    block = (
        await db.execute(
            select(Block).where(Block.project_id == payload.project_id, Block.block_id == payload.block_id)
        )
    ).scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Bloque objetivo no encontrado")

    project = (
        await db.execute(select(Project).where(Project.id == payload.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    bench = block.bench or round(block.z or 0)
    depth = payload.depth_m or suggest_depth(block.category, block.nearest_drillhole_m or 0)
    hole_type = payload.hole_type or suggest_drillhole_type(depth)
    azimuth = payload.azimuth if payload.azimuth is not None else 0.0
    dip = payload.dip if payload.dip is not None else -75.0

    hole_id = f"SIM-{block.block_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Proyección ilustrativa para los bloques de este escenario.
    all_blocks = (
        (await db.execute(select(Block).where(Block.project_id == project.id))).scalars().all()
    )
    if not all_blocks:
        raise HTTPException(status_code=404, detail="No hay bloques para simular")

    avg_unc_before = round(sum(b.epistemic_unc or 0 for b in all_blocks) / len(all_blocks), 4)

    affected = 0
    upgraded = 0
    projected_uncertainties = []
    for b in all_blocks:
        dist = distance_to_proposed_hole(b, block, depth, azimuth, dip)
        projected_unc, projected_category, improves_coverage = projected_block_state(b, dist)
        projected_uncertainties.append(projected_unc)
        if improves_coverage:
            affected += 1
        if improves_coverage and projected_category != b.category:
            upgraded += 1
    avg_unc_after = round(sum(projected_uncertainties) / len(all_blocks), 4)

    return DrillTargetResult(
        message=(
            f"Escenario {hole_id}: sondaje propuesto de {depth}m sobre {block.block_id}. "
            f"Cobertura potencial mejorada en {affected} bloques; {upgraded} cambiarían de etiqueta interna. "
            "No se perforó ni se modificaron las leyes o categorías de la base de datos."
        ),
        hole_id=hole_id,
        block_id=block.block_id,
        bench=bench,
        depth_m=depth,
        hole_type=hole_type,
        affected_blocks=affected,
        upgraded_blocks=upgraded,
        avg_epistemic_unc_before=avg_unc_before,
        avg_epistemic_unc_after=avg_unc_after,
    )
