"""
Validacion cruzada repetida (RepeatedKFold) para comparacion robusta de modelos.

Se evalúan TODOS los modelos sobre los MISMOS splits, generando una matriz
modelos x folds con RMSE/MAE/R2. Ese diseno pareado habilita pruebas
estadisticas robustas (Friedman, Wilcoxon pareado + Bonferroni, bootstrap
pareado) sin necesidad de muestreos sinteticos.

Referencia metodologica: Bergmeir & Benitez (2012), repeated-CV para
comparacion estadistica de modelos.
"""

import numpy as np
from sklearn.model_selection import RepeatedKFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from models.baseline_kriging import KrigingModel
from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel
from models.stacking_ensemble import StackingEnsemble
from models.nn_bayesian import NNBayesianKriging


def _fold_metrics(y_true, y_pred):
    """Metricas por fold (introduce None en R2 si no es finito)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    with np.errstate(invalid='ignore', divide='ignore'):
        r2 = r2_score(y_true, y_pred)
    if not np.isfinite(r2):
        r2 = None
    else:
        r2 = float(np.clip(r2, -10.0, 1.0))
    return {
        'rmse': float(np.sqrt(mean_squared_error(y_true, y_pred))),
        'mae': float(mean_absolute_error(y_true, y_pred)),
        'r2': r2,
    }


def _make_model(key):
    """Instancia un modelo con los mismos parametros que usa el pipeline final."""
    if key == 'kriging':
        return KrigingModel(variogram_model='spherical', n_closest_points=300)
    if key == 'random_forest':
        return RandomForestModel(n_estimators=200, max_depth=15)
    if key == 'xgboost':
        return XGBoostModel(n_estimators=200, max_depth=8)
    if key == 'stacking':
        return StackingEnsemble(rf_n_estimators=150, xgb_n_estimators=150)
    if key == 'nn_bayesian':
        return NNBayesianKriging(hidden_dims=[128, 64, 32], epochs=100, learning_rate=0.001)
    raise ValueError(f"Modelo desconocido para CV: {key}")


def repeated_kfold_cv(X, y, model_keys, n_splits=5, n_repeats=3,
                      random_state=42, max_points=None, verbose=False):
    """
    Corre validacion cruzada repetida para los modelos indicados.

    Returns:
        dict con:
          - 'n_splits', 'n_repeats', 'n_total_folds'
          - 'n_rows_used'
          - 'metrics': {model_key: [ {'fold': int, 'rmse':.., 'mae':.., 'r2':..} ]}
    """
    n = len(y)
    use = n
    if max_points and n > max_points:
        rng = np.random.default_rng(random_state)
        idx = rng.choice(n, size=max_points, replace=False)
        X = X[idx]
        y = y[idx]
        use = max_points
        if verbose:
            print(f"  CV submuestreado de {n} a {use} puntos para mantener el costo acotado")

    if use < max(n_splits, 8):
        raise ValueError(f"Pocos datos para validacion cruzada: {use} muestras")

    rkf = RepeatedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=random_state)
    splits = list(rkf.split(X, y))

    results = {k: [] for k in model_keys}
    total = len(splits)

    for rep_i, (train_idx, test_idx) in enumerate(splits):
        fold_no = rep_i + 1
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        if verbose:
            print(f"  Fold {fold_no}/{total} (train={len(y_tr)}, test={len(y_te)})")

        for key in model_keys:
            try:
                model = _make_model(key)
                if key == 'kriging':
                    model.fit(X_tr[:, :2], y_tr)
                    pred = model.predict(X_te[:, :2])
                elif key == 'nn_bayesian':
                    model.run_feature_importance = False  # acelerar CV (sin permutation)
                    model.fit(X_tr, y_tr)
                    pred = model.predict(X_te)
                else:
                    model.fit(X_tr, y_tr)
                    pred = model.predict(X_te)
                m = _fold_metrics(y_te, pred)
            except Exception as e:
                if verbose:
                    print(f"    {key} fold {fold_no}: error -> {e}")
                m = {'rmse': float('nan'), 'mae': float('nan'), 'r2': None}
            m['fold'] = fold_no
            m['model'] = key
            results[key].append(m)

    return {
        'n_splits': n_splits,
        'n_repeats': n_repeats,
        'n_total_folds': total,
        'n_rows_used': use,
        'metrics': results,
    }