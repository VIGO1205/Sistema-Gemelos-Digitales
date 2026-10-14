from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Block, Project
from app.schemas.economics import (
    EconomicAnalysisResponse,
    EconomicBlockSummary,
    EconomicCutoff,
    EconomicCutoffsResponse,
    EconomicParams,
    LithologyRecovery,
)

router = APIRouter(prefix="/api/economics", tags=["Análisis Económico"])

# Parámetros base — valores de referencia publicados (SNL/CostMine 2024-25, LME spot).
# Todos son sobrescribibles vía query params para escenarios.
LB_PER_TON = 2204.62
G_PER_TROY_OZ = 31.1035

DEFAULT_CU_PRICE_USD_LB = 4.20          # LME spot (referencia 2026, editable)
DEFAULT_AU_PRICE_USD_OZ = 2200.0        # ~USD 2,200/oz
DEFAULT_AU_PRICE_USD_G = DEFAULT_AU_PRICE_USD_OZ / G_PER_TROY_OZ  # ~70.73 USD/g

# Costos mineros por actividad (USD/ton movida) — referencia CostMine open pit 2025
DEFAULT_DRILLING_USD_TON = 1.20
DEFAULT_BLASTING_USD_TON = 1.80
DEFAULT_LOADING_USD_TON = 1.90
DEFAULT_HAULING_BASE_USD_TON = 3.10      # acarreo dist. corta
DEFAULT_HAULING_SLOPE_USD_TON_M = 0.035  # acarreo incremental por metro de profundidad

# Costos de proceso (USD/ton procesada) + G&A
DEFAULT_PROCESSING_USD_TON = 13.50       # chancado + molienda + flotación + relaves
DEFAULT_G_AND_A_USD_TON = 2.50

# Fundición / refino / transporte del concentrado
DEFAULT_CONCENTRATE_CU_PCT = 27.0        # ley del concentrado
DEFAULT_PAYABILITY_CU_PCT = 96.5
DEFAULT_PAYABILITY_AU_PCT = 90.0
DEFAULT_TC_USD_T = 80.0                  # cargo fundición (TC)
DEFAULT_RC_USD_LB = 0.05                 # cargo refino (RC)
DEFAULT_FREIGHT_USD_T = 45.0             # transporte + puerto + seguros

# Recuperación metalúrgica por litología (típica Cu-Au pórfido / brecha / skarn)
DEFAULT_RECOVERY = {
    "Pórfido Cuprífero": {"cu": 90.0, "au": 65.0},
    "Brecha Hidrotermal": {"cu": 85.0, "au": 60.0},
    "Skarn Mineralizado": {"cu": 82.0, "au": 55.0},
    "Andesita Huinquintipa": {"cu": 80.0, "au": 50.0},
}
DEFAULT_RECOVERY_FALLBACK = {"cu": 80.0, "au": 55.0}

MIN_CU_GRADE = 0.05  # ley mínima modelada


def get_recovery(lithology: Optional[str], overrides: Optional[dict] = None) -> tuple[float, float]:
    base = DEFAULT_RECOVERY.get(lithology or "") or DEFAULT_RECOVERY_FALLBACK
    if overrides:
        o = overrides.get(lithology or "") or overrides.get("__default__")
        if o:
            return o.get("cu", base["cu"]), o.get("au", base["au"])
    return base["cu"], base["au"]


def build_recovery_overrides(
    rec_porfido_cu: float, rec_porfido_au: float,
    rec_brecha_cu: float, rec_brecha_au: float,
    rec_skarn_cu: float, rec_skarn_au: float,
    rec_andesita_cu: float, rec_andesita_au: float,
) -> dict:
    return {
        "Pórfido Cuprífero": {"cu": rec_porfido_cu, "au": rec_porfido_au},
        "Brecha Hidrotermal": {"cu": rec_brecha_cu, "au": rec_brecha_au},
        "Skarn Mineralizado": {"cu": rec_skarn_cu, "au": rec_skarn_au},
        "Andesita Huinquintipa": {"cu": rec_andesita_cu, "au": rec_andesita_au},
        "__default__": {"cu": rec_andesita_cu, "au": rec_andesita_au},
    }


class NSREngine:
    """NSR (Net Smelter Return) para un bloque, con desglose por contribución."""

    def __init__(
        self,
        cu_price_usd_lb: float,
        au_price_usd_g: float,
        concentrate_cu_pct: float,
        payability_cu_pct: float,
        payability_au_pct: float,
        tc_usd_t: float,
        rc_usd_lb: float,
        freight_usd_t: float,
        recovery_cu_pct: float,
        recovery_au_pct: float,
    ):
        self.cu_price_usd_lb = cu_price_usd_lb
        self.au_price_usd_g = au_price_usd_g
        self.concentrate_cu = concentrate_cu_pct / 100.0
        self.payability_cu = payability_cu_pct / 100.0
        self.payability_au = payability_au_pct / 100.0
        self.tc = tc_usd_t
        self.rc = rc_usd_lb
        self.freight = freight_usd_t
        self.rec_cu = recovery_cu_pct / 100.0
        self.rec_au = recovery_au_pct / 100.0

    def nsr(self, tonnage: float, cu_pct: float, au_pct: float) -> dict:
        cu_metal_t = tonnage * (cu_pct / 100.0)
        cu_payable_lb = cu_metal_t * self.rec_cu * self.payability_cu * LB_PER_TON
        cu_value = cu_payable_lb * self.cu_price_usd_lb

        au_grams = tonnage * (au_pct / 100.0) * self.rec_au * 1000.0
        au_payable = au_grams * self.payability_au
        au_value = au_payable * self.au_price_usd_g

        concentrate_t = cu_metal_t * self.rec_cu / self.concentrate_cu
        deductions = concentrate_t * (self.tc + self.freight) + cu_payable_lb * self.rc

        return {
            "nsr": cu_value + au_value - deductions,
            "cu_value": cu_value,
            "au_value": au_value,
            "deductions": deductions,
            "cu_payable_lb": cu_payable_lb,
        }

    def nsr_per_ton(self, cu_pct: float, au_pct: float) -> float:
        return self.nsr(1.0, cu_pct, au_pct)["nsr"]

    def breakeven_grade_pct(self, opex_per_ton: float, au_pct: float) -> float:
        """Ley Cu (%) donde NSR/ton == OPEX/ton (crédito de Au reduce el Cu requerido)."""
        k = (self.rec_cu * self.payability_cu * self.cu_price_usd_lb * LB_PER_TON) / 100.0
        conc_per_ton_per_unit = (self.rec_cu / self.concentrate_cu) / 100.0
        c = conc_per_ton_per_unit * (self.tc + self.freight) \
            + (self.rec_cu * self.payability_cu * LB_PER_TON * self.rc) / 100.0
        au_nsr = self.nsr_per_ton(0.0, au_pct)
        if (k - c) <= 0:
            return 0.0
        return max((opex_per_ton - au_nsr) / (k - c), 0.0)


def build_params(
    cu_price_usd_lb: float,
    au_price_usd_oz: float,
    drilling: float,
    blasting: float,
    loading: float,
    hauling_base: float,
    hauling_slope: float,
    processing: float,
    g_and_a: float,
    concentrate_cu_pct: float,
    payability_cu_pct: float,
    payability_au_pct: float,
    tc: float,
    rc: float,
    freight: float,
) -> EconomicParams:
    return EconomicParams(
        cu_price_usd_lb=cu_price_usd_lb,
        au_price_usd_g=au_price_usd_oz / G_PER_TROY_OZ,
        mining_fixed_usd_ton=round(drilling + blasting + loading, 2),
        hauling_base_usd_ton=hauling_base,
        hauling_slope_usd_ton_m=hauling_slope,
        processing_usd_ton=processing,
        g_and_a_usd_ton=g_and_a,
        concentrate_cu_pct=concentrate_cu_pct,
        payability_cu_pct=payability_cu_pct,
        payability_au_pct=payability_au_pct,
        tc_usd_t=tc,
        rc_usd_lb=rc,
        freight_usd_t=freight,
        min_cu_grade=MIN_CU_GRADE,
        recovery_by_lithology=[
            LithologyRecovery(
                lithology=l,
                cu_recovery_pct=DEFAULT_RECOVERY[l]["cu"],
                au_recovery_pct=DEFAULT_RECOVERY[l]["au"],
            )
            for l in DEFAULT_RECOVERY
        ],
    )


def compute_summaries(
    blocks: List[Block],
    crest_z: int,
    params: EconomicParams,
    cu_price_usd_lb: float,
    au_price_usd_g: float,
    drilling: float,
    blasting: float,
    loading: float,
    hauling_base: float,
    hauling_slope: float,
    processing: float,
    g_and_a: float,
    tc: float,
    rc: float,
    freight: float,
    recovery_overrides: Optional[dict] = None,
) -> tuple[List[EconomicBlockSummary], float, float, float, float, float, float]:
    bench_data: dict[int, List[Block]] = {}
    for b in blocks:
        bench_data.setdefault(b.bench, []).append(b)

    summaries: List[EconomicBlockSummary] = []
    total_ton = total_plant = total_waste = 0.0
    total_nsr = total_opex = total_margin = 0.0

    for bnc, blks in sorted(bench_data.items()):
        depth = float(crest_z - bnc)
        min_cost = mining_cost_per_ton(depth, drilling, blasting, loading,
                                       hauling_base, hauling_slope)
        opex_per_ton = min_cost + processing + g_and_a

        ton_plant = ton_waste = 0.0
        nsr_plant = 0.0
        grade_plant_sum = 0.0
        grade_sum = 0.0
        au_sum = 0.0
        cu_fine = 0.0
        au_fine = 0.0
        ton_all = 0.0
        rec_cu_wsum = 0.0
        rec_au_wsum = 0.0
        for blk in blks:
            rec_cu, rec_au = get_recovery(blk.lithology, recovery_overrides)
            engine = NSREngine(cu_price_usd_lb, au_price_usd_g,
                               params.concentrate_cu_pct, params.payability_cu_pct,
                               params.payability_au_pct, tc, rc, freight,
                               rec_cu, rec_au)
            ton = float(blk.tonnage)
            ton_all += ton
            rec_cu_wsum += ton * rec_cu
            rec_au_wsum += ton * rec_au
            grade_sum += ton * blk.cu_bayesian
            au_sum += ton * blk.au_bayesian
            r = engine.nsr(ton, blk.cu_bayesian, blk.au_bayesian)
            cu_fine += ton * (blk.cu_bayesian / 100.0) * (rec_cu / 100.0)
            au_fine += ton * (blk.au_bayesian / 100.0) * (rec_au / 100.0) * 1000.0
            if r["nsr"] >= ton * opex_per_ton:
                ton_plant += ton
                nsr_plant += r["nsr"]
                grade_plant_sum += ton * blk.cu_bayesian

        ton_waste = ton_all - ton_plant
        avg_cu = grade_sum / ton_all if ton_all else 0.0
        avg_au = au_sum / ton_all if ton_all else 0.0
        avg_grade_plant = grade_plant_sum / ton_plant if ton_plant else 0.0
        rec_cu_avg = rec_cu_wsum / ton_all if ton_all else DEFAULT_RECOVERY_FALLBACK["cu"]
        rec_au_avg = rec_au_wsum / ton_all if ton_all else DEFAULT_RECOVERY_FALLBACK["au"]

        engine_avg = NSREngine(cu_price_usd_lb, au_price_usd_g,
                               params.concentrate_cu_pct, params.payability_cu_pct,
                               params.payability_au_pct, tc, rc, freight,
                               rec_cu_avg, rec_au_avg)
        brk = engine_avg.breakeven_grade_pct(opex_per_ton, avg_au)

        nsr_bench = 0.0
        for b in blks:
            rc_, ra_ = get_recovery(b.lithology, recovery_overrides)
            eng_b = NSREngine(cu_price_usd_lb, au_price_usd_g,
                              params.concentrate_cu_pct, params.payability_cu_pct,
                              params.payability_au_pct, tc, rc, freight, rc_, ra_)
            nsr_bench += eng_b.nsr(float(b.tonnage), b.cu_bayesian, b.au_bayesian)["nsr"]
        opex_bench = ton_all * opex_per_ton
        margin = nsr_bench - opex_bench

        summaries.append(EconomicBlockSummary(
            bench=bnc,
            depth_m=round(depth, 1),
            blocks_count=len(blks),
            total_tonnage=round(ton_all, 0),
            tonnage_plant=round(ton_plant, 0),
            tonnage_waste=round(ton_waste, 0),
            avg_cu_grade=round(avg_cu, 3),
            avg_grade_plant=round(avg_grade_plant, 3),
            recovery_cu_pct=round(rec_cu_avg, 1),
            cu_fine_tons=round(cu_fine, 1),
            au_fine_grams=round(au_fine, 0),
            cut_off_grade_pct=round(brk, 3),
            mining_cost_usd_ton=round(min_cost, 2),
            processing_cost_usd_ton=processing,
            g_and_a_usd_ton=g_and_a,
            nsr_value_usd=round(nsr_bench, 0),
            opex_usd=round(opex_bench, 0),
            margin_usd=round(margin, 0),
            margin_per_ton=round(margin / ton_all, 2) if ton_all else 0.0,
        ))

        total_ton += ton_all
        total_plant += ton_plant
        total_waste += ton_waste
        total_nsr += nsr_bench
        total_opex += opex_bench
        total_margin += margin

    return (summaries, total_ton, total_plant, total_waste,
            total_nsr, total_opex, total_margin)


def mining_cost_per_ton(depth_m: float,
                        drilling: float,
                        blasting: float,
                        loading: float,
                        hauling_base: float,
                        hauling_slope: float) -> float:
    return drilling + blasting + loading + hauling_base + hauling_slope * max(depth_m, 0.0)


@router.get("", response_model=EconomicAnalysisResponse)
async def get_economic_analysis(
    project_id: int = Query(...),
    bench: Optional[int] = Query(None),
    cu_price_usd_lb: float = Query(DEFAULT_CU_PRICE_USD_LB),
    au_price_usd_oz: float = Query(DEFAULT_AU_PRICE_USD_OZ),
    drilling_usd_ton: float = Query(DEFAULT_DRILLING_USD_TON),
    blasting_usd_ton: float = Query(DEFAULT_BLASTING_USD_TON),
    loading_usd_ton: float = Query(DEFAULT_LOADING_USD_TON),
    hauling_base_usd_ton: float = Query(DEFAULT_HAULING_BASE_USD_TON),
    hauling_slope_usd_ton_m: float = Query(DEFAULT_HAULING_SLOPE_USD_TON_M),
    processing_cost_usd_ton: float = Query(DEFAULT_PROCESSING_USD_TON),
    g_and_a_usd_ton: float = Query(DEFAULT_G_AND_A_USD_TON),
    concentrate_cu_pct: float = Query(DEFAULT_CONCENTRATE_CU_PCT),
    payability_cu_pct: float = Query(DEFAULT_PAYABILITY_CU_PCT),
    payability_au_pct: float = Query(DEFAULT_PAYABILITY_AU_PCT),
    tc_usd_t: float = Query(DEFAULT_TC_USD_T),
    rc_usd_lb: float = Query(DEFAULT_RC_USD_LB),
    freight_usd_t: float = Query(DEFAULT_FREIGHT_USD_T),
    rec_porfido_cu: float = Query(DEFAULT_RECOVERY["Pórfido Cuprífero"]["cu"]),
    rec_porfido_au: float = Query(DEFAULT_RECOVERY["Pórfido Cuprífero"]["au"]),
    rec_brecha_cu: float = Query(DEFAULT_RECOVERY["Brecha Hidrotermal"]["cu"]),
    rec_brecha_au: float = Query(DEFAULT_RECOVERY["Brecha Hidrotermal"]["au"]),
    rec_skarn_cu: float = Query(DEFAULT_RECOVERY["Skarn Mineralizado"]["cu"]),
    rec_skarn_au: float = Query(DEFAULT_RECOVERY["Skarn Mineralizado"]["au"]),
    rec_andesita_cu: float = Query(DEFAULT_RECOVERY["Andesita Huinquintipa"]["cu"]),
    rec_andesita_au: float = Query(DEFAULT_RECOVERY["Andesita Huinquintipa"]["au"]),
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
        raise HTTPException(status_code=404, detail="No hay bloques para los criterios seleccionados")

    crest_z = max(b.bench for b in blocks)
    params = build_params(
        cu_price_usd_lb, au_price_usd_oz, drilling_usd_ton, blasting_usd_ton,
        loading_usd_ton, hauling_base_usd_ton, hauling_slope_usd_ton_m,
        processing_cost_usd_ton, g_and_a_usd_ton, concentrate_cu_pct,
        payability_cu_pct, payability_au_pct, tc_usd_t, rc_usd_lb, freight_usd_t,
    )
    au_price_usd_g = au_price_usd_oz / G_PER_TROY_OZ
    overrides = build_recovery_overrides(
        rec_porfido_cu, rec_porfido_au, rec_brecha_cu, rec_brecha_au,
        rec_skarn_cu, rec_skarn_au, rec_andesita_cu, rec_andesita_au)

    (summaries, total_ton, total_plant, total_waste,
     total_nsr, total_opex, total_margin) = compute_summaries(
        blocks, crest_z, params, cu_price_usd_lb, au_price_usd_g,
        drilling_usd_ton, blasting_usd_ton, loading_usd_ton,
        hauling_base_usd_ton, hauling_slope_usd_ton_m,
        processing_cost_usd_ton, g_and_a_usd_ton, tc_usd_t, rc_usd_lb, freight_usd_t,
        overrides,
    )

    return EconomicAnalysisResponse(
        project_name=project.name,
        active_bench=bench,
        params=params,
        summaries=summaries,
        total_tonnage=round(total_ton, 0),
        total_tonnage_plant=round(total_plant, 0),
        total_tonnage_waste=round(total_waste, 0),
        total_nsr_usd=round(total_nsr, 0),
        total_opex_usd=round(total_opex, 0),
        total_margin_usd=round(total_margin, 0),
        is_profitable=total_margin > 0,
    )


@router.get("/cutoffs", response_model=EconomicCutoffsResponse)
async def get_economic_cutoffs(
    project_id: int = Query(...),
    cu_price_usd_lb: float = Query(DEFAULT_CU_PRICE_USD_LB),
    au_price_usd_oz: float = Query(DEFAULT_AU_PRICE_USD_OZ),
    drilling_usd_ton: float = Query(DEFAULT_DRILLING_USD_TON),
    blasting_usd_ton: float = Query(DEFAULT_BLASTING_USD_TON),
    loading_usd_ton: float = Query(DEFAULT_LOADING_USD_TON),
    hauling_base_usd_ton: float = Query(DEFAULT_HAULING_BASE_USD_TON),
    hauling_slope_usd_ton_m: float = Query(DEFAULT_HAULING_SLOPE_USD_TON_M),
    processing_cost_usd_ton: float = Query(DEFAULT_PROCESSING_USD_TON),
    g_and_a_usd_ton: float = Query(DEFAULT_G_AND_A_USD_TON),
    concentrate_cu_pct: float = Query(DEFAULT_CONCENTRATE_CU_PCT),
    payability_cu_pct: float = Query(DEFAULT_PAYABILITY_CU_PCT),
    payability_au_pct: float = Query(DEFAULT_PAYABILITY_AU_PCT),
    tc_usd_t: float = Query(DEFAULT_TC_USD_T),
    rc_usd_lb: float = Query(DEFAULT_RC_USD_LB),
    freight_usd_t: float = Query(DEFAULT_FREIGHT_USD_T),
    rec_porfido_cu: float = Query(DEFAULT_RECOVERY["Pórfido Cuprífero"]["cu"]),
    rec_porfido_au: float = Query(DEFAULT_RECOVERY["Pórfido Cuprífero"]["au"]),
    rec_brecha_cu: float = Query(DEFAULT_RECOVERY["Brecha Hidrotermal"]["cu"]),
    rec_brecha_au: float = Query(DEFAULT_RECOVERY["Brecha Hidrotermal"]["au"]),
    rec_skarn_cu: float = Query(DEFAULT_RECOVERY["Skarn Mineralizado"]["cu"]),
    rec_skarn_au: float = Query(DEFAULT_RECOVERY["Skarn Mineralizado"]["au"]),
    rec_andesita_cu: float = Query(DEFAULT_RECOVERY["Andesita Huinquintipa"]["cu"]),
    rec_andesita_au: float = Query(DEFAULT_RECOVERY["Andesita Huinquintipa"]["au"]),
    db: AsyncSession = Depends(get_db),
):
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    query = select(Block).where(Block.project_id == project_id)
    result = await db.execute(query)
    blocks = result.scalars().all()
    if not blocks:
        raise HTTPException(status_code=404, detail="No hay bloques para el proyecto")

    crest_z = max(b.bench for b in blocks)
    params = build_params(
        cu_price_usd_lb, au_price_usd_oz, drilling_usd_ton, blasting_usd_ton,
        loading_usd_ton, hauling_base_usd_ton, hauling_slope_usd_ton_m,
        processing_cost_usd_ton, g_and_a_usd_ton, concentrate_cu_pct,
        payability_cu_pct, payability_au_pct, tc_usd_t, rc_usd_lb, freight_usd_t,
    )
    au_price_usd_g = au_price_usd_oz / G_PER_TROY_OZ
    overrides = build_recovery_overrides(
        rec_porfido_cu, rec_porfido_au, rec_brecha_cu, rec_brecha_au,
        rec_skarn_cu, rec_skarn_au, rec_andesita_cu, rec_andesita_au)

    bench_data: dict[int, List[Block]] = {}
    for b in blocks:
        bench_data.setdefault(b.bench, []).append(b)

    benches: List[EconomicCutoff] = []
    for bnc, blks in sorted(bench_data.items()):
        depth = float(crest_z - bnc)
        min_cost = mining_cost_per_ton(depth, drilling_usd_ton, blasting_usd_ton,
                                       loading_usd_ton, hauling_base_usd_ton,
                                       hauling_slope_usd_ton_m)
        opex_per_ton = min_cost + processing_cost_usd_ton + g_and_a_usd_ton
        avg_cu = sum(b.cu_bayesian for b in blks) / len(blks)
        avg_au = sum(b.au_bayesian for b in blks) / len(blks)
        rec_cu, rec_au = get_recovery(blks[0].lithology, overrides)
        engine = NSREngine(cu_price_usd_lb, au_price_usd_g, concentrate_cu_pct,
                           payability_cu_pct, payability_au_pct, tc_usd_t,
                           rc_usd_lb, freight_usd_t, rec_cu, rec_au)
        brk = engine.breakeven_grade_pct(opex_per_ton, avg_au)
        nsr_avg = sum(engine.nsr(float(b.tonnage), b.cu_bayesian, b.au_bayesian)["nsr"]
                      for b in blks) / sum(b.tonnage for b in blks)
        benches.append(EconomicCutoff(
            bench=bnc,
            depth_m=round(depth, 1),
            cut_off_grade_pct=round(brk, 3),
            mining_cost_usd_ton=round(min_cost, 2),
            processing_cost_usd_ton=processing_cost_usd_ton,
            g_and_a_usd_ton=g_and_a_usd_ton,
            recovery_cu_pct=rec_cu,
            recovery_au_pct=rec_au,
            avg_cu=round(avg_cu, 3),
            avg_au=round(avg_au, 4),
            nsr_avg_usd_ton=round(nsr_avg, 2),
        ))

    return EconomicCutoffsResponse(
        project_name=project.name,
        params=params,
        benches=benches,
    )