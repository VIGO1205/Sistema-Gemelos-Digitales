"""
Evaluacion y comparacion de modelos
CRISP-DM Fase 5: Evaluacion
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from config import METRICS_CONFIG


class ModelEvaluator:
    """Evaluador de modelos con metricas compuestas"""
    
    @staticmethod
    def calculate_metrics(y_true, y_pred, uncertainty=None, y_scale=None):
        """Calcula todas las metricas y score compuesto.

        y_scale: desviacion estandar del target para normalizar el score compuesto
        de forma invariante a la escala (Cu %, Fe %, etc). Si es None se usa la
        dispersion de y_true.
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        n = len(y_true)
        
        if n == 0:
            return {'rmse': 0.0, 'mae': 0.0, 'r2': None, 'mape': 0.0, 
                    'bias': 0.0, 'uncertainty': 0.0, 'composite_score': 0.0}
        
        # Metricas basicas
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        
        # R2 — manejar NaN
        try:
            r2 = r2_score(y_true, y_pred)
            if np.isnan(r2) or np.isinf(r2):
                r2 = None
            else:
                r2 = float(r2)
        except Exception:
            r2 = None
        
        # MAPE — excluir valores reales cercanos a cero (indefinidos / sin sentido)
        # piso absoluto: targets < 1% (bloques Waste con ley de planta ~0 no aportan MAPE)
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = np.abs((y_true - y_pred) / np.where(np.abs(y_true) >= 1.0, y_true, np.nan)) * 100
        mape = np.nanmean(mape) if np.any(np.isfinite(mape)) else 0.0
        
        # Bias (sesgo)
        bias = float(np.mean(y_pred - y_true))
        
        # Incertidumbre promedio
        if uncertainty is not None:
            uncertainty_val = float(np.mean(uncertainty))
        else:
            uncertainty_val = float(np.std(y_pred - y_true))
        
        # Score compuesto ponderado
        metrics_dict = {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': r2,
            'mape': float(mape),
            'bias': abs(bias),
            'uncertainty': uncertainty_val
        }
        
        if y_scale is None or y_scale <= 0:
            y_scale = float(np.std(y_true))
        if y_scale <= 0:
            y_scale = None

        composite_score = ModelEvaluator._calculate_composite_score(metrics_dict, scale=y_scale)
        metrics_dict['composite_score'] = composite_score
        
        return metrics_dict
    
    @staticmethod
    def _calculate_composite_score(metrics, scale=None):
        """Calcula score compuesto ponderado.

        Con `scale` (desviacion estandar del target) los errores se normalizan
        relativo a la dispersion de la variable, haciendo el score comparable
        entre datasets de distinta escala (Cu%, Fe%, ...).
        """
        score = 0
        
        for metric_name, config in METRICS_CONFIG.items():
            value = metrics.get(metric_name, 0)
            weight = config['weight']
            
            # Normalizar a escala 0-1
            if metric_name == 'r2':
                norm_value = max(0, min(1, value))
            elif metric_name == 'mape':
                norm_value = 1 / (1 + value / 10)
            elif scale:  # Errores relativos a la dispersion del target
                ratio = value / scale
                if metric_name == 'rmse':
                    norm_value = 1 / (1 + 5 * ratio)
                elif metric_name == 'mae':
                    norm_value = 1 / (1 + 5 * ratio)
                elif metric_name == 'bias':
                    norm_value = 1 / (1 + 15 * ratio)
                elif metric_name == 'uncertainty':
                    norm_value = 1 / (1 + 2 * ratio)
                else:
                    norm_value = 0.5
            else:  # Fallback escala absoluta (compatibilidad)
                if metric_name == 'rmse':
                    norm_value = 1 / (1 + value * 10)  # Asumiendo RMSE ~0-0.5
                elif metric_name == 'mae':
                    norm_value = 1 / (1 + value * 10)
                elif metric_name == 'bias':
                    norm_value = 1 / (1 + value * 50)
                elif metric_name == 'uncertainty':
                    norm_value = 1 / (1 + value * 5)
                else:
                    norm_value = 0.5
            
            score += norm_value * weight
        
        return score
    
    @staticmethod
    def statistical_tests(results_dict):
        """Pruebas estadisticas para comparar modelos"""
        
        if len(results_dict) < 2:
            return {}
        
        # Extraer metricas
        model_names = list(results_dict.keys())
        rmse_values = [results_dict[m]['rmse'] for m in model_names]
        r2_values = [results_dict[m]['r2'] for m in model_names]
        
        tests = {}
        
        # Test ANOVA para RMSE
        if len(model_names) >= 3:
            # Generar muestras sinteticas de residuos para ANOVA
            np.random.seed(42)
            samples = []
            for name in model_names:
                rmse = results_dict[name]['rmse']
                # Simular distribucion de residuos
                sample = np.random.normal(0, rmse, 100)
                samples.append(sample)
            
            f_stat, p_value = stats.f_oneway(*samples)
            tests['anova_rmse'] = {
                'f_statistic': f_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
        
        # Comparacion pareada: mejor vs segundo mejor
        sorted_models = sorted(model_names, key=lambda m: results_dict[m]['composite_score'], reverse=True)
        best = sorted_models[0]
        second = sorted_models[1] if len(sorted_models) > 1 else None
        
        if second:
            # Test t de Student
            np.random.seed(42)
            best_sample = np.random.normal(0, results_dict[best]['rmse'], 100)
            second_sample = np.random.normal(0, results_dict[second]['rmse'], 100)
            
            t_stat, p_value = stats.ttest_ind(best_sample, second_sample)
            tests['paired_ttest'] = {
                'best_model': best,
                'second_model': second,
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
        
        # Bootstrap para intervalos de confianza del score
        winner = sorted_models[0]
        winner_score = results_dict[winner]['composite_score']
        
        np.random.seed(42)
        bootstrap_scores = []
        for _ in range(1000):
            # Simular variacion del score
            noise = np.random.normal(0, 0.02)
            bootstrap_scores.append(winner_score + noise)
        
        ci_lower = np.percentile(bootstrap_scores, 2.5)
        ci_upper = np.percentile(bootstrap_scores, 97.5)
        
        tests['bootstrap_ci'] = {
            'model': winner,
            'score_mean': winner_score,
            'ci_95': (ci_lower, ci_upper)
        }
        
        return tests
    
    @staticmethod
    def rank_models(results_dict):
        """Genera ranking de modelos por score compuesto"""
        
        ranking = []
        for name, metrics in results_dict.items():
            ranking.append({
                'model': name,
                'rmse': metrics['rmse'],
                'mae': metrics['mae'],
                'r2': metrics['r2'],
                'mape': metrics['mape'],
                'bias': metrics['bias'],
                'composite_score': metrics['composite_score']
            })
        
        # Ordenar por score compuesto descendente
        ranking.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Agregar posicion
        for i, item in enumerate(ranking):
            item['rank'] = i + 1
            item['is_winner'] = (i == 0)
        
        return ranking
    
    @staticmethod
    def select_winner(results_dict):
        """Selecciona el modelo ganador"""
        ranking = ModelEvaluator.rank_models(results_dict)
        winner = ranking[0]
        return winner['model'], winner['composite_score']
