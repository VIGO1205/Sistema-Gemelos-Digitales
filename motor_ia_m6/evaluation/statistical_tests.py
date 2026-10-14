"""
Pruebas estadisticas robustas con datos REALES (no simulados).

Fuentes de evidencia:
  A) Matriz de validacion cruzada (fold-RMSE pareado por modelo):
       - Test de Friedman (H0: todos los modelos equivalentes).
       - Wilcoxon pareado entre pares de modelos con correccion Bonferroni.
  B) Predicciones del set de test (residuales reales):
       - Bootstrap pareado de la diferencia de RMSE (ganador vs cada rival),
         con intervalo de confianza al 95%.

Estas pruebas se ejecutan con los residuales observados, a diferencia de la
version previa que fabricaba distribuciones con np.random.normal.
"""

import numpy as np
from scipy import stats


def _as_finite_pairs(a, b):
    """Retorna pares (x, y) donde ambos valores son finitos."""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    mask = np.isfinite(a) & np.isfinite(b)
    return a[mask], b[mask]


def friedman_test(cv_metrics):
    """
    Test de Friedman sobre fold-RMSE por modelo.

    cv_metrics: dict {model_key: [{'rmse': float, ...}, ...]} (folds alineados).
    """
    keys = [k for k in cv_metrics if cv_metrics[k]]
    if len(keys) < 3:
        return {'statistic': None, 'p_value': None, 'significant': None,
                'models': keys, 'n_folds': 0}

    long = max(len(cv_metrics[k]) for k in keys)
    matrix = np.full((len(keys), long), np.nan)
    for i, k in enumerate(keys):
        rmses = [m['rmse'] for m in cv_metrics[k]]
        matrix[i, :len(rmses)] = rmses

    # Solo folds completamente observados (sin NaN) para comparacion pareada justa
    valid = np.all(np.isfinite(matrix), axis=0)
    valid_count = int(valid.sum())
    if valid_count < 2:
        return {'statistic': None, 'p_value': None, 'significant': None,
                'models': keys, 'n_folds': valid_count}

    sub = matrix[:, valid]
    try:
        statistic, p_value = stats.friedmanchisquare(*sub)
    except Exception:
        return {'statistic': None, 'p_value': None, 'significant': None,
                'models': keys, 'n_folds': valid_count}

    return {
        'statistic': float(statistic),
        'p_value': float(p_value),
        'significant': bool(p_value < 0.05),
        'models': keys,
        'n_folds': valid_count,
    }


def pairwise_wilcoxon(cv_metrics, alpha=0.05):
    """
    Wilcoxon signed-rank pareado sobre fold-RMSE + correccion Bonferroni.
    Un p-valor bajo (menor a alpha/n_comparaciones) indica que el modelo con
    menor RMSE mediano es significativamente mejor en pares.
    """
    keys = list(cv_metrics.keys())
    pairs = []
    for i, a in enumerate(keys):
        for j, b in enumerate(keys):
            if j <= i:
                continue
            ra = [m['rmse'] for m in cv_metrics[a]]
            rb = [m['rmse'] for m in cv_metrics[b]]
            x, y = _as_finite_pairs(ra, rb)
            if len(x) < 6:
                res = {'statistic': None, 'p_value': 1.0, 'significant': False}
            elif np.all(x == y):
                res = {'statistic': None, 'p_value': 1.0, 'significant': False}
            else:
                try:
                    stat, p = stats.wilcoxon(x, y)
                    res = {'statistic': float(stat), 'p_value': float(p), 'significant': False}
                except Exception:
                    res = {'statistic': None, 'p_value': 1.0, 'significant': False}
            res['model_a'] = a
            res['model_b'] = b
            res['mean_rmse_a'] = float(np.mean(x)) if len(x) else None
            res['mean_rmse_b'] = float(np.mean(y)) if len(y) else None
            pairs.append(res)

    n_comp = max(1, len(pairs))
    for p in pairs:
        p['bonferroni_alpha'] = alpha / n_comp
        p['significant'] = bool(p.get('p_value') is not None and p['p_value'] < p['bonferroni_alpha'])
    return pairs


def bootstrap_indices(n, rng, groups=None):
    """Resample whole groups, retaining every row and repeated group draws."""
    if groups is None:
        return rng.integers(0, n, size=n)
    groups = np.asarray(groups)
    if groups.ndim != 1 or len(groups) != n:
        raise ValueError('Los grupos deben estar alineados con las predicciones.')
    unique, inverse = np.unique(groups, return_inverse=True)
    if len(unique) < 2:
        raise ValueError('Bootstrap por sondaje requiere al menos dos sondajes.')
    return np.concatenate([np.flatnonzero(inverse == i)
                           for i in rng.integers(0, len(unique), size=len(unique))])


def rmse_bootstrap(y_true, y_pred, groups=None, n_boot=1000, seed=42):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    if y_true.shape != y_pred.shape or not np.isfinite([y_true, y_pred]).all():
        raise ValueError('Bootstrap requiere vectores finitos y alineados.')
    rng = np.random.default_rng(seed)
    errors = (y_true - y_pred) ** 2
    samples = [np.sqrt(errors[bootstrap_indices(len(errors), rng, groups)].mean())
               for _ in range(n_boot)]
    lower, upper = np.percentile(samples, [2.5, 97.5])
    return {'rmse_mean': float(np.mean(samples)), 'ci_lower': float(lower),
            'ci_upper': float(upper), 'unit': 'sondaje' if groups is not None else 'fila'}


def paired_rmse_bootstrap(y_true, pred_a, pred_b, n_boot=2000, seed=42, groups=None):
    """
    Bootstrap pareado de la diferencia de RMSE: rmse_a - rmse_b.
    Remuestrea las mismas observaciones para ambos modelos (comparacion pareada).

    Returns:
        dict con diff_mean, ci_lower, ci_upper; IC totalmente negativo favorece a A.
    """
    y_true = np.asarray(y_true, dtype=float)
    pred_a = np.asarray(pred_a, dtype=float)
    pred_b = np.asarray(pred_b, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(pred_a) & np.isfinite(pred_b)
    if groups is not None:
        groups = np.asarray(groups)
        if groups.shape != y_true.shape:
            raise ValueError('Grupos y predicciones no están alineados.')
        groups = groups[mask]
    y_true, pred_a, pred_b = y_true[mask], pred_a[mask], pred_b[mask]
    n = len(y_true)
    if n < 10:
        return {'diff_mean': None, 'ci_lower': None, 'ci_upper': None, 'significant': None}

    mse_a = (y_true - pred_a) ** 2
    mse_b = (y_true - pred_b) ** 2
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = bootstrap_indices(n, rng, groups)
        diffs[i] = np.sqrt(mse_a[idx].mean()) - np.sqrt(mse_b[idx].mean())

    ci_lower, ci_upper = np.nanpercentile(diffs, [2.5, 97.5])
    return {
        'diff_mean': float(np.nanmean(diffs)),
        'ci_lower': float(ci_lower),
        'ci_upper': float(ci_upper),
        'significant': bool(ci_lower > 0 or ci_upper < 0),
        'unit': 'sondaje' if groups is not None else 'fila',
        'n_units': int(len(np.unique(groups))) if groups is not None else n,
    }


def run_statistical_analysis(test_predictions, cv_metrics=None, winner=None,
                             n_boot=2000, seed=42, groups=None):
    """
    Ejecuta el bloque completo de pruebas estadisticas.

    Args:
        test_predictions: {model_key: {'y_true':..., 'y_pred':...}} (set de test).
        cv_metrics: dict de fold metrics por modelo (de repeated_kfold_cv['metrics']).
        winner: model_key del ganador por score compuesto.

    Returns:
        dict con 'friedman', 'wilcoxon', 'bootstrap'.
    """
    result = {'friedman': {}, 'wilcoxon': [], 'bootstrap': []}
    if cv_metrics:
        result['friedman'] = friedman_test(cv_metrics)
        result['wilcoxon'] = pairwise_wilcoxon(cv_metrics)

    if winner and winner in test_predictions:
        wins = test_predictions[winner]
        for name, preds in test_predictions.items():
            if name == winner:
                continue
            boot = paired_rmse_bootstrap(wins['y_true'], wins['y_pred'],
                                         preds['y_pred'], n_boot=n_boot, seed=seed,
                                         groups=groups)
            if boot['diff_mean'] is None:
                continue
            boot['winner'] = winner
            boot['rival'] = name
            result['bootstrap'].append(boot)
    return result
