"""
Modelo 5: NN + Bayesian Kriging
Red Neuronal Profunda (MLP) para patrones complejos + 
Kriging Bayesiano para cuantificacion de incertidumbre.
Fusion ponderada optimizada.
"""

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import GroupShuffleSplit
from models.baseline_kriging import KrigingModel


class DeepNN(nn.Module):
    """Red Neuronal Profunda para prediccion de ley de cobre"""
    
    def __init__(self, input_dim, hidden_dims=[128, 64, 32], dropout=0.2):
        super(DeepNN, self).__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, 1))
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x).squeeze()


class NNBayesianKriging(BaseEstimator, RegressorMixin):
    """
    Hibrido NN + Bayesian Kriging.
    
    La NN aprende patrones complejos de alteracion, litologia, etc.
    El Kriging Bayesiano cuantifica incertidumbre espacial.
    Fusion por promedio ponderado optimizado.
    """
    
    def __init__(self, hidden_dims=[128, 64, 32], dropout=0.2,
                 learning_rate=0.001, epochs=200, batch_size=32,
                 kriging_variogram='spherical', nn_weight=0.6,
                 random_state=42, run_feature_importance=True,
                 spatial_dims=2):
        self.hidden_dims = hidden_dims
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.kriging_variogram = kriging_variogram
        self.nn_weight = nn_weight
        self.random_state = random_state
        self.run_feature_importance = run_feature_importance
        self.spatial_dims = spatial_dims
        
        self.nn_model = None
        self.kriging_model = None
        self.scaler = StandardScaler()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.feature_importance = None
        
    def fit(self, X, y, groups=None):
        """Entrena NN y Kriging, optimiza peso de fusion sobre hold-out"""
        np.random.seed(self.random_state)
        torch.manual_seed(self.random_state)
        
        # Split interno train/validacion (85/15).
        # El kriging interpola casi exacto en sus puntos de entrenamiento, asi que el
        # peso de fusion debe optimizarse sobre datos NO vistos para comparar de forma justa.
        n_samples = len(y)
        if groups is not None:
            train_idx, val_idx = next(GroupShuffleSplit(
                n_splits=1, test_size=0.15, random_state=self.random_state
            ).split(X, y, groups))
        else:
            rng = np.random.default_rng(self.random_state)
            idx_all = rng.permutation(n_samples)
            n_val = max(2, int(round(n_samples * 0.15)))
            val_idx = idx_all[:n_val]
            train_idx = idx_all[n_val:]
        
        coords_train = X[train_idx, :self.spatial_dims]
        features_train = X[train_idx]
        y_train = y[train_idx]
        X_val = X[val_idx]
        y_val = y[val_idx]
        
        # Entrenar Kriging Bayesiano (solo con datos de entrenamiento)
        self.kriging_model = KrigingModel(variogram_model=self.kriging_variogram,
                                          n_closest_points=64 if self.spatial_dims == 3 else 300,
                                          spatial_dims=self.spatial_dims)
        self.kriging_model.fit(coords_train, y_train)
        
        # Preparar datos para NN
        features_scaled = self.scaler.fit_transform(features_train)
        
        X_tensor = torch.FloatTensor(features_scaled).to(self.device)
        y_tensor = torch.FloatTensor(y_train).to(self.device)
        
        # Crear y entrenar NN
        input_dim = features_train.shape[1]
        self.nn_model = DeepNN(input_dim, self.hidden_dims, self.dropout).to(self.device)
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.nn_model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=20)
        
        # Entrenamiento
        self.nn_model.train()
        n_samples = len(y_train)
        
        # Ajustar batch_size para evitar batches de 1 muestra
        effective_batch_size = min(self.batch_size, n_samples)
        if n_samples % effective_batch_size == 1:
            effective_batch_size = max(2, effective_batch_size - 1)
        
        for epoch in range(self.epochs):
            # Mini-batch
            indices = np.random.permutation(n_samples)
            epoch_loss = 0
            n_batches = 0
            
            for i in range(0, n_samples, effective_batch_size):
                batch_idx = indices[i:i+effective_batch_size]
                
                # Saltar batches con menos de 2 muestras (BatchNorm requiere >= 2)
                if len(batch_idx) < 2:
                    continue
                
                batch_X = X_tensor[batch_idx]
                batch_y = y_tensor[batch_idx]
                
                optimizer.zero_grad()
                outputs = self.nn_model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                n_batches += 1
            
            if n_batches > 0:
                scheduler.step(epoch_loss / n_batches)
            
            if (epoch + 1) % 50 == 0:
                print(f"Epoch {epoch+1}/{self.epochs}, Loss: {epoch_loss:.6f}")
        
        # Optimizar peso de fusion sobre hold-out (datos no vistos)
        self._optimize_fusion_weight(X_val, y_val)
        
        # Calcular importancia de features (permutation importance aproximada)
        # Desactivable para acelerar CV / tuning, donde solo importa el predict
        if self.run_feature_importance:
            self._calculate_feature_importance(X, y)
        
        return self
    
    def _optimize_fusion_weight(self, X_val, y_val):
        """Optimiza el peso de fusion entre NN y Kriging sobre datos de validacion (no vistos)"""
        coords_val = X_val[:, :self.spatial_dims]
        features_val = X_val
        
        pred_krig = self.kriging_model.predict(coords_val)
        pred_nn = self._nn_predict(features_val)
        
        # Buscar peso optimo minimizando MSE
        best_weight = 0.5
        best_mse = float('inf')
        
        for w in np.linspace(0, 1, 21):
            fused = w * pred_nn + (1 - w) * pred_krig
            mse = np.mean((y_val - fused) ** 2)
            if mse < best_mse:
                best_mse = mse
                best_weight = w
        
        self.nn_weight = best_weight
        print(f"Peso optimo de fusion (validacion): NN={self.nn_weight:.2f}, Kriging={1-self.nn_weight:.2f}")
    
    def _nn_predict(self, features):
        """Prediccion con la red neuronal"""
        self.nn_model.eval()
        features_scaled = self.scaler.transform(features)
        X_tensor = torch.FloatTensor(features_scaled).to(self.device)
        
        with torch.no_grad():
            predictions = self.nn_model(X_tensor).cpu().numpy()
        
        return predictions
    
    def predict(self, X):
        """Prediccion fusionada NN + Kriging"""
        coords = X[:, :self.spatial_dims]
        features = X
        
        pred_krig = self.kriging_model.predict(coords)
        pred_nn = self._nn_predict(features)
        
        # Fusion ponderada
        fused = self.nn_weight * pred_nn + (1 - self.nn_weight) * pred_krig
        return fused
    
    def predict_with_uncertainty(self, X):
        """Prediccion con incertidumbre cuantificada"""
        coords = X[:, :self.spatial_dims]
        features = X
        
        # Predicciones
        pred_krig, std_krig, p10_krig, p90_krig = self.kriging_model.predict_with_uncertainty(coords)
        pred_nn = self._nn_predict(features)
        pred_fused = self.nn_weight * pred_nn + (1 - self.nn_weight) * pred_krig
        
        # Incertidumbre: combinar varianza de kriging + incertidumbre de NN (MC Dropout)
        # MC dropout must never update BatchNorm with held-out observations.
        # Keep the deterministic predictor and all fitted buffers unchanged.
        module_modes = {module: module.training for module in self.nn_model.modules()}
        self.nn_model.eval()
        for module in self.nn_model.modules():
            if isinstance(module, nn.Dropout):
                module.train()
        nn_samples = []
        
        features_scaled = self.scaler.transform(features)
        X_tensor = torch.FloatTensor(features_scaled).to(self.device)
        
        # FIX: BatchNorm requiere batch_size > 1 en modo train
        # Si solo hay 1 muestra, duplicarla temporalmente
        original_size = X_tensor.size(0)
        if original_size == 1:
            X_tensor = X_tensor.repeat(2, 1)
        
        devices = [self.device.index or 0] if self.device.type == 'cuda' else []
        try:
            with torch.random.fork_rng(devices=devices), torch.no_grad():
                torch.manual_seed(self.random_state)
                for _ in range(50):
                    pred_mc = self.nn_model(X_tensor).cpu().numpy()
                    if original_size == 1:
                        pred_mc = pred_mc[:1]
                    nn_samples.append(pred_mc)
        finally:
            for module, training in module_modes.items():
                module.training = training
        
        nn_samples = np.array(nn_samples)
        std_nn = np.std(nn_samples, axis=0)
        
        # Incertidumbre total ponderada
        std_total = np.sqrt(
            (self.nn_weight ** 2) * (std_nn ** 2) +
            ((1 - self.nn_weight) ** 2) * (std_krig ** 2)
        )
        
        p10 = pred_fused - 1.28 * std_total
        p90 = pred_fused + 1.28 * std_total
        
        return pred_fused, std_total, p10, p90
    
    def _calculate_feature_importance(self, X, y, max_points=1500):
        """Calcula importancia de features via permutation (submuestreado)"""
        n = len(X)
        if n > max_points:
            rng = np.random.default_rng(self.random_state)
            idx = rng.choice(n, size=max_points, replace=False)
            X = X[idx]
            y = y[idx]
            print(f"Importancia de features (permutación) sobre {max_points}/{n} puntos...")
        else:
            print(f"Importancia de features (permutación) sobre {n} puntos...")
        
        baseline_pred = self.predict(X)
        baseline_mse = np.mean((y - baseline_pred) ** 2)
        
        importances = []
        for i in range(X.shape[1]):
            print(f"  Permutando feature {i+1}/{X.shape[1]}...")
            X_permuted = X.copy()
            np.random.shuffle(X_permuted[:, i])
            pred_permuted = self.predict(X_permuted)
            mse_permuted = np.mean((y - pred_permuted) ** 2)
            importances.append(mse_permuted - baseline_mse)
        print("Importancia de features completada.")
        
        self.feature_importance = dict(zip(
            [f"feature_{i}" for i in range(X.shape[1])],
            importances
        ))
    
    def get_feature_importance(self):
        return self.feature_importance
    
    def get_params(self, deep=True):
        return {
            'hidden_dims': self.hidden_dims,
            'dropout': self.dropout,
            'learning_rate': self.learning_rate,
            'epochs': self.epochs,
            'batch_size': self.batch_size,
            'kriging_variogram': self.kriging_variogram,
            'nn_weight': self.nn_weight,
            'random_state': self.random_state,
            'run_feature_importance': self.run_feature_importance,
            'spatial_dims': self.spatial_dims
        }
    
    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self
