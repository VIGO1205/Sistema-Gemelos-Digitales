"""
Registro de modelos entrenados del Motor IA M-6.

Persiste el modelo ganador (joblib) junto con sus metadatos en disco para
que el servicio FastAPI de inferencia (serving.py) lo cargue y ejecute
predicciones bajo demanda (arquitectura train/serve separados).
"""

import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np

from config import FEATURES

MODEL_ARTIFACTS_DIR = Path(__file__).resolve().parent / "model_artifacts"
EXPLORATORY_MODEL_NAME = "drillholes_exploratory.joblib"
EXPLORATORY_META_NAME = "drillholes_exploratory.metadata.json"
COPPER_CREEK_MODEL_NAME = "copper_creek_winner.joblib"
COPPER_CREEK_META_NAME = "copper_creek_winner.metadata.json"
MODEL_DEPENDENCIES = ("numpy", "scikit-learn", "xgboost", "pykrige", "torch", "joblib")


def _ensure_dir() -> Path:
    MODEL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return MODEL_ARTIFACTS_DIR


def export_winner(winner_model, model_name: str, bench: int, metrics: dict) -> dict:
    """Guarda el modelo ganador y sus metadatos en el registro de inferencia."""
    d = _ensure_dir()
    model_path = d / f"winner_{bench}.joblib"
    meta_path = d / f"winner_{bench}.metadata.json"

    joblib.dump(winner_model, model_path)

    metadata = {
        "bench": bench,
        "model_name": model_name,
        "features": list(FEATURES),
        "metrics": metrics or {},
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "artifact": model_path.name,
    }
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return metadata


def load_winner(bench: int):
    """Carga el modelo ganador exportado para un banco."""
    model_path = MODEL_ARTIFACTS_DIR / f"winner_{bench}.joblib"
    meta_path = MODEL_ARTIFACTS_DIR / f"winner_{bench}.metadata.json"
    if not model_path.exists():
        return None, None

    metadata = None
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    return joblib.load(model_path), metadata


def list_artifacts() -> list:
    """Lista los modelos exportados en el registro."""
    d = MODEL_ARTIFACTS_DIR
    if not d.exists():
        return []
    artifacts = []
    for p in sorted(d.glob("winner_*.metadata.json")):
        artifacts.append(json.loads(p.read_text(encoding="utf-8")))
    return artifacts


def export_drillhole_experiment(model, model_name: str, metrics: dict,
                                coordinates) -> dict:
    """Publica inferencia espacial GeoMet sin tocar los modelos por banco."""
    xyz = np.asarray(coordinates, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) == 0 or not np.isfinite(xyz).all():
        raise ValueError("Se requieren coordenadas x/y/z finitas del experimento")
    d = _ensure_dir()
    model_path = d / EXPLORATORY_MODEL_NAME
    meta_path = d / EXPLORATORY_META_NAME
    bounds = {
        axis: {"min": float(xyz[:, i].min()), "max": float(xyz[:, i].max()),
               "median": float(np.median(xyz[:, i]))}
        for i, axis in enumerate(("x", "y", "z"))
    }
    metadata = {
        "mode": "drillholes_exploratory",
        "dataset": "GeoMet drillholes",
        "model_name": model_name,
        "features": ["x", "y", "z"],
        "target": "Cu medido (% Cu)",
        "validation": "sondajes completos no vistos",
        "sample_count": len(xyz),
        "coordinate_bounds": bounds,
        "metrics": {k: float(v) for k, v in metrics.items() if v is not None},
        "library_versions": {name: version(name) for name in MODEL_DEPENDENCIES},
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "artifact": EXPLORATORY_MODEL_NAME,
    }
    temporary_model = d / (EXPLORATORY_MODEL_NAME + ".tmp")
    temporary_meta = d / (EXPLORATORY_META_NAME + ".tmp")
    try:
        joblib.dump(model, temporary_model)
        temporary_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        temporary_model.replace(model_path)
        temporary_meta.replace(meta_path)
    finally:
        temporary_model.unlink(missing_ok=True)
        temporary_meta.unlink(missing_ok=True)
    return metadata


def get_drillhole_experiment_metadata():
    """Consulta el despliegue exploratorio sin cargar el modelo."""
    model_path = MODEL_ARTIFACTS_DIR / EXPLORATORY_MODEL_NAME
    meta_path = MODEL_ARTIFACTS_DIR / EXPLORATORY_META_NAME
    if not model_path.exists() or not meta_path.exists():
        return None
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return metadata if metadata.get("mode") == "drillholes_exploratory" else None


def check_drillhole_dependencies(metadata):
    """Impide deserializar un joblib con librerías distintas a las de entrenamiento."""
    def compatible(name, trained, installed):
        # El wheel de Torch para CPU añade "+cpu" al mismo release público.
        # El artefacto entrenado en Windows registra la versión sin ese sufijo.
        if name == "torch":
            return trained.partition("+")[0] == installed.partition("+")[0]
        return trained == installed

    mismatches = [
        f"{name}: entrenamiento {trained}, servicio {installed}"
        for name, trained in metadata.get("library_versions", {}).items()
        if not compatible(name, trained, installed := version(name))
    ]
    if mismatches:
        raise RuntimeError("Versiones incompatibles para el modelo publicado: "
                           + "; ".join(mismatches) + ". Reconstruye motor-inference.")


def load_drillhole_experiment():
    metadata = get_drillhole_experiment_metadata()
    if metadata is None:
        return None, None
    check_drillhole_dependencies(metadata)
    model = joblib.load(MODEL_ARTIFACTS_DIR / EXPLORATORY_MODEL_NAME)
    return model, metadata


def get_copper_creek_metadata():
    meta_path = MODEL_ARTIFACTS_DIR / COPPER_CREEK_META_NAME
    if not meta_path.is_file():
        return None
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    if metadata.get("mode") != "exploratory_block_grade":
        return None
    model_path = MODEL_ARTIFACTS_DIR / COPPER_CREEK_MODEL_NAME
    if not model_path.is_file():
        return None
    return metadata


def load_copper_creek_winner():
    metadata = get_copper_creek_metadata()
    if metadata is None:
        return None, None
    check_drillhole_dependencies(metadata)
    bundle = joblib.load(MODEL_ARTIFACTS_DIR / COPPER_CREEK_MODEL_NAME)
    if not all(key in bundle for key in ("model", "xyz", "grade", "holes")):
        raise RuntimeError("Artefacto Copper Creek incompleto")
    return bundle, metadata
