"""
Servicio FastAPI de Inferencia del Motor IA M-6 (host).

Expone el modelo ganador entrenado como API de predicción en vivo:

  - Carga el artefacto joblib exportado en la Fase 6 (model_registry).
  - Reconstruye las features reales de planta con la MISMA lógica
    de entrenamiento (fetch_real_plant_data) para evitar drift.
  - Ejecuta predict / predict_with_uncertainty del modelo ganador.
  - Opcionalmente persiste las predicciones en la plataforma
    (elección del mismo flujo que usaba la activación).

Ejecutar (en el entorno del Motor IA):
    uvicorn serving:app --host 0.0.0.0 --port 8502
"""

from typing import List, Optional

import numpy as np
from scipy.spatial import cKDTree
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import model_registry
from config import FEATURES
from database.connection import fetch_real_plant_data, send_predictions_to_api

app = FastAPI(
    title="Motor IA M-6 - Servicio de Inferencia",
    description="Predicción de ley de cobre (% Cu) con el modelo ganador entrenado por el Motor IA.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    bench: int = Field(..., description="Banco evaluado (m.s.n.m.)")
    persist: bool = Field(True, description="Persistir predicciones en la plataforma")
    with_uncertainty: bool = Field(True, description="Calcular P10/P90 e incertidumbre")


class ModelInfoResponse(BaseModel):
    success: bool
    model: dict


class DrillholePointRequest(BaseModel):
    x: float = Field(..., description="Coordenada X original de GeoMet")
    y: float = Field(..., description="Coordenada Y original de GeoMet")
    z: float = Field(..., description="Coordenada Z original de GeoMet")


class CopperCreekPointRequest(BaseModel):
    x: float = Field(..., description="UTM easting, EPSG:32612")
    y: float = Field(..., description="UTM northing, EPSG:32612")
    z: float = Field(..., description="Elevation in metres")


@app.get("/health")
def health():
    return {"status": "ok", "service": "motor-ia-inference"}


@app.get("/api/models/copper-creek/info")
def copper_creek_model_info():
    metadata = model_registry.get_copper_creek_metadata()
    if metadata is None:
        raise HTTPException(status_code=404, detail="No hay estimador Copper Creek publicado")
    try:
        model_registry.check_drillhole_dependencies(metadata)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "model": metadata}


@app.post("/api/models/copper-creek/predict")
def predict_copper_creek_point(payload: CopperCreekPointRequest):
    point = np.asarray([payload.x, payload.y, payload.z], dtype=float)
    if not np.isfinite(point).all():
        raise HTTPException(status_code=422, detail="Las coordenadas deben ser finitas")
    try:
        bundle, metadata = model_registry.load_copper_creek_winner()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if bundle is None or metadata is None:
        raise HTTPException(status_code=404, detail="No hay estimador Copper Creek publicado")
    for index, axis in enumerate(("x", "y", "z")):
        bounds = metadata["coordinate_bounds"][axis]
        if not bounds["min"] <= point[index] <= bounds["max"]:
            raise HTTPException(status_code=422, detail=f"{axis.upper()} fuera del rango de los ensayos")

    centered = point - np.asarray(metadata["coordinate_origin"], dtype=float)
    training_xyz = np.asarray(bundle["xyz"], dtype=float)
    neighbors = cKDTree(training_xyz).query_ball_point(
        centered, r=metadata["support_rule"]["max_distance_m"]
    )
    neighbors.sort(key=lambda index: float(np.linalg.norm(training_xyz[index] - centered)))
    selected = []
    seen_holes = set()
    for index in neighbors:
        hole = str(bundle["holes"][index])
        if hole in seen_holes:
            continue
        seen_holes.add(hole)
        selected.append(index)
        if len(selected) == metadata["support_rule"]["max_holes"]:
            break
    if len(selected) < metadata["support_rule"]["min_holes"]:
        raise HTTPException(status_code=422, detail="Punto sin soporte de tres sondajes independientes")

    if metadata["model_name"] == "IDW3":
        distances = np.linalg.norm(training_xyz[selected] - centered, axis=1)
        weights = 1 / np.maximum(distances, 1) ** 3
        grade = float(np.dot(weights, np.asarray(bundle["grade"])[selected]) / weights.sum())
    else:
        grade = float(np.asarray(bundle["model"].predict(centered.reshape(1, 3))).reshape(-1)[0])
    if not np.isfinite(grade):
        raise HTTPException(status_code=422, detail="El modelo no produjo una ley valida")
    return {
        "success": True,
        "mode": "exploratory_block_grade",
        "model_name": metadata["model_name"],
        "predicted_cu_pct": max(0.0, grade),
        "support_holes": len(selected),
        "nearest_hole_m": round(float(np.linalg.norm(training_xyz[selected[0]] - centered)), 2),
        "validation_rmse": metadata["comparison"][metadata["model_name"]]["mean_rmse"],
        "message": "Estimacion academica; no valida recursos ni despacho a planta",
    }


@app.get("/api/experiments/drillholes/info")
def drillhole_experiment_info():
    metadata = model_registry.get_drillhole_experiment_metadata()
    if metadata is None:
        raise HTTPException(status_code=404, detail="No hay modelo exploratorio de sondajes publicado")
    try:
        model_registry.check_drillhole_dependencies(metadata)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "model": metadata}


@app.post("/api/experiments/drillholes/predict")
def predict_drillhole_point(payload: DrillholePointRequest):
    point = np.asarray([[payload.x, payload.y, payload.z]], dtype=float)
    if not np.isfinite(point).all():
        raise HTTPException(status_code=422, detail="Las coordenadas deben ser finitas")
    try:
        model, metadata = model_registry.load_drillhole_experiment()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if model is None:
        raise HTTPException(status_code=404, detail="No hay modelo exploratorio de sondajes publicado")
    for i, axis in enumerate(("x", "y", "z")):
        bounds = metadata["coordinate_bounds"][axis]
        if not bounds["min"] <= point[0, i] <= bounds["max"]:
            raise HTTPException(
                status_code=422,
                detail=(f"{axis.upper()} está fuera del rango observado "
                        f"({bounds['min']:.2f} a {bounds['max']:.2f})"),
            )
    grade = float(np.asarray(model.predict(point), dtype=float).reshape(-1)[0])
    if not np.isfinite(grade):
        raise HTTPException(status_code=422, detail="El modelo no produjo una ley válida")
    return {
        "success": True,
        "mode": "drillholes_exploratory",
        "model_name": metadata["model_name"],
        "x": payload.x, "y": payload.y, "z": payload.z,
        "predicted_cu_pct": grade,
        "plausible": grade >= 0,
        "message": ("Predicción exploratoria; no representa ley de banco ni planta"
                    if grade >= 0 else
                    "La predicción es negativa y físicamente inválida; no usar este punto"),
    }


@app.get("/api/models/info", response_model=ModelInfoResponse)
def model_info(bench: int):
    _, meta = model_registry.load_winner(bench)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No hay modelo exportado para el banco {bench} m.s.n.m. "
                "Entrena en la Fase 4 y activa el Modelo Ganador en la Fase 6 del Motor IA."
            ),
        )
    return {"success": True, "model": meta}


@app.post("/api/models/predict")
def predict(payload: PredictRequest):
    bench = payload.bench
    model, meta = model_registry.load_winner(bench)
    if model is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No hay modelo exportado para el banco {bench} m.s.n.m. "
                "Entrena en la Fase 4 y activa el Modelo Ganador en la Fase 6 del Motor IA."
            ),
        )

    df = fetch_real_plant_data(bench=bench)
    if df is None or len(df) == 0:
        raise HTTPException(
            status_code=422,
            detail="No hay datos de control de procesos para reconstruir las features del modelo.",
        )

    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Features faltantes en los datos: {missing}",
        )

    X = df[FEATURES].to_numpy(dtype=float)

    model_name = meta.get("model_name", "Desconocido")

    if payload.with_uncertainty and hasattr(model, "predict_with_uncertainty"):
        predictions, std, p10, p90 = model.predict_with_uncertainty(X)
    else:
        predictions = model.predict(X)
        std, p10, p90 = None, None, None

    predictions = np.asarray(predictions, dtype=float).ravel()
    std = np.asarray(std, dtype=float).ravel() if std is not None else None
    p10 = np.asarray(p10, dtype=float).ravel() if p10 is not None else None
    p90 = np.asarray(p90, dtype=float).ravel() if p90 is not None else None

    pred_list = predictions.tolist()

    persisted = False
    persist_message = None
    if payload.persist:
        result = send_predictions_to_api(bench, model_name, pred_list)
        persisted = bool(result.get("success"))
        persist_message = result.get("message", "")

    sample = [
        {
            "predicted": round(float(predictions[i]), 5),
            "p10": round(float(p10[i]), 5) if p10 is not None else None,
            "p90": round(float(p90[i]), 5) if p90 is not None else None,
            "std": round(float(std[i]), 5) if std is not None else None,
        }
        for i in range(min(10, len(pred_list)))
    ]

    return {
        "success": True,
        "bench": bench,
        "model_name": model_name,
        "persisted": persisted,
        "persist_message": persist_message,
        "features": FEATURES,
        "n": len(pred_list),
        "summary": {
            "mean": float(np.mean(predictions)),
            "std": float(np.std(predictions)),
            "min": float(np.min(predictions)),
            "max": float(np.max(predictions)),
        },
        "sample": sample,
    }
