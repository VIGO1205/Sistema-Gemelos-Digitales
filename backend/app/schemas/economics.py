from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class LithologyRecovery(BaseModel):
    lithology: str = Field(..., description="Litología")
    cu_recovery_pct: float = Field(..., description="Recuperación de Cu (%)")
    au_recovery_pct: float = Field(..., description="Recuperación de Au (%)")


class EconomicBlockSummary(BaseModel):
    bench: int = Field(..., description="Banco (msnm)")
    depth_m: float = Field(..., description="Profundidad desde la cresta (m)")
    blocks_count: int = Field(..., description="Cantidad de bloques")
    total_tonnage: float = Field(..., description="Tonelaje total")
    tonnage_plant: float = Field(..., description="Tonelaje a planta")
    tonnage_waste: float = Field(..., description="Tonelaje a estéril")
    avg_cu_grade: float = Field(..., description="Ley promedio Cu (% bayesiana)")
    avg_grade_plant: float = Field(..., description="Ley promedio Cu planta (%)")
    recovery_cu_pct: float = Field(..., description="Recuperación Cu efectiva (%)")
    cu_fine_tons: float = Field(..., description="Ton Cu fino recuperable")
    au_fine_grams: float = Field(..., description="Gramos Au fino recuperable")
    cut_off_grade_pct: float = Field(..., description="Ley de corte de equilibrio (%)")
    mining_cost_usd_ton: float = Field(..., description="Costo minado USD/ton")
    processing_cost_usd_ton: float = Field(..., description="Costo proceso USD/ton")
    g_and_a_usd_ton: float = Field(..., description="Costo G&A USD/ton procesado")
    nsr_value_usd: float = Field(..., description="Valor NSR (puerta fundición) USD")
    opex_usd: float = Field(..., description="OPEX total USD")
    margin_usd: float = Field(..., description="Margen NSR − OPEX (USD)")
    margin_per_ton: float = Field(..., description="Margen por tonelada (USD)")


class EconomicCutoff(BaseModel):
    bench: int = Field(..., description="Banco (msnm)")
    depth_m: float = Field(..., description="Profundidad (m)")
    cut_off_grade_pct: float = Field(..., description="Ley de corte efectiva (%)")
    mining_cost_usd_ton: float = Field(..., description="Costo minado USD/ton")
    processing_cost_usd_ton: float = Field(..., description="Costo proceso USD/ton")
    g_and_a_usd_ton: float = Field(..., description="Costo G&A USD/ton")
    recovery_cu_pct: float = Field(..., description="Recuperación Cu (%)")
    recovery_au_pct: float = Field(..., description="Recuperación Au (%)")
    avg_cu: float = Field(..., description="Ley Cu promedio del banco (%)")
    avg_au: float = Field(..., description="Ley Au promedio del banco (%)")
    nsr_avg_usd_ton: float = Field(..., description="NSR promedio USD/ton")


class EconomicParams(BaseModel):
    cu_price_usd_lb: float = Field(..., description="Precio Cu USD/lb")
    au_price_usd_g: float = Field(..., description="Precio Au USD/g")
    mining_fixed_usd_ton: float = Field(...,
                                        description="Costos mineros fijos USD/ton"
                                        )
    hauling_base_usd_ton: float = Field(..., description="Acarreo base USD/ton")
    hauling_slope_usd_ton_m: float = Field(...,
                                           description="Acarreo por metro de profundidad USD/ton/m"
                                           )
    processing_usd_ton: float = Field(..., description="Procesamiento USD/ton")
    g_and_a_usd_ton: float = Field(..., description="G&A USD/ton")
    concentrate_cu_pct: float = Field(..., description="Ley del concentrado (%)")
    payability_cu_pct: float = Field(..., description="Payabilidad Cu (%)")
    payability_au_pct: float = Field(..., description="Payabilidad Au (%)")
    tc_usd_t: float = Field(..., description="Cargo fundición (TC) USD/t concentrado")
    rc_usd_lb: float = Field(..., description="Cargo refino (RC) USD/lb Cu")
    freight_usd_t: float = Field(..., description="Transporte + puerto USD/t concentrado"
                                 )
    min_cu_grade: float = Field(..., description="Ley Cu mínima modelada (%)")
    recovery_by_lithology: List[LithologyRecovery] = Field(...,
                                                        description="Recuperación por litología"
                                                        )


class EconomicAnalysisResponse(BaseModel):
    project_name: str = Field(..., description="Nombre del proyecto")
    active_bench: Optional[int] = Field(None, description="Banco activo")
    params: EconomicParams = Field(..., description="Parámetros utilizados")
    summaries: List[EconomicBlockSummary] = Field(...,
                                                  description="Resumen por banco"
                                                  )
    total_tonnage: float = Field(..., description="Tonelaje total")
    total_tonnage_plant: float = Field(..., description="Tonelaje total a planta")
    total_tonnage_waste: float = Field(..., description="Tonelaje total a estéril")
    total_nsr_usd: float = Field(..., description="Valor NSR total USD")
    total_opex_usd: float = Field(..., description="OPEX total USD")
    total_margin_usd: float = Field(..., description="Margen total USD")
    is_profitable: bool = Field(..., description="¿Es rentable en agregado?")


class EconomicCutoffsResponse(BaseModel):
    project_name: str = Field(..., description="Nombre del proyecto")
    params: EconomicParams = Field(..., description="Parámetros utilizados")
    benches: List[EconomicCutoff] = Field(..., description="Corte por banco")