"""
Agregador de datos para reportes profesionales del Motor IA M-6
Reune benchmark, predicciones, interpretaciones y metadatos en una estructura unificada
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MODELS, BENCHES, MODEL_COLORS, FEATURES
from evaluation.interpretation_engine import InterpretationEngine, InterpretationResult


class ReportDataCollector:
    """
    Recolecta y estructura todos los datos necesarios para generar reportes PDF y Excel.
    Opera principalmente desde st.session_state (datos en memoria del entrenamiento actual).
    """
    
    def __init__(self, bench: int):
        self.bench = bench
        self.timestamp = datetime.now()
        self.data = {}
    
    def collect_all(self, session_state: Dict) -> Dict[str, Any]:
        """
        Recolecta todos los datos disponibles del banco especificado.
        
        Returns:
            Dict con estructura completa lista para reportes
        """
        self.data = {
            'metadata': self._collect_metadata(),
            'benchmark': self._collect_benchmark(session_state),
            'predictions': self._collect_predictions(session_state),
            'interpretations': self._collect_interpretations(session_state),
            'stability': self._collect_stability(session_state),
            'bootstrap': self._collect_bootstrap(session_state),
            'cross_validation': self._collect_cross_validation(session_state),
            'stat_tests': self._collect_stat_tests(session_state),
            'hyperparameters': self._collect_hyperparameters(session_state),
        }
        return self.data
    
    def _collect_metadata(self) -> Dict[str, Any]:
        """Metadatos del experimento"""
        import platform
        
        return {
            'bench': self.bench,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'date': self.timestamp.strftime('%Y-%m-%d'),
            'time': self.timestamp.strftime('%H:%M:%S'),
            'system': platform.system(),
            'python_version': platform.python_version(),
            'features_used': FEATURES,
            'n_features': len(FEATURES),
            'motor_version': 'M-6 IA v1.0',
            'methodology': 'CRISP-DM',
        }
    
    def _collect_benchmark(self, session_state: Dict) -> Optional[pd.DataFrame]:
        """Resultados de benchmark de los 5 modelos"""
        bench_key = f"benchmark_{self.bench}"
        
        if bench_key not in session_state:
            return None
        
        results = session_state[bench_key]
        rows = []
        
        for name, metrics in results.items():
            rows.append({
                'model_key': name,
                'model_name': MODELS[name]['name'],
                'model_type': MODELS[name]['type'],
                'rmse': metrics.get('rmse', np.nan),
                'mae': metrics.get('mae', np.nan),
                'r2': metrics.get('r2', np.nan),
                'mape': metrics.get('mape', np.nan),
                'bias': metrics.get('bias', np.nan),
                'uncertainty': metrics.get('uncertainty', np.nan),
                'composite_score': metrics.get('composite_score', np.nan),
            })
        
        df = pd.DataFrame(rows)
        # Agregar ranking
        df['rank'] = df['composite_score'].rank(ascending=False).astype(int)
        df['is_winner'] = df['rank'] == 1
        
        return df
    
    def _collect_predictions(self, session_state: Dict) -> Optional[Dict[str, Any]]:
        """Predicciones detalladas por modelo"""
        pred_key = f"predictions_{self.bench}"
        
        if pred_key not in session_state:
            return None
        
        predictions = session_state[pred_key]
        
        # Crear DataFrame consolidado con todos los modelos
        # Usamos el primer modelo como base para y_true
        first_model = list(predictions.keys())[0]
        y_true = predictions[first_model]['y_true']
        n = len(y_true)
        
        df_preds = pd.DataFrame({
            'sample_id': [f'SMP_{i:04d}' for i in range(n)],
            'actual_cu': y_true,
        })
        
        for name, preds in predictions.items():
            df_preds[f'pred_{name}'] = preds['y_pred']
            df_preds[f'residual_{name}'] = preds['residuals']
            if 'std' in preds:
                df_preds[f'std_{name}'] = preds['std']
        
        return {
            'dataframe': df_preds,
            'n_samples': n,
            'models': list(predictions.keys())
        }
    
    def _collect_interpretations(self, session_state: Dict) -> Dict[str, Any]:
        """Genera interpretaciones automaticas para el reporte"""
        bench_key = f"benchmark_{self.bench}"
        
        if bench_key not in session_state:
            return {}
        
        results = session_state[bench_key]
        interpretations = {}
        
        # Interpretacion por cada modelo
        for name, metrics in results.items():
            model_name = MODELS[name]['name']
            full_interps = InterpretationEngine.interpret_model_full(metrics, model_name)
            interpretations[name] = [interp.to_dict() for interp in full_interps]
        
        # Interpretacion comparativa global
        df_benchmark = self._collect_benchmark(session_state)
        if df_benchmark is not None:
            comp_interp = InterpretationEngine.interpret_model_comparison(df_benchmark)
            interpretations['__comparison__'] = [comp_interp.to_dict()]
        
        # Interpretacion del ganador
        if df_benchmark is not None:
            winner = df_benchmark.loc[df_benchmark['composite_score'].idxmax()]
            winner_key = [k for k, v in MODELS.items() if v['name'] == winner['model_name']][0]
            rank_interp = InterpretationEngine.interpret_composite_ranking(
                winner['model_name'], winner['composite_score'], rank=1, total_models=len(df_benchmark)
            )
            interpretations['__winner__'] = [rank_interp.to_dict()]
        
        return interpretations
    
    def _collect_stability(self, session_state: Dict) -> Optional[Dict]:
        """Datos de estabilidad (perturbacion de datos)"""
        models_key = f"models_{self.bench}"
        testdata_key = f"testdata_{self.bench}"
        
        if models_key not in session_state or testdata_key not in session_state:
            return None
        
        noise_levels = [0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2]
        models_dict = session_state[models_key]
        X_base = session_state[testdata_key]['X_test']
        y_base = session_state[testdata_key]['y_test']
        
        stability_data = {}
        
        for name, model in models_dict.items():
            rmse_by_noise = []
            for noise in noise_levels:
                X_noisy = X_base + np.random.normal(0, noise, X_base.shape)
                pred_noisy = model.predict(X_noisy)
                mse = np.mean((y_base - pred_noisy) ** 2)
                rmse_by_noise.append(np.sqrt(mse))
            
            interp = InterpretationEngine.interpret_stability(
                noise_levels, rmse_by_noise, MODELS[name]['name']
            )
            
            stability_data[name] = {
                'noise_levels': noise_levels,
                'rmse_by_noise': rmse_by_noise,
                'interpretation': interp.to_dict()
            }
        
        return stability_data
    
    def _collect_cross_validation(self, session_state: Dict) -> Optional[Dict]:
        """Resumen de validacion cruzada repetida (tabla + datos por fold)."""
        cv_key = f"cv_{self.bench}"
        if cv_key not in session_state or not session_state.get(cv_key):
            return None
        
        raw = session_state[cv_key]
        metrics_by_model = raw.get('metrics', {})
        if not metrics_by_model:
            return None
        
        rows = []
        for key, folds in metrics_by_model.items():
            for m in folds:
                rows.append({
                    'model_key': key,
                    'model_name': MODELS.get(key, {}).get('name', key),
                    'fold': m.get('fold', 0),
                    'rmse': m['rmse'],
                    'mae': m['mae'],
                    'r2': m['r2'] if m['r2'] is not None else np.nan,
                })
        df_long = pd.DataFrame(rows)
        df_summary = df_long.groupby('model_name').agg(
            rmse_mean=('rmse', 'mean'), rmse_std=('rmse', 'std'),
            mae_mean=('mae', 'mean'), r2_mean=('r2', 'mean'),
            n_folds=('rmse', 'count')
        ).reset_index()
        df_summary['ci_lower'] = df_summary['rmse_mean'] - 1.96 * df_summary['rmse_std'] / np.sqrt(df_summary['n_folds'])
        df_summary['ci_upper'] = df_summary['rmse_mean'] + 1.96 * df_summary['rmse_std'] / np.sqrt(df_summary['n_folds'])
        
        interpretation = None
        try:
            interp = InterpretationEngine.interpret_cross_validation(df_summary, raw.get('n_total_folds', 0))
            interpretation = interp.to_dict()
        except Exception:
            pass
        
        return {
            'n_splits': raw.get('n_splits', 5),
            'n_repeats': raw.get('n_repeats', 3),
            'n_total_folds': raw.get('n_total_folds', 0),
            'n_rows_used': raw.get('n_rows_used', 0),
            'long': df_long,
            'summary': df_summary,
            'interpretation': interpretation,
        }
    
    def _collect_stat_tests(self, session_state: Dict) -> Optional[Dict]:
        """Pruebas estadisticas robustas (Friedman, Wilcoxon+Bonferroni, bootstrap pareado)."""
        stat_key = f"stat_tests_{self.bench}"
        if stat_key not in session_state or not session_state.get(stat_key):
            return None
        
        stat = session_state[stat_key]
        interpretation = None
        try:
            interp = InterpretationEngine.interpret_statistical_tests(stat)
            interpretation = interp.to_dict()
        except Exception:
            pass
        
        return {**stat, 'interpretation': interpretation}
    
    def _collect_hyperparameters(self, session_state: Dict) -> Optional[Dict]:
        """Resultados de la optimizacion de hiperparametros."""
        hp_key = f"hyperparameters_{self.bench}"
        if hp_key not in session_state or not session_state.get(hp_key):
            return None
        
        raw = session_state[hp_key]
        tuning = raw.get('tuning', {})
        if not tuning:
            return None
        
        rows = []
        for key, r in tuning.items():
            if not isinstance(r, dict) or 'best_rmse' not in r:
                continue
            rows.append({
                'model_key': key,
                'model_name': MODELS.get(key, {}).get('name', key),
                'best_params': str(r.get('best_params', {})),
                'best_rmse': r['best_rmse'],
                'default_rmse': r.get('default_rmse', np.nan),
                'improvement_pct': r.get('improvement_pct', 0.0),
                'n_candidates': r.get('n_candidates', 0),
                'evaluations': r.get('evaluations', []),
            })
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        
        interpretation = None
        try:
            interp = InterpretationEngine.interpret_hyperparameters(raw)
            interpretation = interp.to_dict()
        except Exception:
            pass
        
        return {
            'table': df,
            'used': raw.get('used', {}),
            'interpretation': interpretation,
        }
    
    def _collect_bootstrap(self, session_state: Dict) -> Optional[List[Dict]]:
        """Intervalos de confianza bootstrap"""
        pred_key = f"predictions_{self.bench}"
        
        if pred_key not in session_state:
            return None
        
        predictions = session_state[pred_key]
        bootstrap_results = []
        np.random.seed(42)
        
        for name, preds in predictions.items():
            y_true = preds['y_true']
            y_pred = preds['y_pred']
            n = len(y_true)
            
            rmse_bootstrap = []
            for _ in range(1000):
                idx = np.random.choice(n, n, replace=True)
                y_true_boot = y_true[idx]
                y_pred_boot = y_pred[idx]
                mse = np.mean((y_true_boot - y_pred_boot) ** 2)
                rmse_bootstrap.append(np.sqrt(mse))
            
            rmse_bootstrap = np.array(rmse_bootstrap)
            ci_lower = float(np.percentile(rmse_bootstrap, 2.5))
            ci_upper = float(np.percentile(rmse_bootstrap, 97.5))
            rmse_mean = float(rmse_bootstrap.mean())
            
            interp = InterpretationEngine.interpret_bootstrap_ci(
                rmse_mean, ci_lower, ci_upper, MODELS[name]['name']
            )
            
            bootstrap_results.append({
                'model_key': name,
                'model_name': MODELS[name]['name'],
                'rmse_mean': rmse_mean,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'ci_width': ci_upper - ci_lower,
                'interpretation': interp.to_dict()
            })
        
        return bootstrap_results
    
    def get_winner_info(self) -> Optional[Dict]:
        """Retorna informacion resumida del modelo ganador"""
        benchmark = self.data.get('benchmark')
        if benchmark is None or benchmark.empty:
            return None
        
        winner = benchmark.loc[benchmark['composite_score'].idxmax()]
        return {
            'name': winner['model_name'],
            'type': winner['model_type'],
            'score': winner['composite_score'],
            'rmse': winner['rmse'],
            'r2': winner['r2'],
            'mae': winner['mae'],
            'mape': winner['mape'],
            'bias': winner['bias'],
        }
    
    def has_data(self) -> bool:
        """Verifica si hay datos suficientes para generar un reporte"""
        benchmark = self.data.get('benchmark')
        return benchmark is not None and not benchmark.empty
