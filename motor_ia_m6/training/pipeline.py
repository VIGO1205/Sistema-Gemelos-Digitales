"""
Pipeline de entrenamiento y feature engineering
CRISP-DM Fase 3: Preparacion de datos + Fase 4: Modelado
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

from config import TRAIN_CONFIG, FEATURES, TARGET
from database.connection import (
    fetch_dataframe, insert_benchmark_result, 
    insert_predictions, clear_benchmark_for_bench,
    fetch_real_plant_data
)
from models.baseline_kriging import KrigingModel
from models.random_forest import RandomForestModel
from models.xgboost_model import XGBoostModel
from models.stacking_ensemble import StackingEnsemble
from models.nn_bayesian import NNBayesianKriging
from evaluation.cross_validation import repeated_kfold_cv
from evaluation.statistical_tests import run_statistical_analysis
from training.hyperparameter_tuning import tune_all


class FeatureEngineer:
    """Ingenieria de caracteristicas para datos mineros"""
    
    @staticmethod
    def create_features(df: pd.DataFrame) -> pd.DataFrame:
        """Crea features adicionales a partir de datos crudos"""
        df = df.copy()
        
        # Features espaciales (solo si las columnas existen)
        if 'x' in df.columns and 'y' in df.columns:
            df['distance_to_origin'] = np.sqrt(df['x']**2 + df['y']**2)
        if 'z' in df.columns:
            df['elevation_relative'] = df['z'] - df['z'].min()
        
        # Features geologicas
        if 'cu_base' in df.columns:
            df['cu_base_log'] = np.log1p(df['cu_base'])
        
        # Features de incertidumbre
        if 'epistemic_unc' in df.columns:
            df['uncertainty_category'] = pd.cut(
                df['epistemic_unc'], 
                bins=[0, 0.3, 0.6, 1.0],
                labels=['baja', 'media', 'alta']
            )
        
        # Features de alteracion
        if 'swir_alteration_index' in df.columns:
            df['alteration_intensity'] = df['swir_alteration_index'] * df['cu_base']
        
        # Ratios
        if 'distance_to_fault' in df.columns and 'distance_to_contact' in df.columns:
            df['fault_contact_ratio'] = df['distance_to_fault'] / (df['distance_to_contact'] + 1e-6)
        
        return df
    
    @staticmethod
    def prepare_matrix(df: pd.DataFrame, feature_cols=None, target_col=TARGET):
        """Prepara matrices X, y para entrenamiento"""
        if feature_cols is None:
            feature_cols = [c for c in df.columns if c != target_col and c != 'id']
        
        X = df[feature_cols].values
        y = df[target_col].values if target_col in df.columns else None
        
        return X, y, feature_cols


class TrainingPipeline:
    """Pipeline completo de entrenamiento de los 5 modelos"""
    
    def __init__(self, bench=None):
        self.bench = bench
        self.models = {}
        self.results = {}
        self.scaler = StandardScaler()
        self.feature_engineer = FeatureEngineer()
        self.hyperparameters = {}
        self.cv_results = {}
        self.stat_tests = {}
        self.is_drillhole_dataset = False
        self.split_strategy = None
        self.test_indices = None
        self.train_groups = None
        
    def load_data(self, bench=None, use_real_data=False):
        """Carga datos desde PostgreSQL o datos reales de planta"""
        bench = bench or self.bench
        
        if use_real_data:
            # Cargar datos reales de planta desde backend API
            print(f"Cargando datos reales de planta para banco {bench}...")
            df = fetch_real_plant_data(bench=bench)
            if not df.empty:
                print(f"Datos reales cargados: {len(df)} muestras")
                return df
            else:
                raise ValueError(
                    f"No hay datos reales de planta para el banco {bench}m. "
                    f"Verifica que existan registros en Control de Procesos (process_control_points) "
                    f"con project_id=4 y bench={bench}."
                )
        
        # Modo tradicional: cargar desde block_models en PostgreSQL
        query = f"""
            SELECT id, x, y, z, cu_base, cu_bayesian, 
                   rock_type, alteration, 
                   distance_to_fault, distance_to_contact,
                   swir_alteration_index, blasthole_density, 
                   epistemic_unc, p10, p50, p90
            FROM block_models 
            WHERE bench = {bench}
        """
        
        try:
            df = fetch_dataframe(query)
            if df.empty:
                # Generar datos sinteticos SOLO en modo demo (use_real_data=False)
                print(f"No hay datos en block_models para banco {bench}. Generando datos sinteticos para demo...")
                df = self._generate_synthetic_data(bench)
            return df
        except Exception as e:
            print(f"Error cargando datos: {e}. Generando sinteticos...")
            return self._generate_synthetic_data(bench)
    
    def _generate_synthetic_data(self, bench, n_samples=2000):
        """Genera datos sinteticos realistas para demostracion"""
        from data.synthetic_generator import generate_realistic_mining_data
        return generate_realistic_mining_data(bench, n_samples=n_samples)
    
    @staticmethod
    def _adapt_geomet_drillholes(raw):
        """Convierte ensayos GeoMet a coordenadas y Cu medido en porcentaje."""
        required = ['HOLEID', 'X', 'Y', 'Z', 'Cu ppm']
        values = raw[required].apply(pd.to_numeric, errors='coerce')
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError("HOLEID, coordenadas o Cu ppm contienen valores no finitos")
        if (values['HOLEID'] <= 0).any() or (values['HOLEID'] % 1 != 0).any():
            raise ValueError("HOLEID debe ser un entero positivo")
        if (values['Cu ppm'] < 0).any() or (values['Cu ppm'] > 1_000_000).any():
            raise ValueError("Cu ppm fuera del rango físico 0–1 000 000")
        if values.duplicated(['X', 'Y', 'Z']).any():
            raise ValueError("Hay coordenadas repetidas; revisar las muestras")
        return pd.DataFrame({
            'hole_id': values['HOLEID'].astype(int),
            'x': values['X'], 'y': values['Y'], 'z': values['Z'],
            'cu_bayesian': values['Cu ppm'] / 10_000.0,
        })

    @staticmethod
    def _split_holes(hole_ids, val_size, test_size, random_state):
        """Reserva sondajes completos, sin compartir intervalos entre conjuntos."""
        groups = np.asarray(hole_ids)
        holes = np.unique(groups)
        if len(holes) < 20:
            raise ValueError("Se necesitan al menos 20 sondajes para una evaluación independiente.")
        shuffled = np.random.default_rng(random_state).permutation(holes)
        n_test = max(1, round(len(holes) * test_size))
        n_val = max(1, round(len(holes) * val_size))
        test_holes = shuffled[:n_test]
        val_holes = shuffled[n_test:n_test + n_val]
        train_holes = shuffled[n_test + n_val:]
        return tuple(np.flatnonzero(np.isin(groups, chosen))
                     for chosen in (train_holes, val_holes, test_holes))

    def load_from_file(self, file_path: str) -> pd.DataFrame:
        """Carga datos desde archivo CSV o Excel"""
        # Streamlit UploadedFile (objeto con .name/.read) o ruta de archivo (str)
        name = file_path.name if hasattr(file_path, 'name') else str(file_path)

        if name.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path, engine=None)
        else:
            raise ValueError("Formato no soportado. Use CSV o Excel.")

        if {'HOLEID', 'X', 'Y', 'Z', 'Cu ppm'}.issubset(df.columns):
            df = self._adapt_geomet_drillholes(df)
        
        # Validar columnas requeridas
        drillholes = 'hole_id' in df.columns and 'cu_base' not in df.columns
        required_cols = ['x', 'y', 'z', TARGET] if drillholes else ['x', 'y', 'z', 'cu_base', TARGET]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes: {missing}")
        
        # Conservar el archivo tal como llega. Copiar cu_base a cu_bayesian
        # fabricaría una variable objetivo y produciría métricas perfectas falsas.
        return df
    
    def preprocess(self, df):
        """Preprocesamiento completo"""
        self.is_drillhole_dataset = 'hole_id' in df.columns and 'cu_base' not in df.columns
        if TARGET not in df.columns:
            raise ValueError(f"Falta la ley medida {TARGET}; no se puede entrenar.")
        if self.is_drillhole_dataset:
            # Solo la posición predice Cu: no incluir otros ensayos de la misma muestra.
            feature_cols = ['x', 'y', 'z']
            missing = [c for c in feature_cols if c not in df.columns]
            if missing:
                raise ValueError(f"Faltan coordenadas de sondajes: {missing}")
            X = df[feature_cols].apply(pd.to_numeric, errors='coerce').to_numpy(dtype=float)
            y = pd.to_numeric(df[TARGET], errors='coerce').to_numpy(dtype=float)
            mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
            return X[mask], y[mask], feature_cols, df.loc[mask].copy()

        # Feature engineering
        df = self.feature_engineer.create_features(df)
        
        # Codificar categoricas
        le_rock = LabelEncoder()
        le_alt = LabelEncoder()
        
        if 'rock_type' in df.columns:
            df['rock_type_encoded'] = le_rock.fit_transform(df['rock_type'].astype(str))
        if 'alteration' in df.columns:
            df['alteration_encoded'] = le_alt.fit_transform(df['alteration'].astype(str))
        if 'uncertainty_category' in df.columns:
            df['uncertainty_cat_encoded'] = le_alt.fit_transform(df['uncertainty_category'].astype(str))
        
        # Seleccionar SOLO las features definidas en config.py (sin autocompletar)
        # Esto previene data leakage de columnas "sorpresa" que lleguen del backend
        available_features = []
        for f in FEATURES:
            if f in df.columns:
                available_features.append(f)
        
        if not available_features:
            raise ValueError(f"Ninguna de las features definidas en config.py está presente en el dataset. "
                             f"Features esperadas: {FEATURES}. Columnas disponibles: {list(df.columns)}")
        
        X, y, feature_names = self.feature_engineer.prepare_matrix(
            df, feature_cols=available_features, target_col=TARGET
        )
        
        # Limpiar NaN/Inf
        mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
        X = X[mask]
        y = y[mask]
        
        return X, y, feature_names, df.loc[mask]
    
    def split_data(self, X, y, df=None):
        """Divide datos en train/val/test.
        
        Para sondajes, separa por HOLEID para no compartir intervalos del mismo
        sondaje entre entrenamiento y evaluación.
        """
        test_size = TRAIN_CONFIG['test_size']
        val_size = TRAIN_CONFIG['val_size']
        random_state = TRAIN_CONFIG['random_state']
        n = len(y)
        self.split_strategy = None
        self.train_groups = None

        if df is not None and 'hole_id' in df.columns and 'cu_base' not in df.columns:
            train_idx, val_idx, test_idx = self._split_holes(
                df['hole_id'].to_numpy(), val_size, test_size, random_state
            )
            self.split_strategy = 'sondajes_independientes'
            self.train_groups = df['hole_id'].to_numpy()[train_idx]
        # Walk-forward temporal para datos reales de planta
        elif df is not None and 'timestamp' in df.columns:
            order = np.argsort(pd.to_datetime(df['timestamp']).to_numpy())
            n_test = max(1, int(n * test_size))
            n_val = max(1, int(n * val_size))
            n_train = n - n_test - n_val
            if n_train < 2:
                raise ValueError("Muy pocos datos para separar entrenamiento, validación y prueba.")
            train_idx, val_idx, test_idx = (order[:n_train],
                                             order[n_train:n_train + n_val],
                                             order[n_train + n_val:])
            self.split_strategy = 'temporal'
            print(f"Walk-forward split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")
        elif self.split_strategy != 'sondajes_independientes':
            # Split aleatorio para bloques sintéticos o sin identificación de sondaje.
            temp_idx, test_idx = train_test_split(
                np.arange(n), test_size=test_size, random_state=random_state
            )
            val_ratio = val_size / (1 - test_size)
            train_idx, val_idx = train_test_split(
                temp_idx, test_size=val_ratio, random_state=random_state
            )
            self.split_strategy = 'aleatorio'

        self.test_indices = test_idx
        return (X[train_idx], X[val_idx], X[test_idx],
                y[train_idx], y[val_idx], y[test_idx])

    def get_test_frame(self, df):
        """Filas alineadas exactamente con X_test e y_test."""
        if self.test_indices is None:
            raise ValueError("Primero debe ejecutarse split_data.")
        return df.iloc[self.test_indices].copy()
    
    def train_all_models(self, X_train, y_train, X_val, y_val, models_to_train=None,
                         tune_hyperparameters=True, tuning_max_points=3000,
                         tuning_n_candidates=15, verbose=True):
        """Entrena los modelos seleccionados (o todos si no se especifica).

        tune_hyperparameters: si True, optimiza RF/XGB/NN sobre el validation set
        y re-entrena los modelos finales con los mejores hiperparametros.
        """
        from config import MODELS, TRAIN_CONFIG
        
        # Si no se especifica, entrenar todos los habilitados
        if models_to_train is None:
            models_to_train = [k for k, v in MODELS.items() if v.get('enabled', True)]
        
        total = len(models_to_train)
        print("\n" + "="*60)
        print(f"ENTRENANDO {total} MODELO(S): {', '.join(models_to_train)}")
        print("="*60)
        
        # ── Optimización de hiperparámetros ──────────────────────────────────
        if tune_hyperparameters:
            tunable = [m for m in models_to_train if m in ('random_forest', 'xgboost', 'nn_bayesian')]
            if tunable:
                print("\nOPTIMIZANDO HIPERPARAMETROS (rejilla sobre validation set)...")
                self.hyperparameters['tuning'] = tune_all(
                    X_train, y_train, X_val, y_val, tunable,
                    max_points=tuning_max_points,
                    n_candidates=tuning_n_candidates,
                    groups=self.train_groups,
                    spatial_dims=3 if self.is_drillhole_dataset else 2,
                    verbose=verbose
                )
        
        def _tuned(key, default):
            params = dict(default)
            best = self.hyperparameters.get('tuning', {}).get(key, {}).get('best_params')
            if best:
                params.update({k: v for k, v in best.items()})
            return params
        
        # Limpiar modelos previos
        self.models = {}
        
        for i, name in enumerate(models_to_train, 1):
            if name == 'kriging':
                print(f"\n[{i}/{total}] Entrenando Ordinary Kriging...")
                krig = KrigingModel(variogram_model='spherical',
                                    n_closest_points=64 if self.is_drillhole_dataset else 300,
                                    spatial_dims=3 if self.is_drillhole_dataset else 2)
                krig.fit(X_train, y_train)
                self.models['kriging'] = krig
                
            elif name == 'random_forest':
                print(f"[{i}/{total}] Entrenando Random Forest...")
                params = _tuned('random_forest', {'n_estimators': 200, 'max_depth': 15,
                                                  'min_samples_split': 5})
                rf = RandomForestModel(**params)
                rf.fit(X_train, y_train)
                self.models['random_forest'] = rf
                
            elif name == 'xgboost':
                print(f"[{i}/{total}] Entrenando XGBoost...")
                params = _tuned('xgboost', {'n_estimators': 200, 'max_depth': 8,
                                            'learning_rate': 0.05, 'subsample': 0.8,
                                            'colsample_bytree': 0.8})
                xgb = XGBoostModel(**params)
                xgb.fit(X_train, y_train)
                self.models['xgboost'] = xgb
                
            elif name == 'stacking':
                print(f"[{i}/{total}] Entrenando Stacking Ensemble...")
                stack = StackingEnsemble(rf_n_estimators=150, xgb_n_estimators=150,
                                         spatial_dims=3 if self.is_drillhole_dataset else 2)
                stack.fit(X_train, y_train, groups=self.train_groups)
                self.models['stacking'] = stack
                
            elif name == 'nn_bayesian':
                print(f"[{i}/{total}] Entrenando NN + Bayesian Kriging...")
                params = _tuned('nn_bayesian', {'epochs': 100, 'learning_rate': 0.001})
                nn_bayes = NNBayesianKriging(
                    hidden_dims=[128, 64, 32], run_feature_importance=True,
                    spatial_dims=3 if self.is_drillhole_dataset else 2, **params
                )
                nn_bayes.fit(X_train, y_train, groups=self.train_groups)
                self.models['nn_bayesian'] = nn_bayes
        
        # Registrar parametros usados (para reportes / DB / hyperparameters_used)
        self.hyperparameters['used'] = {
            name: self.models[name].get_params() for name in self.models
        }
        
        print("\n" + "="*60)
        print("ENTRENAMIENTO COMPLETADO")
        print("="*60)
        
        return self.models
    
    def run_cross_validation(self, X, y, model_keys, n_splits=None, n_repeats=None,
                             max_points=None, verbose=True):
        """
        Validacion cruzada repetida (RepeatedKFold) sobre X, y (train+val).
        Todos los modelos se evaluan sobre los MISMOS folds (diseno pareado),
        lo que habilita pruebas estadisticas robustas posteriores.
        """
        from config import TRAIN_CONFIG
        n_splits = n_splits or TRAIN_CONFIG.get('n_splits_cv', 5)
        n_repeats = n_repeats or TRAIN_CONFIG.get('n_repeats', 3)
        if max_points is None:
            max_points = TRAIN_CONFIG.get('cv_max_points', 3000)
        
        print("\n" + "="*60)
        print(f"VALIDACIÓN CRUZADA REPETIDA ({n_repeats}x{n_splits}-fold, pareada)")
        print("="*60)
        self.cv_results = repeated_kfold_cv(
            X, y, model_keys, n_splits=n_splits, n_repeats=n_repeats,
            max_points=max_points, verbose=verbose
        )
        print(f"CV completado: {self.cv_results['n_total_folds']} folds en "
              f"{self.cv_results['n_rows_used']} filas.")
        return self.cv_results
    
    def evaluate_all_models(self, X_test, y_test, df_test):
        """Evalua todos los modelos en test set"""
        from evaluation.metrics import ModelEvaluator
        
        evaluator = ModelEvaluator()
        results = {}
        predictions = {}  # Guardar predicciones para graficos
        
        print("\n" + "="*60)
        print("EVALUANDO MODELOS")
        print("="*60)
        
        for name, model in self.models.items():
            print(f"\nEvaluando {name}...")
            
            # Prediccion con incertidumbre
            if hasattr(model, 'predict_with_uncertainty'):
                pred, std, p10, p90 = model.predict_with_uncertainty(X_test)
            else:
                pred = model.predict(X_test)
                std = np.zeros_like(pred)
                p10 = pred - 0.1
                p90 = pred + 0.1
            
            # Calcular metricas (score compuesto normalizado por la escala del target)
            y_scale = float(np.std(y_test))
            metrics = evaluator.calculate_metrics(y_test, pred, std, y_scale=y_scale)
            results[name] = metrics
            
            # Guardar predicciones para graficos
            predictions[name] = {
                'y_true': y_test,
                'y_pred': pred,
                'residuals': y_test - pred,
                'std': std
            }
            
            # Guardar predicciones en PostgreSQL
            pred_df = pd.DataFrame({
                'block_id': df_test['id'].values if 'id' in df_test.columns else [f'BLK_{i}' for i in range(len(pred))],
                'x': df_test['x'].to_numpy(),
                'y': df_test['y'].to_numpy(),
                'z': df_test['z'].to_numpy(),
                'predicted': pred,
                'actual': y_test,
                'residual': y_test - pred,
                'p10': p10,
                'p50': pred,
                'p90': p90
            })
            
            if not self.is_drillhole_dataset:
                try:
                    insert_predictions(pred_df, name, self.bench)
                except Exception as e:
                    print(f"  Warning: No se pudieron guardar predicciones: {e}")
            
            print(f"  RMSE: {metrics['rmse']:.4f} | R2: {metrics['r2']:.4f} | Score: {metrics['composite_score']:.4f}")
        
        # ── Pruebas estadísticas robustas con datos REALES ───────────────────
        try:
            winner = (min(results, key=lambda n: results[n]['rmse'])
                      if self.is_drillhole_dataset else
                      max(results, key=lambda n: (results[n].get('composite_score') or -1)))
            test_preds = {n: {'y_true': p['y_true'], 'y_pred': p['y_pred']}
                          for n, p in predictions.items()}
            cv_metrics = None
            if self.cv_results:
                cv_metrics = {k: list(v) for k, v in self.cv_results.get('metrics', {}).items()}
            
            self.stat_tests = run_statistical_analysis(
                test_preds, cv_metrics=cv_metrics, winner=winner,
                groups=df_test['hole_id'].to_numpy() if self.is_drillhole_dataset else None
            )
            fri = self.stat_tests.get('friedman', {})
            if fri.get('p_value') is not None:
                print(f"  Friedman: chi2={fri.get('statistic'):.3f}, "
                      f"p={fri.get('p_value'):.4f} "
                      f"({'diferencia significativa' if fri.get('significant') else 'sin diferencia significativa'})")
            n_sig = sum(1 for w in self.stat_tests.get('wilcoxon', []) if w.get('significant'))
            print(f"  Wilcoxon pareado+Bonferroni: {n_sig} pares con diferencia significativa")
            print(f"  Bootstrap pareado (ganador {winner}): "
                  f"{len(self.stat_tests.get('bootstrap', []))} comparaciones")
        except Exception as e:
            print(f"  Warning: pruebas estadisticas fallaron: {e}")
            self.stat_tests = {}
        
        self.results = results
        self.predictions = predictions
        self.test_data = {'X_test': X_test, 'y_test': y_test, 'df_test': df_test}
        return results
    
    def save_results(self):
        """Guarda resultados de benchmark en PostgreSQL"""
        from config import MODELS

        if self.is_drillhole_dataset:
            print("Resultados de sondajes exploratorios: no se guardan como banco operativo.")
            return
        
        # Limpiar resultados anteriores
        try:
            clear_benchmark_for_bench(self.bench)
        except Exception as e:
            print(f"Warning: No se pudieron limpiar resultados previos: {e}")
        
        # Insertar nuevos resultados
        for name, metrics in self.results.items():
            model_info = MODELS.get(name, {'type': 'CLASSIC'})
            
            try:
                insert_benchmark_result(
                    model_name=model_info['name'],
                    model_type=model_info['type'],
                    bench=self.bench,
                    metrics=metrics,
                    hyperparams=self.models[name].get_params()
                )
            except Exception as e:
                print(f"Warning: No se pudo guardar benchmark de {name}: {e}")
        
        print(f"\nResultados guardados para banco {self.bench}")
    
    def run_full_pipeline(self, bench=None):
        """Ejecuta el pipeline completo"""
        self.bench = bench or self.bench
        
        print(f"\n{'='*60}")
        print(f"PIPELINE M6 - BANCO {self.bench}m")
        print(f"{'='*60}")
        
        # 1. Cargar datos
        df = self.load_data(self.bench)
        print(f"Datos cargados: {len(df)} registros")
        
        # 2. Preprocesar
        X, y, feature_names, df_clean = self.preprocess(df)
        print(f"Features: {feature_names}")
        print(f"Muestras despues de limpieza: {len(y)}")
        
        # 3. Split
        X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y)
        print(f"Train: {len(y_train)} | Val: {len(y_val)} | Test: {len(y_test)}")
        
        # 4. Entrenar
        self.train_all_models(X_train, y_train, X_val, y_val)
        
        # 5. Evaluar
        results = self.evaluate_all_models(X_test, y_test, self.get_test_frame(df_clean))
        
        # 6. Guardar
        self.save_results()
        
        return results
