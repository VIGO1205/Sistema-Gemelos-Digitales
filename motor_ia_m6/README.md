# Motor IA M-6

Motor de Inteligencia Artificial para estimación de leyes de cobre en el Sistema de Gemelos Digitales M-6.

## Estructura

```
motor_ia_m6/
├── app.py                      # Aplicación Streamlit principal
├── config.py                   # Configuración global
├── requirements.txt            # Dependencias Python
├── data/                       # Datos
│   ├── raw/                    # Datos crudos (CSV, Excel)
│   ├── processed/              # Datos procesados
│   └── synthetic_generator.py  # Generador de datos sintéticos
├── database/                   # Conexión PostgreSQL
│   ├── connection.py
│   └── schema_models.sql
├── models/                     # Modelos de ML
│   ├── baseline_kriging.py
│   ├── random_forest.py
│   ├── xgboost_model.py
│   ├── stacking_ensemble.py
│   └── nn_bayesian.py
├── training/                   # Pipeline de entrenamiento
│   └── pipeline.py
├── evaluation/                 # Métricas y evaluación
│   └── metrics.py
├── reports/                    # Reportes generados
├── utils/                      # Utilidades
└── xai/                        # Explainable AI (futuro)
```

## Uso

### 1. Instalar dependencias

```bash
cd motor_ia_m6
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`.

## Modelos Implementados

| Modelo | Tipo | Descripción |
|--------|------|-------------|
| Ordinary Kriging | Geoestadístico | Interpolación geoestadística clásica |
| Random Forest | Ensemble | 200 árboles con validación OOB |
| XGBoost | Gradient Boosting | 100 estimadores, learning rate 0.05 |
| Stacking Ensemble | Meta-modelo | Ridge como meta sobre Kriging+RF+XGB |
| NN + Bayesian Kriging | Híbrido | MLP + Kriging con MC Dropout |

## Metodología CRISP-DM

La aplicación Streamlit implementa las 6 fases de CRISP-DM:

1. **Comprensión del Negocio** - Objetivos y contexto minero
2. **Comprensión de Datos** - Análisis exploratorio espacial
3. **Preparación de Datos** - Feature engineering y limpieza
4. **Modelado** - Entrenamiento de los 5 modelos
5. **Evaluación** - Métricas avanzadas, bootstrap, estabilidad
6. **Despliegue** - Activación del mejor modelo

## Conexión a Base de Datos

El motor intenta conectarse a PostgreSQL. Si falla (por ejemplo, por incompatibilidad de `psycopg2` en Python 3.13), utiliza almacenamiento en memoria (`session_state`) como fallback.

## Notas

- Los datos sintéticos generan ~2,000 muestras por banco con patrones geológicos realistas (skarn, supergene, fallas).
- El modelo ganador se determina por un **score compuesto** ponderado: RMSE 25%, MAE 20%, R² 20%, MAPE 15%, Bias 10%, Incertidumbre 10%.
- En Windows con Python 3.13, `psycopg2` puede fallar con error de decodificación UTF-8. La aplicación maneja esto automáticamente.
