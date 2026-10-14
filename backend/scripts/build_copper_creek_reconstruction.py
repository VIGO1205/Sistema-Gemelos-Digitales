"""Build a clearly labelled Mammoth study scene from public Copper Creek CSVs.

The pit outlines are an approximation of Figure 16-14 in the 2023 PEA, not
surveyed pit solids. Block grades are exploratory IDW3 estimates, not the
company's resource block model or the separately trained GeoMet model.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np

from copper_creek_samples import load_study_samples, source_hashes, trace_position


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "backend" / "data" / "copper_creek_mammoth.json"
MODEL_ARTIFACT = ROOT / "motor_ia_m6" / "model_artifacts" / "copper_creek_winner.joblib"
MODEL_METADATA = MODEL_ARTIFACT.with_suffix(".metadata.json")
CENTER_X, CENTER_Y = 548470.0, 3623920.0
GRID_X, GRID_Y, GRID_Z = 546250.0, 3621800.0, 1520.0
DX, DY, DZ = 20, 20, 12
BENCHES = [GRID_Z - DZ * i for i in range(17, 30)]
MAX_SAMPLE_DISTANCE = 120.0


def pit_radius(angle: float, level: int) -> float:
    # Stylized upper-sector outline inspired by report Figure 16-14. Multiple
    # smooth lobes produce irregular benches without claiming surveyed edges.
    def angle_delta(target: float) -> float:
        return math.atan2(math.sin(angle - target), math.cos(angle - target))

    def rounded_lobe(target: float, width: float, height: float) -> float:
        return height * math.exp(-.5 * (angle_delta(target) / width) ** 2)

    outer_radius = (
        470.0
        + 43.0 * math.cos(2 * angle - .6)
        + 25.0 * math.sin(3 * angle + .4)
        + 23.0 * math.sin(5 * angle + .2)
        + 17.0 * math.cos(8 * angle - .5)
        + 13.0 * math.sin(13 * angle + .1)
        + 9.0 * math.cos(19 * angle - .3)
        + 5.0 * math.sin(27 * angle + .6)
        - rounded_lobe(.7, .23, 27.0)
        + rounded_lobe(2.7, .30, 23.0)
        - rounded_lobe(-2.1, .24, 17.0)
        + rounded_lobe(.18, .105, 27.0)
        - rounded_lobe(1.22, .11, 22.0)
        + rounded_lobe(2.03, .12, 30.0)
        - rounded_lobe(3.36, .10, 21.0)
        + rounded_lobe(4.42, .125, 26.0)
        - rounded_lobe(5.47, .11, 20.0)
    )
    # Erode each bench in different sectors. The moving, rounded cuts make the
    # outlines visibly distinct while every setback stays positive, so lower
    # contours remain inside the level above instead of crossing it.
    radius = outer_radius
    for band in range(1, level + 1):
        phase = 2.399963229728653 * band
        main_width = .22 + .015 * (band % 4)
        main_depth = 80.0 + 8.0 * (band % 3)
        secondary_width = .17 + .01 * ((band + 1) % 3)
        secondary_depth = 40.0 + 7.0 * ((band + 2) % 3)
        setback = (
            4.0
            + 1.5 * (1.0 + math.cos(2 * angle + phase))
            + rounded_lobe(.3 + phase, main_width, main_depth)
            + rounded_lobe(2.4 + 1.35 * band, secondary_width, secondary_depth)
            + rounded_lobe(4.8 - .9 * band, .18, 16.0)
        )
        radius -= min(setback, 115.0)
    # Widen only the five upper benches. Each extra setback has its own smooth
    # lobes, so the crest and upper terraces open at different angles while
    # the lower section keeps its existing footprint.
    for band in range(level + 1, 6):
        radius += (
            8.0
            + 2.5 * (1.0 + math.cos(2 * angle + 1.19 * band))
            + rounded_lobe(.52 + 2.17 * band, .28, 28.0)
            + rounded_lobe(2.8 - 1.38 * band, .18, 14.0)
        )
    return radius


def pit_center(level: int) -> tuple[float, float]:
    # Gentle offsets avoid identical concentric rings without moving the pit.
    return (
        CENTER_X + 5.0 * math.sin(.38 * level),
        CENTER_Y + 4.0 * (math.cos(.32 * level) - 1.0),
    )


def inside_pit(x: float, y: float, level: int) -> bool:
    cx, cy = pit_center(level)
    ox, oy = x - cx, y - cy
    angle = math.atan2(oy, ox)
    return math.hypot(ox, oy) <= pit_radius(angle, level) - 12


def main() -> None:
    collars, surveys, sample_points, by_hole, invalid_cu = load_study_samples()
    if not MODEL_METADATA.is_file():
        raise RuntimeError("Primero ejecuta benchmark_copper_creek.py para validar y publicar el estimador.")
    model_metadata = json.loads(MODEL_METADATA.read_text(encoding="utf-8"))
    if model_metadata.get("source_hashes") != source_hashes():
        raise RuntimeError("Los CSV de Copper Creek cambiaron; vuelve a validar y entrenar el modelo.")
    if model_metadata.get("sample_count") != len(sample_points):
        raise RuntimeError("El artefacto y los composites de Copper Creek no coinciden.")
    model_name = model_metadata["model_name"]
    model = None
    if model_name != "IDW3":
        if not MODEL_ARTIFACT.is_file():
            raise RuntimeError("Falta el artefacto del modelo ganador de Copper Creek.")
        model = joblib.load(MODEL_ARTIFACT)["model"]

    # Three-dimensional spatial bins keep nearest-neighbour searches bounded.
    bin_size = 60
    bins = defaultdict(list)
    for point in sample_points:
        key = tuple(math.floor(v / bin_size) for v in point[:3])
        bins[key].append(point)

    blocks = []
    skipped_unsupported = 0
    ix0 = math.floor((CENTER_X - 220 - GRID_X) / DX)
    ix1 = math.ceil((CENTER_X + 220 - GRID_X) / DX)
    iy0 = math.floor((CENTER_Y - 220 - GRID_Y) / DY)
    iy1 = math.ceil((CENTER_Y + 220 - GRID_Y) / DY)
    for level, bench in enumerate(BENCHES):
        # Heights are aligned to the source model's 12 m vertical lattice.
        z = bench
        for ix in range(ix0, ix1 + 1):
            x = GRID_X + ix * DX + DX / 2
            for iy in range(iy0, iy1 + 1):
                y = GRID_Y + iy * DY + DY / 2
                if not inside_pit(x, y, level):
                    continue
                key = tuple(math.floor(v / bin_size) for v in (x, y, z))
                candidates = []
                for bx in range(key[0] - 2, key[0] + 3):
                    for by in range(key[1] - 2, key[1] + 3):
                        for bz in range(key[2] - 2, key[2] + 3):
                            candidates.extend(bins.get((bx, by, bz), ()))
                nearby = []
                for point in candidates:
                    distance = math.dist((x, y, z), point[:3])
                    if distance <= MAX_SAMPLE_DISTANCE:
                        nearby.append((distance, point))
                nearby.sort(key=lambda item: item[0])
                # Require independent support from at least three distinct holes.
                nearest_holes = {}
                for distance, point in nearby:
                    nearest_holes.setdefault(point[5], (distance, point))
                    if len(nearest_holes) >= 8:
                        break
                if len(nearest_holes) < 3:
                    skipped_unsupported += 1
                    continue
                selected = list(nearest_holes.values())
                weights = [1 / max(distance, 1) ** 3 for distance, _ in selected]
                total_weight = sum(weights)
                cu_est = sum(weight * point[3] for weight, (_, point) in zip(weights, selected)) / total_weight
                au_pairs = [(weight, point[4]) for weight, (_, point) in zip(weights, selected) if point[4] is not None]
                au_est = (sum(weight * au for weight, au in au_pairs) / sum(weight for weight, _ in au_pairs)) if au_pairs else 0.0
                # Spatial spread is a visual support indicator, not a calibrated probability interval.
                spread = math.sqrt(sum(weight * (point[3] - cu_est) ** 2 for weight, (_, point) in zip(weights, selected)) / total_weight)
                nearest_distance = selected[0][0]
                blocks.append({
                    "id": f"CC-MAM-{int(z)}-{ix}-{iy}", "x": x, "y": y, "z": z,
                    "bench": int(z), "dx": DX, "dy": DY, "dz": DZ,
                    "cu_base": round(selected[0][1][3], 4),
                    "cu_bayesian": round(cu_est, 4),
                    "cu_idw3": round(cu_est, 4),
                    "cu_variance": round(spread ** 2, 5),
                    "au_base": round(au_est, 4), "au_bayesian": round(au_est, 4),
                    "epistemic_unc": round(spread, 4), "aleatoric_unc": 0,
                    "total_unc": round(spread, 4), "p10": 0, "p50": round(cu_est, 4), "p90": 0,
                    "confidence_pct": 0,
                    "tonnage": DX * DY * DZ * 2.6, "density": 2.6,
                    "lithology": "No determinada", "alteration": "No determinada",
                    "hyperspectral_mineral": "Sin datos SWIR", "dominant_mineral": "No determinado",
                    "category": "Unclassified", "deviation_pct": 0,
                    "nearest_drillhole_m": round(nearest_distance, 1),
                    "support_holes": len(selected),
                })

    if model is not None and blocks:
        origin = np.asarray(model_metadata["coordinate_origin"], dtype=float)
        coordinates = np.asarray(
            [[block["x"], block["y"], block["z"]] for block in blocks], dtype=float
        ) - origin
        predicted = np.asarray(model.predict(coordinates), dtype=float).reshape(-1)
        if len(predicted) != len(blocks) or not np.isfinite(predicted).all():
            raise RuntimeError("El modelo ganador produjo predicciones invalidas para los cubos.")
        for block, grade in zip(blocks, predicted):
            # Keep the public IDW3 estimate separately for a clear baseline.
            block["cu_bayesian"] = round(max(0.0, float(grade)), 4)
            block["p50"] = block["cu_bayesian"]

    contours = []
    for level, bench in enumerate(BENCHES):
        points = []
        cx, cy = pit_center(level)
        for step in range(192):
            angle = 2 * math.pi * step / 192
            radius = pit_radius(angle, level)
            points.append([round(cx + radius * math.cos(angle), 1),
                           round(cy + radius * math.sin(angle), 1)])
        contours.append({"bench": bench, "points": points})

    # Display only trajectories crossing the modelled window. Other assays may
    # still support the estimates; the UI explicitly reports this visual subset.
    display_candidates = []
    for hole, collar in collars.items():
        if hole not in by_hole:
            continue
        trace = []
        trace_start_depth = None
        max_depth = min(collar["depth"], 450.0)
        depth = 0.0
        while depth <= max_depth:
            tx, ty, tz = trace_position(collar, surveys[hole], depth)
            level_at_depth = max(0, min(len(BENCHES) - 1, int((BENCHES[0] - tz) // DZ)))
            if (abs(tx - CENTER_X) <= 235 and abs(ty - CENTER_Y) <= 235
                    and BENCHES[-1] - 12 <= tz <= BENCHES[0] + 24
                    and inside_pit(tx, ty, level_at_depth)):
                if trace_start_depth is None:
                    trace_start_depth = depth
                trace.append([round(tx, 2), round(ty, 2), round(tz, 2)])
            elif trace:
                break
            depth += 15.0
        if len(trace) < 2:
            continue
        distance_to_center = min(math.hypot(x - CENTER_X, y - CENTER_Y) for x, y, _ in trace)
        display_candidates.append((distance_to_center, {
            "hole_id": hole, "type": "DIAMOND_DDH", "x": collar["x"], "y": collar["y"],
            "z": collar["z"], "total_depth_m": collar["depth"],
            "azimuth": collar["azimuth"], "dip": collar["dip"],
            "date_drilled": collar["year"] or "Sin fecha", "samples": [],
            "trace": trace, "trace_start_depth_m": trace_start_depth,
        }))
    display_candidates.sort(key=lambda candidate: candidate[0])
    drillholes = [candidate[1] for candidate in display_candidates[:64]]

    payload = {
        "metadata": {
            "project": "Copper Creek — sector Mammoth",
            "status": "Reconstrucción académica aproximada; no es el modelo oficial ni valida reservas o despacho",
            "crs": "EPSG:32612 (WGS 84 / UTM 12N)",
            "source": "Faraday Copper, CSV de enero 2026; NI 43-101 PEA 2023, §§14.7-14.8, 16.4, figura 16-14",
            "method": f"Composites ~6 m; {model_name} seleccionado por validación de sondajes completos no vistos",
            "model_name": model_name,
            "model_validation": {
                name: {key: round(scores[key], 4) for key in ("mean_rmse", "mean_mae", "mean_r2")}
                for name, scores in model_metadata["comparison"].items()
            },
            "support_method": "Hasta 8 sondajes independientes a 120 m; minimo 3. IDW3 conservado como referencia.",
            "model_exported_at": model_metadata["exported_at"],
            "geometry": "Ventana superior de Mammoth; contornos aproximados con base abierta, elevaciones y taludes asumidos",
            "bench_height_m": 12, "block_size_m": [DX, DY, DZ],
            "study_holes": len(by_hole), "displayed_holes": len(drillholes),
            "used_composites": len(sample_points),
            "skipped_unsupported_blocks": skipped_unsupported,
            "invalid_cu_rows": invalid_cu,
            "reference_center": [CENTER_X, CENTER_Y],
        },
        "blocks": blocks, "drillholes": drillholes, "pit_levels": contours,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(blocks)} bloques estimados, {len(by_hole)} sondajes en sector, {len(drillholes)} trazas visibles, {len(sample_points)} composites; {skipped_unsupported} bloques sin soporte")
    print(OUTPUT)


if __name__ == "__main__":
    main()
