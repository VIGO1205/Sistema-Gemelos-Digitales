"""
Router para Modelos Activos y Benchmark
Obtiene el mejor modelo seleccionado por el Motor IA
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.database import engine

router = APIRouter(prefix="/api/models", tags=["Modelos Activos"])


class ActivateModelRequest(BaseModel):
    bench: int
    model_name: str
    composite_score: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    mae: Optional[float] = None
    mape: Optional[float] = None
    bias: Optional[float] = None


@router.get("/active")
async def get_active_model(bench: Optional[int] = None):
    """
    Obtiene el modelo activo (ganador) para un banco especifico
    o para todos los bancos si no se especifica.
    """
    try:
        async with engine.connect() as conn:
            if bench is not None:
                query = text("""
                    SELECT bench, model_name, composite_score, rmse, r2, mae, mape, bias, activated_at
                    FROM active_models
                    WHERE bench = :bench AND is_current = TRUE
                """)
                result = await conn.execute(query, {"bench": bench})
                row = result.fetchone()
                
                if not row:
                    return {
                        "bench": bench,
                        "model_name": "Gemelo Digital M-6 (Bayesiano)",
                        "composite_score": None,
                        "rmse": None,
                        "r2": None,
                        "mae": None,
                        "mape": None,
                        "bias": None,
                        "activated_at": None,
                        "note": "No hay modelo activo registrado. Usando default."
                    }
                
                return {
                    "bench": row.bench,
                    "model_name": row.model_name,
                    "composite_score": row.composite_score,
                    "rmse": row.rmse,
                    "r2": row.r2,
                    "mae": row.mae,
                    "mape": row.mape,
                    "bias": row.bias,
                    "activated_at": row.activated_at.isoformat() if row.activated_at else None
                }
            else:
                query = text("""
                    SELECT bench, model_name, composite_score, rmse, r2, mae, mape, bias, activated_at
                    FROM active_models
                    WHERE is_current = TRUE
                    ORDER BY bench DESC
                """)
                result = await conn.execute(query)
                rows = result.fetchall()
                
                return {
                    "active_models": [
                        {
                            "bench": r.bench,
                            "model_name": r.model_name,
                            "composite_score": r.composite_score,
                            "rmse": r.rmse,
                            "r2": r.r2,
                            "mae": r.mae,
                            "mape": r.mape,
                            "bias": r.bias,
                            "activated_at": r.activated_at.isoformat() if r.activated_at else None
                        }
                        for r in rows
                    ]
                }
    except Exception as e:
        # Si la tabla no existe, devolver default
        return {
            "bench": bench,
            "model_name": "Gemelo Digital M-6 (Bayesiano)",
            "composite_score": None,
            "note": f"Tabla no disponible: {str(e)}. Usando default."
        }


@router.post("/activate")
async def activate_model_endpoint(payload: ActivateModelRequest):
    """
    Activa (guarda/actualiza) el modelo ganador para un banco.
    Usado por el Motor IA Streamlit para persistir el modelo seleccionado.
    También genera una notificación en la bandeja de alertas del sistema.
    """
    try:
        async with engine.begin() as conn:
            project_id = await conn.scalar(
                text("SELECT id FROM projects WHERE project_id = :project_key"),
                {"project_key": "proj-m6-esperanza"},
            )
            # Desactivar modelo anterior del mismo banco
            await conn.execute(
                text("""
                    UPDATE active_models 
                    SET is_current = FALSE, deactivated_at = NOW()
                    WHERE bench = :bench AND is_current = TRUE
                """),
                {"bench": payload.bench}
            )
            # Insertar o actualizar modelo activo
            await conn.execute(
                text("""
                    INSERT INTO active_models 
                    (bench, model_name, composite_score, rmse, r2, mae, mape, bias, is_current, activated_at)
                    VALUES (:bench, :model_name, :composite_score, :rmse, :r2, :mae, :mape, :bias, TRUE, NOW())
                    ON CONFLICT (bench) DO UPDATE 
                    SET model_name = EXCLUDED.model_name,
                        composite_score = EXCLUDED.composite_score,
                        rmse = EXCLUDED.rmse,
                        r2 = EXCLUDED.r2,
                        mae = EXCLUDED.mae,
                        mape = EXCLUDED.mape,
                        bias = EXCLUDED.bias,
                        activated_at = NOW(),
                        deactivated_at = NULL,
                        is_current = TRUE
                """),
                {
                    "bench": payload.bench,
                    "model_name": payload.model_name,
                    "composite_score": payload.composite_score,
                    "rmse": payload.rmse,
                    "r2": payload.r2,
                    "mae": payload.mae,
                    "mape": payload.mape,
                    "bias": payload.bias,
                }
            )
            
            # Crear notificación en bandeja de alertas
            alert_id = f"MODEL-{payload.bench}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            score_str = f"{payload.composite_score:.4f}" if payload.composite_score is not None else "N/A"
            rmse_str = f"{payload.rmse:.4f}" if payload.rmse is not None else "N/A"
            r2_str = f"{payload.r2:.4f}" if payload.r2 is not None else "N/A"
            
            if project_id is not None:
                await conn.execute(
                    text("""
                        INSERT INTO alerts
                        (alert_id, project_id, alert_type, severity, bench, block_id, title, description,
                         current_val, threshold_val, timestamp, acknowledged, assigned_role, action_recommended)
                        VALUES (:alert_id, :project_id, :alert_type, :severity, :bench, :block_id, :title, :description,
                         :current_val, :threshold_val, NOW(), FALSE, :assigned_role, :action_recommended)
                    """),
                    {
                        "alert_id": alert_id,
                        "project_id": project_id,
                        "alert_type": "MODEL_ACTIVATED",
                        "severity": "INFO",
                        "bench": payload.bench,
                        "block_id": "SYSTEM",
                        "title": f"Modelo {payload.model_name} registrado en Banco {payload.bench}m",
                        "description": (
                            f"Se registró '{payload.model_name}' para el banco de ejemplo {payload.bench}m. "
                            f"Métricas del experimento: Score={score_str}, RMSE={rmse_str}% Cu, R²={r2_str}. "
                            "La publicación de predicciones y su validación son pasos separados."
                        ),
                        "current_val": score_str,
                        "threshold_val": "N/A",
                        "assigned_role": "ADMIN",
                        "action_recommended": "Comprobar el conjunto de entrenamiento, la publicación del modelo y la procedencia de los puntos de control antes de interpretar la reconciliación.",
                    },
                )
        
        return {
            "success": True,
            "message": f"Modelo '{payload.model_name}' activado para banco {payload.bench}",
            "bench": payload.bench,
            "model_name": payload.model_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error activando modelo: {str(e)}")


@router.get("/benchmark")
async def get_benchmark(bench: int):
    """
    Obtiene todos los resultados de benchmark para un banco
    """
    try:
        async with engine.connect() as conn:
            query = text("""
                SELECT model_name, model_type, rmse, mae, r2, mape, bias, 
                       composite_score, is_winner, trained_at
                FROM benchmark_models
                WHERE bench = :bench
                ORDER BY composite_score DESC
            """)
            result = await conn.execute(query, {"bench": bench})
            rows = result.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail=f"No hay benchmark para banco {bench}")
            
            return {
                "bench": bench,
                "models": [
                    {
                        "model_name": r.model_name,
                        "model_type": r.model_type,
                        "rmse": r.rmse,
                        "mae": r.mae,
                        "r2": r.r2,
                        "mape": r.mape,
                        "bias": r.bias,
                        "composite_score": r.composite_score,
                        "is_winner": r.is_winner,
                        "trained_at": r.trained_at.isoformat() if r.trained_at else None
                    }
                    for r in rows
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando benchmark: {str(e)}")
