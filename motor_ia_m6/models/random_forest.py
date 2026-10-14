"""
Modelo 2: Random Forest
Robustez y manejo de no linealidades en datos espaciales
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.base import BaseEstimator, RegressorMixin


class RandomForestModel(BaseEstimator, RegressorMixin):
    """
    Random Forest para prediccion de ley de cobre.
    Maneja bien relaciones no lineales entre variables geologicas.
    """
    
    def __init__(self, n_estimators=200, max_depth=15, min_samples_split=5,
                 min_samples_leaf=2, max_features='sqrt', random_state=42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.random_state = random_state
        self.model = None
        self.feature_importance = None
        
    def fit(self, X, y):
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            max_features=self.max_features,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.model.fit(X, y)
        self.feature_importance = dict(zip(
            [f"feature_{i}" for i in range(X.shape[1])],
            self.model.feature_importances_.tolist()
        ))
        return self
    
    def predict(self, X):
        if self.model is None:
            raise ValueError("Modelo no entrenado.")
        return self.model.predict(X)
    
    def predict_with_uncertainty(self, X):
        """
        Usa la desviacion entre arboles como medida de incertidumbre.
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado.")
        
        # Obtener predicciones de cada arbol
        predictions = np.array([tree.predict(X) for tree in self.model.estimators_])
        
        mean_pred = np.mean(predictions, axis=0)
        std_pred = np.std(predictions, axis=0)
        
        # Intervalos aproximados P10-P90
        p10 = np.percentile(predictions, 10, axis=0)
        p90 = np.percentile(predictions, 90, axis=0)
        
        return mean_pred, std_pred, p10, p90
    
    def get_feature_importance(self):
        return self.feature_importance
    
    def get_params(self, deep=True):
        return {
            'n_estimators': self.n_estimators,
            'max_depth': self.max_depth,
            'min_samples_split': self.min_samples_split,
            'min_samples_leaf': self.min_samples_leaf,
            'max_features': self.max_features,
            'random_state': self.random_state
        }
    
    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self
