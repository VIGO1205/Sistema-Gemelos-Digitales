"""Select an exploratory Cu estimator using unseen Copper Creek drillholes.

Only X/Y/Z from public Mammoth assay composites are used. Validation holds out
complete holes; the previously published GeoMet model is never reused here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from scipy.spatial import cKDTree
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from xgboost import XGBRegressor

from copper_creek_samples import load_study_samples, source_hashes


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "motor_ia_m6" / "model_artifacts" / "copper_creek_winner.joblib"
METADATA = ARTIFACT.with_suffix(".metadata.json")
ORIGIN = np.array([548470.0, 3623920.0, 1250.0])
SEARCH_RADIUS_M = 120.0
MAX_HOLES = 8
MIN_HOLES = 3


def centered_xyz(points):
    return np.asarray([point[:3] for point in points], dtype=float) - ORIGIN


def idw3_from_independent_holes(train_xyz, train_grade, train_holes, query_xyz):
    """Reproduce the scene's eight-hole IDW3 support rule for held-out points."""
    tree = cKDTree(train_xyz)
    distances, indices = tree.query(
        query_xyz, k=min(160, len(train_xyz)), distance_upper_bound=SEARCH_RADIUS_M
    )
    predictions = np.full(len(query_xyz), np.nan, dtype=float)
    for row, (distance_row, index_row) in enumerate(zip(distances, indices)):
        selected = []
        seen = set()
        for distance, index in zip(distance_row, index_row):
            if not np.isfinite(distance) or index >= len(train_xyz):
                break
            hole = train_holes[index]
            if hole in seen:
                continue
            seen.add(hole)
            selected.append((distance, train_grade[index]))
            if len(selected) == MAX_HOLES:
                break
        if len(selected) < MIN_HOLES:
            continue
        weights = np.asarray([1 / max(distance, 1) ** 3 for distance, _ in selected])
        predictions[row] = np.dot(weights, [grade for _, grade in selected]) / weights.sum()
    return predictions


def candidate(name):
    if name == "Random Forest":
        return RandomForestRegressor(
            n_estimators=160, min_samples_leaf=4, max_features=2,
            n_jobs=4, random_state=42,
        )
    if name == "XGBoost":
        return XGBRegressor(
            n_estimators=350, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.9, n_jobs=4,
            random_state=42, objective="reg:squarederror",
        )
    raise ValueError(name)


def main():
    _, _, points, by_hole, invalid_cu = load_study_samples()
    xyz = centered_xyz(points)
    grade = np.asarray([point[3] for point in points], dtype=float)
    holes = np.asarray([point[5] for point in points])
    if len(points) < 100 or len(by_hole) < 20:
        raise RuntimeError("Insufficient independent assays for Copper Creek validation")

    results = {name: [] for name in ("IDW3", "Random Forest", "XGBoost")}
    for fold, (train, test) in enumerate(GroupKFold(n_splits=5).split(xyz, grade, holes), 1):
        baseline = idw3_from_independent_holes(
            xyz[train], grade[train], holes[train], xyz[test]
        )
        supported = np.isfinite(baseline)
        if supported.sum() < 30:
            raise RuntimeError(f"Only {supported.sum()} supported samples in fold {fold}")
        predictions = {"IDW3": baseline}
        for name in ("Random Forest", "XGBoost"):
            estimator = candidate(name)
            estimator.fit(xyz[train], grade[train])
            predictions[name] = estimator.predict(xyz[test])
        for name, predicted in predictions.items():
            actual = grade[test][supported]
            estimated = predicted[supported]
            results[name].append({
                "fold": fold,
                "test_holes": int(len(set(holes[test]))),
                "test_samples": int(len(test)),
                "supported_samples": int(supported.sum()),
                "rmse": float(mean_squared_error(actual, estimated) ** 0.5),
                "mae": float(mean_absolute_error(actual, estimated)),
                "r2": float(r2_score(actual, estimated)),
            })

    comparison = {}
    for name, folds in results.items():
        comparison[name] = {
            "mean_rmse": float(np.mean([fold["rmse"] for fold in folds])),
            "mean_mae": float(np.mean([fold["mae"] for fold in folds])),
            "mean_r2": float(np.mean([fold["r2"] for fold in folds])),
            "folds": folds,
        }
    winner = min(comparison, key=lambda name: comparison[name]["mean_rmse"])
    metadata = {
        "project": "Copper Creek - Mammoth",
        "mode": "exploratory_block_grade",
        "model_name": winner,
        "features": ["x", "y", "z"],
        "target": "Cu medido (% Cu) en composites ~6 m",
        "validation": "5 folds con sondajes completos no vistos; mismas muestras con soporte IDW3",
        "sample_count": len(points),
        "hole_count": len(by_hole),
        "invalid_cu_rows": invalid_cu,
        "source_hashes": source_hashes(),
        "library_versions": {
            package: version(package)
            for package in ("numpy", "scikit-learn", "xgboost", "joblib")
        },
        "coordinate_bounds": {
            axis: {"min": float(xyz[:, i].min() + ORIGIN[i]), "max": float(xyz[:, i].max() + ORIGIN[i])}
            for i, axis in enumerate(("x", "y", "z"))
        },
        "support_rule": {"max_distance_m": SEARCH_RADIUS_M, "min_holes": MIN_HOLES, "max_holes": MAX_HOLES},
        "coordinate_origin": ORIGIN.tolist(),
        "comparison": comparison,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "limitations": "No hay sólidos oficiales del tajo, dominios, densidades medidas ni datos de planta. No valida recursos ni despacho.",
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    estimator = None
    if winner != "IDW3":
        estimator = candidate(winner)
        estimator.fit(xyz, grade)
    temporary = ARTIFACT.with_suffix(".joblib.tmp")
    joblib.dump({"model": estimator, "xyz": xyz, "grade": grade, "holes": holes}, temporary)
    temporary.replace(ARTIFACT)
    temporary_metadata = METADATA.with_suffix(".json.tmp")
    temporary_metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_metadata.replace(METADATA)
    for name, score in comparison.items():
        print(f"{name}: RMSE={score['mean_rmse']:.4f}, MAE={score['mean_mae']:.4f}, R2={score['mean_r2']:.4f}")
    print(f"Ganador exploratorio Copper Creek: {winner}")
    print(METADATA)


if __name__ == "__main__":
    main()
