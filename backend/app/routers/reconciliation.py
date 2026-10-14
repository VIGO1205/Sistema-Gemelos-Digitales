import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db, engine
from app.models import ProcessControlPoint
from app.schemas.reconciliation import (
    ReconciliationResponse,
    ReconciliationPoint,
    ModelMetrics,
    DriftAlert,
)

router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliación Mine-to-Mill"])


class PredictionPayload(BaseModel):
    bench: int
    model_name: str
    predictions: List[float]


async def get_active_model_for_bench(bench: int) -> dict:
    """Consulta el modelo activo desde PostgreSQL"""
    try:
        async with engine.connect() as conn:
            query = text("""
                SELECT model_name, composite_score, rmse, r2
                FROM active_models
                WHERE bench = :bench AND is_current = TRUE
            """)
            result = await conn.execute(query, {"bench": bench})
            row = result.fetchone()
            
            if row:
                return {
                    "name": row.model_name,
                    "composite_score": row.composite_score,
                    "rmse": row.rmse,
                    "r2": row.r2,
                    "is_active": True,
                }
    except Exception:
        pass
    
    # Default si no hay modelo activo
    return {
        "name": "Gemelo Digital M-6 (Bayesiano)",
        "composite_score": None,
        "rmse": None,
        "r2": None,
        "is_active": False,
    }


def _compute_metrics(actual: List[float], predicted: List[float], name: str) -> ModelMetrics:
    n = len(actual)
    if n == 0:
        return ModelMetrics(
            model_name=name, mae=0.0, rmse=0.0, bias=0.0,
            r2=None, count=0, mean_absolute_pct_error=0.0
        )
    
    residuals = [a - p for a, p in zip(actual, predicted)]
    mae = sum(abs(r) for r in residuals) / n
    rmse = math.sqrt(sum(r ** 2 for r in residuals) / n)
    bias = sum(residuals) / n

    # R² — manejar casos edge
    mean_actual = sum(actual) / n
    ss_total = sum((a - mean_actual) ** 2 for a in actual)
    ss_res = sum(r ** 2 for r in residuals)
    if ss_total > 1e-12:
        r2 = 1 - (ss_res / ss_total)
    else:
        r2 = None  # Todos los valores iguales

    # MAPE — manejar división por cero
    mape_values = [abs(r / a) * 100 for r, a in zip(residuals, actual) if abs(a) > 1e-12]
    mape = sum(mape_values) / len(mape_values) if mape_values else 0.0

    return ModelMetrics(
        model_name=name,
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        bias=round(bias, 4),
        r2=round(r2, 4) if r2 is not None else None,
        count=n,
        mean_absolute_pct_error=round(mape, 2),
    )


def _detect_drift(krig: ModelMetrics, active: ModelMetrics, active_name: str) -> List[DriftAlert]:
    alerts = []

    # Alerta de bias Kriging
    if abs(krig.bias) > 0.15:
        alerts.append(DriftAlert(
            severity="CRITICAL" if abs(krig.bias) > 0.25 else "WARNING",
            message=f"El modelo Kriging presenta un bias significativo de {krig.bias:.3f}% Cu. Se recomienda revisar la estimación base.",
            metric="bias_kriging",
            current_value=krig.bias,
            threshold=0.15,
        ))

    # Alerta de bias del modelo activo
    if abs(active.bias) > 0.10:
        alerts.append(DriftAlert(
            severity="CRITICAL" if abs(active.bias) > 0.18 else "WARNING",
            message=f"El modelo {active_name} presenta un bias de {active.bias:.3f}% Cu. Revisar calibración.",
            metric="bias_active_model",
            current_value=active.bias,
            threshold=0.10,
        ))

    # Alerta de RMSE alto
    if active.rmse > 0.20:
        alerts.append(DriftAlert(
            severity="WARNING",
            message=f"El RMSE de {active_name} ({active.rmse:.3f}) supera el umbral aceptable de 0.20% Cu.",
            metric="rmse_active_model",
            current_value=active.rmse,
            threshold=0.20,
        ))

    # Alerta si Kriging es mejor que el modelo activo
    if krig.rmse < active.rmse:
        alerts.append(DriftAlert(
            severity="INFO",
            message=f"El Kriging base tiene menor RMSE ({krig.rmse:.3f}) que {active_name} ({active.rmse:.3f}). Considerar recalibración.",
            metric="model_comparison",
            current_value=active.rmse - krig.rmse,
            threshold=0.0,
        ))

    return alerts


@router.post("/predictions")
async def upload_predictions(payload: PredictionPayload):
    """
    Recibe predicciones del modelo ganador desde el Motor IA Streamlit
    y las guarda en process_control_points.predicted_active_model.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not payload.predictions or any(not math.isfinite(value) or value < 0 for value in payload.predictions):
        raise HTTPException(status_code=422, detail="Las predicciones deben ser finitas y no negativas")

    try:
        logger.info(f"[upload_predictions] Received: bench={payload.bench}, model={payload.model_name}, n_preds={len(payload.predictions)}")
        logger.info(f"[upload_predictions] Pred stats: min={min(payload.predictions):.4f}, mean={sum(payload.predictions)/len(payload.predictions):.4f}, max={max(payload.predictions):.4f}")
        logger.info(f"[upload_predictions] First 5 preds: {payload.predictions[:5]}")
        
        async with engine.begin() as conn:
            # Obtener registros del banco ordenados cronológicamente
            query = text("""
                SELECT id, timestamp, plant_feed_grade FROM process_control_points
                WHERE bench = :bench
                ORDER BY timestamp
            """)
            result = await conn.execute(query, {"bench": payload.bench})
            rows = result.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail=f"No hay registros para el banco {payload.bench}")
            if len(payload.predictions) != len(rows):
                raise HTTPException(status_code=422, detail="El número de predicciones no coincide con los puntos del banco")

            current = await conn.execute(text("""
                SELECT model_name FROM active_models
                WHERE bench = :bench AND is_current = TRUE
            """), {"bench": payload.bench})
            current_model = current.scalar_one_or_none()
            if current_model != payload.model_name:
                raise HTTPException(status_code=409, detail="El modelo enviado no coincide con el modelo activo del banco")
            
            logger.info(f"[upload_predictions] Found {len(rows)} DB records for bench={payload.bench}")
            logger.info(f"[upload_predictions] First DB record: id={rows[0].id}, ts={rows[0].timestamp}, grade={rows[0].plant_feed_grade}")
            
            # Limpiar predicciones anteriores para evitar datos stale
            await conn.execute(
                text("""
                    UPDATE process_control_points
                    SET predicted_active_model = NULL,
                        residual_active = NULL
                    WHERE bench = :bench
                """),
                {"bench": payload.bench}
            )
            logger.info(f"[upload_predictions] Cleared old predictions for bench={payload.bench}")
            
            # Actualizar cada registro con la predicción correspondiente
            predictions = payload.predictions
            updated_count = 0
            for i, row in enumerate(rows):
                pred_value = predictions[i]
                if pred_value is not None:
                    await conn.execute(
                        text("""
                            UPDATE process_control_points
                            SET predicted_active_model = :pred,
                                residual_active = plant_feed_grade - :pred
                            WHERE id = :id
                        """),
                        {"pred": pred_value, "id": row.id}
                    )
                    updated_count += 1
            
            logger.info(f"[upload_predictions] Updated {updated_count} records")
        
        return {
            "success": True,
            "message": f"Predicciones de '{payload.model_name}' guardadas para banco {payload.bench}",
            "records_updated": updated_count,
            "bench": payload.bench,
            "model_name": payload.model_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[upload_predictions] ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Error guardando predicciones: {str(e)}")


@router.get("", response_model=ReconciliationResponse)
async def get_reconciliation(
    project_id: int = Query(...),
    bench: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(ProcessControlPoint).where(ProcessControlPoint.project_id == project_id)
    if bench is not None:
        query = query.where(ProcessControlPoint.bench == bench)
    query = query.order_by(ProcessControlPoint.timestamp)

    result = await db.execute(query)
    points = result.scalars().all()

    if not points:
        raise HTTPException(status_code=404, detail="No hay datos de control de procesos para los criterios seleccionados")

    # Obtener modelo activo PRIMERO para usar su nombre real
    active_model_info = await get_active_model_for_bench(bench)
    active_model_name = active_model_info.get("name") or "Gemelo Digital M-6 (Bayesiano)"

    actual = [p.plant_feed_grade for p in points]
    krig_pred = [p.predicted_base_krig for p in points]
    
    # Una comparación del modelo activo exige predicciones para todos los puntos.
    has_active_predictions = active_model_info["is_active"] and all(
        p.predicted_active_model is not None for p in points
    )
    if has_active_predictions:
        active_pred = [p.predicted_active_model for p in points]
    else:
        active_pred = [p.predicted_bayesian for p in points]
        active_model_name = "Estimación M-6 simulada (sin predicciones activas completas)"

    krig_metrics = _compute_metrics(actual, krig_pred, "Ordinary Kriging")
    active_metrics = _compute_metrics(actual, active_pred, active_model_name)

    improvement_pct = ((krig_metrics.rmse - active_metrics.rmse) / krig_metrics.rmse * 100) if krig_metrics.rmse > 0 else 0.0
    winner = active_model_name if active_metrics.rmse < krig_metrics.rmse else "Ordinary Kriging"

    drift_alerts = _detect_drift(krig_metrics, active_metrics, active_model_name)

    point_list = [
        ReconciliationPoint(
            point_id=p.point_id,
            blast_id=p.blast_id,
            timestamp=p.timestamp.isoformat(),
            bench=p.bench,
            tonnage=p.tonnage,
            plant_feed_grade=p.plant_feed_grade,
            predicted_base_krig=p.predicted_base_krig,
            predicted_bayesian=p.predicted_bayesian,
            predicted_active_model=p.predicted_active_model,
            residual_base=p.residual_base,
            residual_bayesian=p.residual_bayesian,
            residual_active=p.residual_active,
        )
        for p in points
    ]

    from app.schemas.reconciliation import ActiveModelInfo

    return ReconciliationResponse(
        bench=bench,
        points=point_list,
        kriging_metrics=krig_metrics,
        bayesian_metrics=active_metrics,
        drift_alerts=drift_alerts,
        winner_model=winner,
        improvement_pct=round(improvement_pct, 2),
        active_model=ActiveModelInfo(
            model_name=active_model_info["name"],
            composite_score=active_model_info.get("composite_score"),
            rmse=active_model_info.get("rmse"),
            r2=active_model_info.get("r2"),
        ),
    )
