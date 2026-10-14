"""
Optimizacion de hiperparametros por rejilla evaluada sobre el set de validacion.

Modelos tuneados: RandomForest, XGBoost, NN+Bayesian (Kriging y Stacking usan
defaults documentados, ya que su costo reentrenable hace el barrido impráctico).

Para acotar el costo, los datos se submuestrean (max_points) y se evalúa un
subconjunto aleatorio de candidatos (n_candidates). El resultado incluye la
curva de desempeno (val-RMSE por candidato) para graficar y reportar.
"""

import time
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel
from models.nn_bayesian import NNBayesianKriging

RF_GRID = [
    {'n_estimators': ne, 'max_depth': md, 'min_samples_split': mss}
    for ne in (100, 200, 300)
    for md in (10, 15, 20)
    for mss in (2, 5, 10)
]

XGB_GRID = [
    {'n_estimators': ne, 'max_depth': md, 'learning_rate': lr}
    for ne in (100, 200, 300)
    for md in (6, 8, 10)
    for lr in (0.05, 0.1)
]

NN_GRID = [
    {'epochs': e, 'learning_rate': lr}
    for e in (60, 100)
    for lr in (5e-4, 1e-3, 2e-3)
]

DEFAULTS = {
    'random_forest': {'n_estimators': 200, 'max_depth': 15},
    'xgboost': {'n_estimators': 200, 'max_depth': 8},
    'nn_bayesian': {'epochs': 100, 'learning_rate': 0.001},
}


def _sample_candidates(grid, n, seed=42):
    if len(grid) <= n:
        return list(grid)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(grid), size=n, replace=False)
    return [grid[i] for i in idx]


def _score(y_true, y_pred):
    with np.errstate(invalid='ignore', divide='ignore'):
        r2 = r2_score(y_true, y_pred)
    return {
        'val_rmse': float(np.sqrt(mean_squared_error(y_true, y_pred))),
        'val_mae': float(mean_absolute_error(y_true, y_pred)),
        'val_r2': float(r2) if np.isfinite(r2) else None,
    }


def _eval_rf(params, X, y, groups=None, spatial_dims=2):
    model = RandomForestModel(random_state=42, **params)
    model.fit(X, y)
    return model


def _eval_xgb(params, X, y, groups=None, spatial_dims=2):
    model = XGBoostModel(random_state=42, **params)
    model.fit(X, y)
    return model


def _eval_nn(params, X, y, groups=None, spatial_dims=2):
    model = NNBayesianKriging(hidden_dims=[128, 64, 32], run_feature_importance=False,
                              spatial_dims=spatial_dims, **params)
    model.fit(X, y, groups=groups)
    return model


_EVAL = {
    'random_forest': _eval_rf,
    'xgboost': _eval_xgb,
    'nn_bayesian': _eval_nn,
}


def _tune_model(key, X_train, y_train, X_val, y_val, n_candidates, seed=42,
                verbose=True, groups=None, spatial_dims=2):
    grid = {'random_forest': RF_GRID, 'xgboost': XGB_GRID, 'nn_bayesian': NN_GRID}[key]
    candidates = _sample_candidates(grid, n_candidates, seed)

    default_params = DEFAULTS[key]
    default_model = _EVAL[key](default_params, X_train, y_train,
                                groups=groups, spatial_dims=spatial_dims)
    default_scores = _score(y_val, default_model.predict(X_val))
    default_rmse = default_scores['val_rmse']

    best_params = default_params
    best_rmse = default_rmse
    evaluations = [{'params': dict(default_params), 'val_rmse': default_rmse,
                    'val_mae': default_scores['val_mae'], 'val_r2': default_scores['val_r2'],
                    'is_default': True}]

    for cand in candidates:
        t0 = time.time()
        try:
            model = _EVAL[key](cand, X_train, y_train,
                                groups=groups, spatial_dims=spatial_dims)
            scores = _score(y_val, model.predict(X_val))
            del model
        except Exception as e:
            if verbose:
                print(f"    {key} candidato {cand} fallo: {e}")
            continue
        scores['params'] = dict(cand)
        scores['is_default'] = False
        scores['time_s'] = time.time() - t0
        evaluations.append(scores)
        if scores['val_rmse'] < best_rmse:
            best_rmse = scores['val_rmse']
            best_params = dict(cand)

    evaluations.sort(key=lambda e: e['val_rmse'])
    return {
        'model': key,
        'best_params': best_params,
        'best_rmse': float(best_rmse),
        'default_rmse': float(default_rmse),
        'improvement_pct': float((default_rmse - best_rmse) / default_rmse * 100),
        'n_candidates': len(evaluations),
        'evaluations': evaluations,
    }


def tune_all(X_train, y_train, X_val, y_val, models_to_tune,
             max_points=3000, n_candidates=15, seed=42, verbose=True,
             groups=None, spatial_dims=2):
    """
    Tunea los modelos solicitados y retorna dict con resultados por modelo.
    Submuestrea train/val si superan max_points para acotar el costo.
    """
    # Submuestreo consistente (mismo seed -> rows alineadas train/val)
    n_tr = len(y_train)
    rng = np.random.default_rng(seed)
    if max_points and n_tr > max_points:
        tr_idx = rng.choice(n_tr, size=max_points, replace=False)
        X_train = X_train[tr_idx]
        y_train = y_train[tr_idx]
        if groups is not None:
            groups = np.asarray(groups)[tr_idx]
    n_va = len(y_val)
    if max_points and n_va > max_points:
        va_idx = rng.choice(n_va, size=max_points, replace=False)
        X_val = X_val[va_idx]
        y_val = y_val[va_idx]

    results = {}
    for key in models_to_tune:
        if key not in _EVAL:
            continue
        if verbose:
            print(f"  Tuneando {key} ...")
        t0 = time.time()
        results[key] = _tune_model(key, X_train, y_train, X_val, y_val,
                                   n_candidates, seed=seed, verbose=verbose,
                                   groups=groups, spatial_dims=spatial_dims)
        if verbose:
            best = results[key]
            print(f"    {key}: mejor val-RMSE {best['best_rmse']:.4f} "
                  f"(default {best['default_rmse']:.4f}, mejora {best['improvement_pct']:.1f}%) "
                  f"[{time.time()-t0:.0f}s]")
    return results
