"""
Modelo 3: XGBoost
Estado del arte para problemas tabulares con datos mineros
"""

import numpy as np
import xgboost as xgb
from sklearn.base import BaseEstimator, RegressorMixin


class XGBoostModel(BaseEstimator, RegressorMixin):
    """
    XGBoost para prediccion de ley de cobre.
    Excelente manejo de outliers y datos faltantes.
    """
    
    def __init__(self, n_estimators=200, max_depth=8, learning_rate=0.05,
                 subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
                 reg_lambda=1.0, random_state=42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.random_state = random_state
        self.model = None
        self.feature_importance = None
        
    def fit(self, X, y):
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            random_state=self.random_state,
            n_jobs=-1,
            objective='reg:squarederror'
        )
        self.model.fit(X, y)
        
        # Guardar importancia de features
        importance = self.model.feature_importances_
        self.feature_importance = dict(zip(
            [f"feature_{i}" for i in range(X.shape[1])],
            importance.tolist()
        ))
        return self
    
    def predict(self, X):
        if self.model is None:
            raise ValueError("Modelo no entrenado.")
        return self.model.predict(X)
    
    def predict_with_uncertainty(self, X):
        """
        Usa quantile regression para intervalos de prediccion.
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado.")
        
        # Prediccion puntual
        pred = self.model.predict(X)
        
        # Estimar incertidumbre usando SHAP o residual aproximado
        # Por simplicidad, usamos la desviacion de predicciones de boosting
        dmatrix = xgb.DMatrix(X)
        # Obtener predicciones de cada arbol
        tree_preds = self.model.get_booster().predict(dmatrix, pred_leaf=True)
        
        # Aproximacion simple: usar predicciones de early trees
        n_trees = min(50, self.n_estimators)
        early_preds = []
        for i in range(n_trees):
            tree = self.model.get_booster()[i]
            early_preds.append(tree.predict(dmatrix))
        
        std_pred = np.std(early_preds, axis=0)
        p10 = pred - 1.28 * std_pred
        p90 = pred + 1.28 * std_pred
        
        return pred, std_pred, p10, p90
    
    def get_feature_importance(self):
        return self.feature_importance
    
    def get_params(self, deep=True):
        return {
            'n_estimators': self.n_estimators,
            'max_depth': self.max_depth,
            'learning_rate': self.learning_rate,
            'subsample': self.subsample,
            'colsample_bytree': self.colsample_bytree,
            'reg_alpha': self.reg_alpha,
            'reg_lambda': self.reg_lambda,
            'random_state': self.random_state
        }
    
    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self
