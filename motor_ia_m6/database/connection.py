"""
Conexion a PostgreSQL para el Motor IA M-6
"""

import os
import numpy as np
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import pandas as pd
from config import DB_CONFIG

# Forzar encoding UTF-8 para psycopg2
os.environ['PGCLIENTENCODING'] = 'utf8'


# Cache en memoria para cuando PostgreSQL no está disponible
_in_memory_benchmark = {}
_in_memory_predictions = {}
_in_memory_active_models = {}


@contextmanager
def get_connection():
    """Context manager para conexiones a PostgreSQL"""
    conn = None
    try:
        # Conectar con codificacion UTF-8 explicita
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            client_encoding='utf8'
        )
        yield conn
    except UnicodeDecodeError as e:
        print(f"⚠️ Error de codificacion UTF-8: {e}")
        print("   PostgreSQL no disponible. Usando almacenamiento en memoria.")
        raise ConnectionError("PostgreSQL no accesible")
    except Exception as e:
        print(f"⚠️ PostgreSQL no disponible: {e}")
        raise ConnectionError("PostgreSQL no accesible")
    finally:
        if conn is not None:
            conn.close()


@contextmanager
def get_cursor():
    """Context manager para cursores con diccionarios"""
    with get_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()


def fetch_dataframe(query: str, params=None) -> pd.DataFrame:
    """Ejecuta query y retorna DataFrame de pandas"""
    try:
        with get_connection() as conn:
            return pd.read_sql(query, conn, params=params)
    except ConnectionError:
        return pd.DataFrame()


def execute_query(query: str, params=None) -> list:
    """Ejecuta query y retorna lista de diccionarios"""
    try:
        with get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    except ConnectionError:
        return []


def insert_benchmark_result(model_name, model_type, bench, metrics, hyperparams=None):
    """Inserta resultado de benchmark"""
    try:
        query = """
            INSERT INTO benchmark_models 
            (model_name, model_type, bench, rmse, mae, r2, mape, bias, uncertainty, composite_score, hyperparameters)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            model_name, model_type, bench,
            metrics.get('rmse'), metrics.get('mae'), metrics.get('r2'),
            metrics.get('mape'), metrics.get('bias'), metrics.get('uncertainty'),
            metrics.get('composite_score'),
            hyperparams or {}
        )
        with get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()['id']
    except ConnectionError:
        # Fallback a memoria
        if bench not in _in_memory_benchmark:
            _in_memory_benchmark[bench] = []
        _in_memory_benchmark[bench].append({
            'model_name': model_name,
            'model_type': model_type,
            'bench': bench,
            **metrics,
            'hyperparameters': hyperparams or {}
        })
        return None


def insert_predictions(df: pd.DataFrame, model_name: str, bench: int):
    """Inserta predicciones en batch"""
    try:
        query = """
            INSERT INTO model_predictions 
            (model_name, bench, block_id, x, y, z, predicted_cu, actual_cu, residual, p10, p50, p90)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                for _, row in df.iterrows():
                    cur.execute(query, (
                        model_name, bench,
                        row.get('block_id'),
                        row.get('x'), row.get('y'), row.get('z'),
                        row.get('predicted'),
                        row.get('actual'),
                        row.get('residual'),
                        row.get('p10'), row.get('p50'), row.get('p90')
                    ))
                conn.commit()
    except ConnectionError:
        # Fallback a memoria
        key = f"{bench}_{model_name}"
        _in_memory_predictions[key] = df.to_dict('records')


def get_active_model(bench: int) -> dict:
    """Obtiene el modelo activo para un banco"""
    try:
        query = """
            SELECT * FROM active_models 
            WHERE bench = %s AND is_current = TRUE
        """
        result = execute_query(query, (bench,))
        return dict(result[0]) if result else None
    except ConnectionError:
        # Fallback a memoria
        return _in_memory_active_models.get(bench)


def get_benchmark_results(bench: int) -> pd.DataFrame:
    """Obtiene resultados de benchmark para un banco"""
    try:
        query = """
            SELECT * FROM benchmark_models 
            WHERE bench = %s
            ORDER BY composite_score DESC
        """
        return fetch_dataframe(query, (bench,))
    except ConnectionError:
        # Fallback a memoria
        if bench in _in_memory_benchmark:
            return pd.DataFrame(_in_memory_benchmark[bench])
        return pd.DataFrame()


def clear_benchmark_for_bench(bench: int):
    """Limpia resultados anteriores de un banco"""
    try:
        queries = [
            "DELETE FROM benchmark_models WHERE bench = %s",
            "DELETE FROM model_predictions WHERE bench = %s",
        ]
        with get_connection() as conn:
            with conn.cursor() as cur:
                for q in queries:
                    cur.execute(q, (bench,))
                conn.commit()
    except ConnectionError:
        # Limpiar memoria
        if bench in _in_memory_benchmark:
            del _in_memory_benchmark[bench]


import requests

# URL del backend API para activar modelos (evita bug psycopg2 en Python 3.13 Windows)
# En Docker (servicio motor_ia/serving) se sobreescribe con http://backend:8000
API_BASE_URL = os.getenv("MOTOR_API_BASE_URL", "http://localhost:8000")

def activate_model(bench: int, model_name: str, composite_score: float,
                   rmse: float = None, r2: float = None, mae: float = None,
                   mape: float = None, bias: float = None):
    """Activa un modelo como ganador via HTTP API del backend (evita bug psycopg2)."""
    try:
        payload = {
            "bench": bench,
            "model_name": model_name,
            "composite_score": composite_score,
            "rmse": rmse,
            "r2": r2,
            "mae": mae,
            "mape": mape,
            "bias": bias,
        }
        resp = requests.post(
            f"{API_BASE_URL}/api/models/activate",
            json=payload,
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        # Fallback a memoria si la API no responde
        _in_memory_active_models[bench] = {
            'bench': bench,
            'model_name': model_name,
            'composite_score': composite_score,
            'rmse': rmse,
            'r2': r2,
            'mae': mae,
            'mape': mape,
            'bias': bias,
            'is_current': True
        }
        return {"success": False, "message": "API no disponible. Guardado en memoria local."}


def fetch_real_plant_data(bench: int = None, project_id: int = 4):
    """Carga datos reales de planta desde el backend API.
    
    Usa el endpoint /api/process-control/export para obtener los datos
    que luego se usan en reconciliación.
    
    Features creadas a partir de datos REALES (no aleatorios):
    - cu_base: predicción del kriging (feature principal)
    - predicted_bayesian: predicción bayesiana previa
    - krig_error: error histórico del kriging (cu_bayesian - cu_base)
    - bayes_error: error histórico del bayesiano
    - tonnage_norm: tonelaje normalizado
    - days_from_start: días desde la primera voladura
    - prev_grade_avg: promedio móvil de leyes anteriores
    """
    import pandas as pd
    try:
        url = f"{API_BASE_URL}/api/process-control/export?project_id={project_id}"
        if bench is not None:
            url += f"&bench={bench}"
        
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get('success') and result.get('data'):
            df = pd.DataFrame(result['data'])
            
            # Ordenar cronológicamente para calcular tendencias
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Target: ley real de planta (NO se usa como feature)
            df['cu_bayesian'] = df['plant_feed_grade']
            
            # Feature principal: predicción del kriging (NO usa target)
            df['cu_base'] = df['predicted_base_krig']
            
            # Feature: predicción bayesiana previa (NO usa target)
            df['predicted_bayesian'] = df['predicted_bayesian']
            
            # Feature: tonelaje normalizado (NO usa target)
            df['tonnage_norm'] = (df['tonnage'] - df['tonnage'].mean()) / df['tonnage'].std()
            
            # Feature: días desde el inicio (NO usa target)
            min_date = df['timestamp'].min()
            df['days_from_start'] = (df['timestamp'] - min_date).dt.days
            
            # Feature: promedio móvil de leyes ANTERIORES únicamente (no usa target actual)
            # shift(1) asegura que no veamos el valor actual
            # fillna(0) evita usar la media global que sí contiene información futura
            df['prev_grade_avg'] = df['plant_feed_grade'].shift(1).expanding().mean().fillna(0.0)
            
            # Features espaciales básicas (NO usan target)
            df['x'] = df['bench'] * 10 + df['days_from_start'] * 0.5
            df['z'] = df['bench']
            
            # NOTA: Las siguientes features fueron eliminadas por DATA LEAKAGE:
            # - krig_error, bayes_error, krig_residual: son target - predicción
            # - distance_to_fault, distance_to_contact, swir_alteration_index,
            #   blasthole_density, epistemic_unc: calculadas directamente del target
            # - rock_type, alteration: inferidas del target
            # - y: calculada usando krig_error que depende del target
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error cargando datos reales: {e}")
        return pd.DataFrame()


def send_predictions_to_api(bench: int, model_name: str, predictions: list):
    """Envia predicciones del modelo ganador al backend via HTTP API."""
    try:
        preds_float = [float(p) for p in predictions]
        print(f"[send_predictions_to_api] bench={bench}, model={model_name}, n_preds={len(preds_float)}")
        print(f"[send_predictions_to_api] pred stats: min={min(preds_float):.4f}, mean={sum(preds_float)/len(preds_float):.4f}, max={max(preds_float):.4f}")
        print(f"[send_predictions_to_api] primeras 5: {preds_float[:5]}")
        
        payload = {
            "bench": bench,
            "model_name": model_name,
            "predictions": preds_float
        }
        resp = requests.post(
            f"{API_BASE_URL}/api/reconciliation/predictions",
            json=payload,
            timeout=15
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"[send_predictions_to_api] respuesta backend: {result}")
        return result
    except Exception as e:
        print(f"[send_predictions_to_api] ERROR: {e}")
        return {"success": False, "message": f"Error enviando predicciones: {str(e)}"}
