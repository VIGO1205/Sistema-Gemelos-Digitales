"""
Configuracion global del Motor IA M-6
Gemelo Digital Predictivo para Control de Ley en Mineria a Cielo Abierto
"""

import os
from pathlib import Path

# Rutas base
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Base de datos PostgreSQL
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "m6_gemelo_digital"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# Parametros de entrenamiento
TRAIN_CONFIG = {
    "test_size": 0.15,
    "val_size": 0.15,
    "random_state": 42,
    "n_splits_cv": 5,
    "n_splits_cv_repeated": 5,
    "n_repeats": 3,
    # Validacion cruzada (RepeatedKFold) sobre train+val
    "cv_enabled": True,
    "cv_max_points": 3000,
    # Optimizacion de hiperparametros por rejilla (validation set)
    "tuning_enabled": True,
    "tuning_max_points": 3000,
    "tuning_n_candidates": 15,
}

# Metricas y pesos para score compuesto
METRICS_CONFIG = {
    "rmse": {"weight": 0.25, "direction": "min"},
    "mae": {"weight": 0.20, "direction": "min"},
    "r2": {"weight": 0.20, "direction": "max"},
    "mape": {"weight": 0.15, "direction": "min"},
    "bias": {"weight": 0.10, "direction": "min"},
    "uncertainty": {"weight": 0.10, "direction": "min"},
}

# Modelos a entrenar
MODELS = {
    "kriging": {
        "name": "Ordinary Kriging",
        "type": "CLASSIC",
        "enabled": True,
    },
    "random_forest": {
        "name": "Random Forest",
        "type": "CLASSIC",
        "enabled": True,
    },
    "xgboost": {
        "name": "XGBoost",
        "type": "CLASSIC",
        "enabled": True,
    },
    "stacking": {
        "name": "Stacking Ensemble",
        "type": "HYBRID",
        "enabled": True,
    },
    "nn_bayesian": {
        "name": "NN + Bayesian Kriging",
        "type": "HYBRID",
        "enabled": True,
    },
}

# Variables del modelo — SOLO features que NO contienen el target (plant_feed_grade)
# Eliminadas por data leakage: krig_error, bayes_error, krig_residual,
# distance_to_fault, distance_to_contact, swir_alteration_index,
# blasthole_density, epistemic_unc, rock_type_encoded, alteration_encoded, y
FEATURES = [
    "x",
    "z",
    "cu_base",
    "predicted_bayesian",
    "tonnage_norm",
    "days_from_start",
    "prev_grade_avg",
]

TARGET = "cu_bayesian"

# Bancos operativos
BENCHES = [3260, 3245, 3230, 3215, 3200, 3185, 3170, 3155, 3140, 3125]

# Colores para visualizacion
MODEL_COLORS = {
    "kriging": "#94a3b8",
    "random_forest": "#10b981",
    "xgboost": "#0284c7",
    "stacking": "#f59e0b",
    "nn_bayesian": "#8b5cf6",
}

# Umbrales de alerta
THRESHOLDS = {
    "rmse_max": 5.0,
    "r2_min": 0.85,
    "mape_max": 9.0,
    "bias_max": 0.35,
}
