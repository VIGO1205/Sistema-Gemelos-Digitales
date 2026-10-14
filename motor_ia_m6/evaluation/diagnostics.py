"""Reproducible diagnostics that do not silently mix fitted model states."""
import numpy as np


def stability_curve(model, X, y, reference, noise_levels, repeats=5, seed=42):
    X, y, reference = np.asarray(X), np.asarray(y), np.asarray(reference)
    baseline = np.asarray(model.predict(X)).reshape(-1)
    if baseline.shape != reference.shape or not np.allclose(baseline, reference, rtol=1e-6, atol=1e-8):
        raise ValueError('La predicción actual difiere de la evaluación guardada. '
                         'Reentrena este modelo para evaluar su estabilidad sin mezclar estados.')
    rng = np.random.default_rng(seed)
    means, deviations = [], []
    for level in noise_levels:
        if level == 0:
            errors = [float(np.sqrt(np.mean((y - baseline) ** 2)))]
        else:
            errors = [float(np.sqrt(np.mean((y - model.predict(
                X + rng.normal(0, level, X.shape))) ** 2))) for _ in range(repeats)]
        means.append(float(np.mean(errors)))
        deviations.append(float(np.std(errors)))
    return {'rmse': means, 'std': deviations, 'repeats': repeats, 'seed': seed}
