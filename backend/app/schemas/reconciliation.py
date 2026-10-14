from typing import List, Optional
from pydantic import BaseModel, Field


class ReconciliationPoint(BaseModel):
    point_id: str = Field(..., description="ID del punto de control")
    blast_id: str = Field(..., description="ID de la voladura")
    timestamp: str = Field(..., description="Fecha de la voladura")
    bench: int = Field(..., description="Banco")
    tonnage: float = Field(..., description="Tonelaje")
    plant_feed_grade: float = Field(..., description="Ley real de alimentación a planta")
    predicted_base_krig: float = Field(..., description="Predicción Kriging base")
    predicted_bayesian: float = Field(..., description="Predicción Bayesiana M-6")
    predicted_active_model: Optional[float] = Field(None, description="Predicción del modelo activo seleccionado")
    residual_base: float = Field(..., description="Residual Kriging")
    residual_bayesian: float = Field(..., description="Residual Bayesiano")
    residual_active: Optional[float] = Field(None, description="Residual del modelo activo")


class ModelMetrics(BaseModel):
    model_name: str = Field(..., description="Nombre del modelo")
    mae: float = Field(..., description="Mean Absolute Error")
    rmse: float = Field(..., description="Root Mean Square Error")
    bias: float = Field(..., description="Bias sistemático (promedio de residuales)")
    r2: Optional[float] = Field(None, description="Coeficiente de determinación R²")
    count: int = Field(..., description="Número de puntos evaluados")
    mean_absolute_pct_error: float = Field(..., description="MAPE (%)")


class DriftAlert(BaseModel):
    severity: str = Field(..., description="CRITICAL, WARNING o INFO")
    message: str = Field(..., description="Descripción del drift detectado")
    metric: str = Field(..., description="Métrica afectada (bias, rmse, etc.)")
    current_value: float = Field(..., description="Valor actual")
    threshold: float = Field(..., description="Umbral de alerta")


class ActiveModelInfo(BaseModel):
    model_name: str = Field(..., description="Nombre del modelo activo")
    composite_score: Optional[float] = Field(None, description="Score compuesto")
    rmse: Optional[float] = Field(None, description="RMSE del modelo activo")
    r2: Optional[float] = Field(None, description="R² del modelo activo")


class ReconciliationResponse(BaseModel):
    bench: Optional[int] = Field(None, description="Banco evaluado (null = todos)")
    points: List[ReconciliationPoint] = Field(..., description="Puntos de control individuales")
    kriging_metrics: ModelMetrics = Field(..., description="Métricas del modelo Kriging")
    bayesian_metrics: ModelMetrics = Field(..., description="Métricas del modelo Bayesiano M-6")
    drift_alerts: List[DriftAlert] = Field(default_factory=list, description="Alertas de drift detectadas")
    winner_model: str = Field(..., description="Modelo con menor RMSE")
    improvement_pct: float = Field(..., description="Mejora porcentual del Bayesiano sobre Kriging")
    active_model: ActiveModelInfo = Field(..., description="Modelo activo seleccionado por el Motor IA")
