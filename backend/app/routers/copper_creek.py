"""Read-only study scene built from the public Copper Creek drilling files."""

import json
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/copper-creek", tags=["Copper Creek"])
SCENE_PATH = Path(__file__).resolve().parents[2] / "data" / "copper_creek_mammoth.json"
ML_INFERENCE_URL = os.getenv("ML_INFERENCE_URL", "http://host.docker.internal:8502")
LOCAL_MODEL = os.getenv("COPPER_CREEK_LOCAL_MODEL", "false").lower() == "true"


class CopperCreekPointRequest(BaseModel):
    x: float
    y: float
    z: float


@router.get("/mammoth-reconstruction")
def mammoth_reconstruction():
    if not SCENE_PATH.is_file():
        raise HTTPException(status_code=503, detail="Reconstrucción no generada")
    with SCENE_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


async def _forward_model(method: str, path: str, payload: dict | None = None):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, f"{ML_INFERENCE_URL}{path}", json=payload
            )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=503, detail="Motor IA Copper Creek no disponible") from exc
    if response.is_error:
        try:
            detail = response.json().get("detail", "Error de inferencia Copper Creek")
        except ValueError:
            detail = "Error de inferencia Copper Creek"
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@router.get("/model-info")
async def copper_creek_model_info():
    if LOCAL_MODEL:
        from app.copper_creek_inference import model_metadata

        return {"success": True, "model": model_metadata()}
    return await _forward_model("GET", "/api/models/copper-creek/info")


@router.post("/predict")
async def copper_creek_predict(payload: CopperCreekPointRequest):
    if LOCAL_MODEL:
        from app.copper_creek_inference import predict

        return predict(payload.x, payload.y, payload.z)
    return await _forward_model(
        "POST", "/api/models/copper-creek/predict", payload.model_dump()
    )
