"""
Modelo 4: Stacking Ensemble
Meta-modelo (Regresion Lineal) que fusiona Kriging + RF + XGBoost
"""

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import GroupShuffleSplit
from models.baseline_kriging import KrigingModel
from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel


class StackingEnsemble(BaseEstimator, RegressorMixin):
    """
    Stacking Ensemble que combina:
    - Ordinary Kriging (geostadistica)
    - Random Forest (no lineal)
    - XGBoost (boosting)
    
    Meta-modelo: Ridge Regression para combinar predicciones.
    """
    
    def __init__(self, kriging_variogram='spherical', rf_n_estimators=150,
                 xgb_n_estimators=150, meta_alpha=1.0, random_state=42,
                 spatial_dims=2):
        self.kriging_variogram = kriging_variogram
        self.rf_n_estimators = rf_n_estimators
        self.xgb_n_estimators = xgb_n_estimators
        self.meta_alpha = meta_alpha
        self.random_state = random_state
        self.spatial_dims = spatial_dims
        
        self.kriging = None
        self.rf = None
        self.xgb = None
        self.meta_model = None
        self.feature_importance = None
        
    def fit(self, X, y, groups=None):
        """
        Entrena los 3 modelos base y luego el meta-modelo.
        X debe incluir coordenadas [x, y] y features adicionales.
        """
        # Los modelos de arboles usan todas las variables disponibles.
        coords = X[:, :self.spatial_dims]
        features = X
        
        # Modelo base 1: Kriging (solo usa coordenadas)
        self.kriging = KrigingModel(variogram_model=self.kriging_variogram,
                                    n_closest_points=64 if self.spatial_dims == 3 else 300,
                                    spatial_dims=self.spatial_dims)
        
        # Modelo base 2: Random Forest
        self.rf = RandomForestModel(
            n_estimators=self.rf_n_estimators,
            random_state=self.random_state
        )
        
        # Modelo base 3: XGBoost
        self.xgb = XGBoostModel(
            n_estimators=self.xgb_n_estimators,
            random_state=self.random_state
        )
        
        # Generar predicciones out-of-fold para entrenar meta-modelo
        # Usamos validacion simple (70-30) para evitar data leakage
        n = len(y)
        if groups is not None:
            train_idx, val_idx = next(GroupShuffleSplit(
                n_splits=1, test_size=0.3, random_state=self.random_state
            ).split(X, y, groups))
        else:
            split_idx = int(n * 0.7)
            train_idx = np.arange(split_idx)
            val_idx = np.arange(split_idx, n)
        
        # Entrenar modelos base en train
        self.kriging.fit(coords[train_idx], y[train_idx])
        self.rf.fit(features[train_idx], y[train_idx])
        self.xgb.fit(features[train_idx], y[train_idx])
        
        # Predicciones en validacion
        val_coords = coords[val_idx]
        val_features = features[val_idx]
        
        pred_krig = self.kriging.predict(val_coords)
        pred_rf = self.rf.predict(val_features)
        pred_xgb = self.xgb.predict(val_features)
        
        # Stack de predicciones
        stack_X = np.column_stack([pred_krig, pred_rf, pred_xgb])
        
        # Meta-modelo: Ridge Regression
        self.meta_model = Ridge(alpha=self.meta_alpha)
        self.meta_model.fit(stack_X, y[val_idx])
        
        # Re-entrenar modelos base con todos los datos
        self.kriging.fit(coords, y)
        self.rf.fit(features, y)
        self.xgb.fit(features, y)
        
        # Guardar pesos del meta-modelo como importancia
        weights = self.meta_model.coef_
        self.feature_importance = {
            'kriging_weight': float(weights[0]),
            'rf_weight': float(weights[1]),
            'xgb_weight': float(weights[2])
        }
        
        return self
    
    def predict(self, X):
        """Predice usando el stack completo"""
        if self.meta_model is None:
            raise ValueError("Modelo no entrenado.")
        
        coords = X[:, :self.spatial_dims]
        features = X
        
        pred_krig = self.kriging.predict(coords)
        pred_rf = self.rf.predict(features)
        pred_xgb = self.xgb.predict(features)
        
        stack_X = np.column_stack([pred_krig, pred_rf, pred_xgb])
        return self.meta_model.predict(stack_X)
    
    def predict_with_uncertainty(self, X):
        """Combina incertidumbres de los 3 modelos base"""
        coords = X[:, :self.spatial_dims]
        features = X
        
        # Predicciones de cada modelo
        pred_krig, std_krig, p10_krig, p90_krig = self.kriging.predict_with_uncertainty(coords)
        pred_rf, std_rf, p10_rf, p90_rf = self.rf.predict_with_uncertainty(features)
        pred_xgb, std_xgb, p10_xgb, p90_xgb = self.xgb.predict_with_uncertainty(features)
        
        # Stack para meta-modelo
        stack_X = np.column_stack([pred_krig, pred_rf, pred_xgb])
        pred = self.meta_model.predict(stack_X)
        
        # Incertidumbre ponderada por pesos del meta-modelo
        weights = self.meta_model.coef_
        weights_norm = np.abs(weights) / np.sum(np.abs(weights))
        
        std = (weights_norm[0] * std_krig + 
               weights_norm[1] * std_rf + 
               weights_norm[2] * std_xgb)
        
        p10 = pred - 1.28 * std
        p90 = pred + 1.28 * std
        
        return pred, std, p10, p90
    
    def get_feature_importance(self):
        return self.feature_importance
    
    def get_params(self, deep=True):
        return {
            'kriging_variogram': self.kriging_variogram,
            'rf_n_estimators': self.rf_n_estimators,
            'xgb_n_estimators': self.xgb_n_estimators,
            'meta_alpha': self.meta_alpha,
            'random_state': self.random_state,
            'spatial_dims': self.spatial_dims
        }
    
    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self
