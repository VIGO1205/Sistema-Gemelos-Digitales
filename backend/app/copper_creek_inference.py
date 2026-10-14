"""Inference for the published Copper Creek Random Forest inside the API process."""

import json
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import joblib
import numpy as np
from fastapi import HTTPException
from scipy.spatial import cKDTree


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "model_artifacts"
MODEL_PATH = ARTIFACT_DIR / "copper_creek_winner.joblib"
METADATA_PATH = ARTIFACT_DIR / "copper_creek_winner.metadata.json"


@lru_cache(maxsize=1)
def model_metadata() -> dict:
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        raise HTTPException(status_code=503, detail="No hay estimador Copper Creek publicado")
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    if metadata.get("mode") != "exploratory_block_grade":
        raise HTTPException(status_code=503, detail="Metadatos Copper Creek incompatibles")
    mismatches = []
    for package, trained in metadata.get("library_versions", {}).items():
        try:
            installed = version(package)
        except PackageNotFoundError:
            installed = "no instalado"
        if trained != installed:
            mismatches.append(f"{package}: entrenamiento {trained}, servicio {installed}")
    if mismatches:
        raise HTTPException(
            status_code=503,
            detail="Versiones incompatibles para el modelo publicado: " + "; ".join(mismatches),
        )
    return metadata


@lru_cache(maxsize=1)
def _model_bundle() -> dict:
    model_metadata()
    try:
        bundle = joblib.load(MODEL_PATH)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="No se pudo cargar el modelo Copper Creek") from exc
    if not isinstance(bundle, dict) or not all(
        key in bundle for key in ("model", "xyz", "grade", "holes")
    ):
        raise HTTPException(status_code=503, detail="Artefacto Copper Creek incompleto")
    return bundle


def predict(x: float, y: float, z: float) -> dict:
    metadata = model_metadata()
    point = np.asarray([x, y, z], dtype=float)
    if not np.isfinite(point).all():
        raise HTTPException(status_code=422, detail="Las coordenadas deben ser finitas")
    for index, axis in enumerate(("x", "y", "z")):
        bounds = metadata["coordinate_bounds"][axis]
        if not bounds["min"] <= point[index] <= bounds["max"]:
            raise HTTPException(status_code=422, detail=f"{axis.upper()} fuera del rango de los ensayos")

    bundle = _model_bundle()
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
