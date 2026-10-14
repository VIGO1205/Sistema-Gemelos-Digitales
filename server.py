"""Vercel entrypoint for the existing FastAPI application."""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("COPPER_CREEK_LOCAL_MODEL", "true")
os.environ.setdefault("COPPER_CREEK_ARTIFACT_DIR", str(ROOT / "motor_ia_m6" / "model_artifacts"))
os.environ.setdefault("M6_SERVERLESS", "true")

from app.main import app  # noqa: E402
