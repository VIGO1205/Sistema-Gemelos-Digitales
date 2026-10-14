"""
Modelo 1: Ordinary Kriging (Baseline Geostatistico)
Interfaz sklearn-like para PyKrige
"""

import numpy as np
from pykrige.ok import OrdinaryKriging
from pykrige.ok3d import OrdinaryKriging3D
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')


class KrigingModel(BaseEstimator, RegressorMixin):
    """
    Ordinary Kriging envuelto en interfaz sklearn.
    Predice ley de cobre usando coordenadas espaciales.
    """
    
    def __init__(self, variogram_model='spherical', nlags=20, n_closest_points=300,
                 spatial_dims=2, max_training_points=500, random_state=42):
        self.variogram_model = variogram_model
        self.nlags = nlags
        self.n_closest_points = n_closest_points
        if spatial_dims not in (2, 3):
            raise ValueError("spatial_dims debe ser 2 o 3")
        self.spatial_dims = spatial_dims
        self.max_training_points = max_training_points
        self.random_state = random_state
        self.model = None
        self.n_samples_fit = None
        self.feature_names = ['x', 'y', 'z'][:spatial_dims]

    def _coordinates(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[1] < self.spatial_dims:
            raise ValueError(f"Kriging requiere {self.spatial_dims} coordenadas por muestra")
        return X[:, :self.spatial_dims]
        
    def fit(self, X, y):
        """
        X: array-like con [x, y] o [x, y, z] segun spatial_dims
        y: array-like shape (n_samples,) con leyes reales
        """
        coords = self._coordinates(X)
        y = np.asarray(y, dtype=float)
        # PyKrige 3D calcula estadisticas de ajuste muy costosas con miles de puntos.
        # Limitar solo el componente geostadistico; el resto de modelos usa todo X.
        if (self.spatial_dims == 3 and self.max_training_points is not None
                and len(coords) > self.max_training_points):
            idx = np.random.default_rng(self.random_state).choice(
                len(coords), size=self.max_training_points, replace=False
            )
            coords, y = coords[idx], y[idx]
        self.n_samples_fit = len(coords)
        if self.spatial_dims == 3:
            self.model = OrdinaryKriging3D(
                coords[:, 0], coords[:, 1], coords[:, 2], y,
                variogram_model=self.variogram_model, nlags=self.nlags,
                verbose=False, enable_plotting=False
            )
        else:
            self.model = OrdinaryKriging(
                x=coords[:, 0], y=coords[:, 1], z=y,
                variogram_model=self.variogram_model, nlags=self.nlags,
                verbose=False, enable_plotting=False
            )
        return self

    def _execute(self, X):
        if self.model is None:
            raise ValueError("Modelo no entrenado. Llame fit() primero.")
        coords = self._coordinates(X)
        points = [coords[:, i] for i in range(self.spatial_dims)]
        return self.model.execute(
            'points', *points,
            n_closest_points=min(self.n_closest_points, self.n_samples_fit),
            backend='loop' if self.spatial_dims == 3 else 'C'
        )
    
    def predict(self, X):
        """Predice leyes para coordenadas X"""
        predictions, _ = self._execute(X)
        return np.asarray(predictions).reshape(-1)
    
    def predict_with_uncertainty(self, X):
        """Predice leyes + varianza de kriging (incertidumbre)"""
        predictions, sigmasq = self._execute(X)
        predictions = np.asarray(predictions).reshape(-1)
        
        # Convertir varianza a intervalos P10-P90
        std = np.sqrt(np.maximum(np.asarray(sigmasq).reshape(-1), 0))
        p10 = predictions - 1.28 * std
        p90 = predictions + 1.28 * std
        
        return predictions, std, p10, p90
    
    def get_params(self, deep=True):
        return {
            'variogram_model': self.variogram_model,
            'nlags': self.nlags,
            'n_closest_points': self.n_closest_points,
            'spatial_dims': self.spatial_dims,
            'max_training_points': self.max_training_points,
            'random_state': self.random_state
        }
    
    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self
