"""Read and locate Copper Creek assay composites used by the Mammoth study."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path


DATASET = Path(__file__).resolve().parents[2] / "dataset"


def source_hashes() -> dict[str, str]:
    patterns = ("*collars*csv", "*surveys*csv", "*assays*csv")
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for pattern in patterns for path in (next(DATASET.glob(pattern)),)
    }


def number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        result = float(value.replace(",", "."))
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def read_csv(pattern: str):
    path = next(DATASET.glob(pattern))
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream, delimiter=";")


def trace_position(collar: dict, stations: list[tuple[float, float, float]], depth: float):
    """Integrate measured downhole azimuth and inclination in short segments."""
    x, y, z = collar["x"], collar["y"], collar["z"]
    previous = 0.0
    while previous < depth:
        step = min(depth, previous + 10.0)
        mid = (previous + step) / 2
        before = max((s for s in stations if s[0] <= mid), default=stations[0])
        after = min((s for s in stations if s[0] >= mid), default=stations[-1])
        fraction = 0.0 if after[0] == before[0] else (mid - before[0]) / (after[0] - before[0])
        azimuth = before[1] + ((after[1] - before[1] + 180) % 360 - 180) * fraction
        inclination = before[2] + (after[2] - before[2]) * fraction
        az, inc = math.radians(azimuth), math.radians(inclination)
        length = step - previous
        horizontal = length * math.cos(inc)
        x += horizontal * math.sin(az)
        y += horizontal * math.cos(az)
        z += length * math.sin(inc)
        previous = step
    return x, y, z


def load_study_samples():
    """Return collars, surveys, geolocated 6 m composites, and quality counts."""
    collars = {}
    for row in read_csv("*collars*csv"):
        x, y, z = (number(row[k]) for k in ("Easting", "Northing", "Elevation"))
        depth = number(row["Total Depth"])
        if (x is None or y is None or z is None or depth is None or depth <= 0
                or row["Drilled Location"].strip().lower() != "surface"
                or not 547650 <= x <= 549300 or not 3623100 <= y <= 3624750):
            continue
        collars[row["Hole ID"]] = {
            "x": x, "y": y, "z": z, "depth": depth,
            "azimuth": number(row["Azimuth"]) or 0.0,
            "dip": -abs(number(row["Inclination"]) or -90.0),
            "year": row["Year Drilled"].strip(),
        }

    surveys = defaultdict(list)
    for row in read_csv("*surveys*csv"):
        hole = row["Hole ID"]
        if hole not in collars:
            continue
        depth, azimuth, dip = (number(row[k]) for k in ("Depth (m)", "Azimuth", "Inclination"))
        if None not in (depth, azimuth, dip):
            surveys[hole].append((depth, azimuth, dip))
    for hole, collar in collars.items():
        surveys[hole].sort()
        if not surveys[hole] or surveys[hole][0][0] > 0:
            surveys[hole].insert(0, (0.0, collar["azimuth"], collar["dip"]))

    composites = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    invalid_cu = 0
    for row in read_csv("*assays*csv"):
        hole = row["Hole ID"]
        if hole not in collars:
            continue
        start, end, cu = (number(row[k]) for k in ("From (m)", "To (m)", "Cu (%)"))
        au = number(row["Au (ppm)"])
        if start is None or end is None or cu is None or not 0 <= cu <= 20 or end <= start:
            invalid_cu += 1
            continue
        for interval in range(int(start // 6), int((end - 1e-8) // 6) + 1):
            overlap = min(end, (interval + 1) * 6) - max(start, interval * 6)
            if overlap <= 0:
                continue
            cell = composites[(hole, interval)]
            cell[0] += cu * overlap
            cell[1] += overlap
            if au is not None and au >= 0:
                cell[2] += au * overlap
                cell[3] += overlap

    sample_points = []
    by_hole = defaultdict(list)
    for (hole, interval), (cu_sum, length, au_sum, au_length) in composites.items():
        if length < 1.0:
            continue
        depth = min(interval * 6 + 3, collars[hole]["depth"])
        x, y, z = trace_position(collars[hole], surveys[hole], depth)
        if not 547950 <= x <= 548990 or not 3623410 <= y <= 3624430 or not 1120 <= z <= 1350:
            continue
        point = (x, y, z, cu_sum / length, au_sum / au_length if au_length else None, hole)
        sample_points.append(point)
        by_hole[hole].append(point)
    return collars, surveys, sample_points, by_hole, invalid_cu
