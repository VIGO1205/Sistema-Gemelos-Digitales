from typing import List, Optional
from pydantic import BaseModel, Field


class DrillTargetRequest(BaseModel):
    project_id: int = Field(..., gt=0)
    block_id: str = Field(..., min_length=1, description="Bloque destino (ubicación del collar)")
    depth_m: Optional[int] = Field(None, gt=0, le=2000, description="Longitud propuesta en metros")
    hole_type: Optional[str] = Field(None, description="Tipo de sondaje (si se omite se sugiere por profundidad)")
    azimuth: Optional[float] = Field(None, ge=0, lt=360, description="Azimut °")
    dip: Optional[float] = Field(-75.0, ge=-90, le=0, description="Inclinación °")


class DrillTargetResult(BaseModel):
    message: str
    hole_id: str
    block_id: str
    bench: int
    depth_m: int
    hole_type: str
    affected_blocks: int
    upgraded_blocks: int
    avg_epistemic_unc_before: float
    avg_epistemic_unc_after: float


class DrillholeRecommendation(BaseModel):
    rank: int = Field(..., description="Ranking de prioridad (1 = más prioritario)")
    block_id: str = Field(..., description="ID del bloque recomendado")
    bench: int = Field(..., description="Banco Z")
    easting_x: float = Field(..., description="Coordenada Este UTM")
    northing_y: float = Field(..., description="Coordenada Norte UTM")
    elevation_z: float = Field(..., description="Elevación Z")
    cu_bayesian: float = Field(..., description="Ley Cu predicha (%)")
    epistemic_unc: float = Field(..., description="Incertidumbre epistémica σ")
    nearest_drillhole_m: float = Field(..., description="Distancia al sondaje más cercano (m)")
    current_category: str = Field(..., description="Categoría JORC actual")
    target_category: str = Field(..., description="Categoría JORC objetivo tras sondaje")
    suggested_depth_m: int = Field(..., description="Profundidad sugerida del sondaje (m)")
    suggested_type: str = Field(..., description="Tipo de sondaje sugerido")
    priority_score: float = Field(..., description="Puntuación de prioridad (0-100)")
    justification: str = Field(..., description="Justificación textual de la recomendación")


class DrillholePlanningResponse(BaseModel):
    project_name: str = Field(..., description="Nombre del proyecto")
    total_blocks_analyzed: int = Field(..., description="Total de bloques analizados")
    recommendations: List[DrillholeRecommendation] = Field(..., description="Top recomendaciones ordenadas por prioridad")
    summary: dict = Field(..., description="Resumen estadístico")
