"""
Router de Inferencia en Vivo del Motor IA.

Proxy de las peticiones de predicción hacia el servicio de inferencia del
host (puerto 8502), donde vive el modelo entrenado con sus dependencias
ML (torch/sklearn/xgboost/pykrige). Esto mantiene un ÚNICO origen de API
para el frontend:  POST /api/models/predict.
"""

import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ML_INFERENCE_URL = os.getenv(
    "ML_INFERENCE_URL",
    "http://host.docker.internal:8502",
)

router = APIRouter(prefix="/api/models", tags=["Inferencia Motor IA"])


class PredictRequest(BaseModel):
    bench: int = Field(..., description="Banco evaluado (m.s.n.m.)")
    persist: bool = Field(True, description="Persistir predicciones en la plataforma")
    with_uncertainty: bool = Field(True, description="Calcular P10/P90 e incertidumbre")


class DrillholePointRequest(BaseModel):
    x: float
    y: float
    z: float


async def _forward_exploratory(method: str, path: str, payload: dict = None):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, f"{ML_INFERENCE_URL}{path}", json=payload
            )
    except (httpx.ConnectError, httpx.TimeoutException):
        raise HTTPException(status_code=503, detail="Servicio de inferencia exploratoria no disponible")
    if response.is_error:
        try:
            detail = response.json().get("detail", "Error de inferencia exploratoria")
        except ValueError:
            detail = "Error de inferencia exploratoria"
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@router.get("/experiments/drillholes/info")
async def exploratory_drillhole_info():
    return await _forward_exploratory("GET", "/api/experiments/drillholes/info")


@router.post("/experiments/drillholes/predict")
async def exploratory_drillhole_predict(payload: DrillholePointRequest):
    return await _forward_exploratory(
        "POST", "/api/experiments/drillholes/predict", payload.model_dump()
    )


@router.get("/info")
async def forward_info(bench: int):
    """Metadata del modelo ganador exportado para un banco (inferencia en vivo)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{ML_INFERENCE_URL}/api/models/info",
                params={"bench": bench},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Motor de inferencia IA no disponible (servicio 8502). "
                   "Ejecuta 'uvicorn serving:app --host 0.0.0.0 --port 8502' en el host del Motor IA.",
        )


@router.post("/predict")
async def forward_predict(payload: PredictRequest):
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{ML_INFERENCE_URL}/api/models/predict",
                json=payload.model_dump(),
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=503, detail=resp.json().get("detail", "Modelo no exportado"))
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Motor de inferencia IA no disponible (servicio 8502). "
                   "Ejecuta 'uvicorn serving:app --host 0.0.0.0 --port 8502' en el host del Motor IA.",
        )
