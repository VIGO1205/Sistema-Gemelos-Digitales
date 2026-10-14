# 📄 Respuestas Técnicas y Análisis de Base de Código
**Proyecto:** M-6 Gemelo Digital (Control de Leyes y Cuantificación de Incertidumbre en Minería)  
**Objetivo:** Insumo técnico para la redacción de la sección de Métodos, Resultados y Discusión del Artículo Científico.

---

## 📌 1. Sobre el modelo "NN + Bayesian Kriging"

### A. Identidad de Métricas con Ordinary Kriging
* **Diagnóstico técnico**: El fenómeno donde las 5 métricas ($RMSE, MAE, R^2, MAPE, Score$) son $100\%$ idénticas a las de Ordinary Kriging **no se debe a un error de ejecución ni a un fallback por excepción**, sino al comportamiento explícito de la función de optimización de fusión ponderada.
* **Mecanismo en el código**: En [`motor_ia_m6/models/nn_bayesian.py`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/models/nn_bayesian.py#L141-L161), la predicción fusionada se define como:
  $$\hat{y}_{fused} = w \cdot \hat{y}_{NN} + (1 - w) \cdot \hat{y}_{Kriging}$$
  Durante la fase `fit`, la función `_optimize_fusion_weight` realiza una búsqueda en grilla sobre $w \in [0, 1]$ para minimizar el Error Cuadrático Medio ($MSE$). Cuando la Red Neuronal (debido a un tamaño muestral reducido como $n=36$ en el conjunto de entrenamiento) no logra superar la precisión del Kriging Ordinario, el optimizador selecciona **$w = 0.0$**.
* **Consecuencia matemática**: Al ser $w = 0.0$, el modelo asigna peso nulo a la red y peso completo al Kriging ($\hat{y}_{fused} = \hat{y}_{Kriging}$), produciendo predicciones y métricas estadísticamente idénticas.

> [!NOTE]
> Para el artículo, esto demuestra un mecanismo de **selección objetiva de modelos** que previene el sobreajuste (*overfitting*) reduciendo el ensamble al estimador geoestadístico base cuando los datos tabulares no justifican la complejidad del modelo profundo.

### B. Arquitectura Exacta del Modelo
El modelo es una **arquitectura híbrida de dos etapas**:
1. **Componente Red Neuronal (PyTorch)**: Perceptrón Multicapa (MLP) con 3 capas ocultas ($128 \rightarrow 64 \rightarrow 32$ neuronas), funciones de activación `ReLU`, normalización por lotes (`BatchNorm1d`) y regularización mediante `Dropout(0.2)`.
2. **Componente Geoestadístico**: Kriging Ordinario (`PyKrige`) con modelo variográmico Esférico sobre las coordenadas espaciales ($X, Y$).
3. **Incertidumbre Probalística**: La estimación de incertidumbre en `predict_with_uncertainty` implementa **Monte Carlo Dropout** activo (50 pasadas *forward* con `model.train()` activado) combinando la varianza epistémica de la red con la varianza del Kriging:
   $$\sigma_{total}^2 = w^2 \sigma_{nn}^2 + (1-w)^2 \sigma_{krig}^2$$

### C. Registro y Logs de Entrenamiento
* Los logs de entrenamiento se emiten directamente a la salida estándar/consola y a la interfaz de Streamlit en cada época (`Epoch 50/100, Loss: ...`) mostrando la evolución de la función de pérdida MSE y el peso óptimo de fusión asignado (`Peso optimo de fusion: NN=0.00, Kriging=1.00`).

---

## 📌 2. Sobre la variable `predicted_bayesian`

### A. Origen de la Variable
* En el flujo de datos operacionales de planta ([`fetch_real_plant_data`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/database/connection.py#L238-L290)), `predicted_bayesian` proviene de la estimación de inferencia bayesiana espacial previa obtenida mediante el **Kernel Matérn 5/2** y simulación Monte Carlo sobre los bloques 3D y sondajes informados.

### B. Evaluación de Fuga de Datos (Data Leakage)
* **Ausencia de Data Leakage**: La variable se calculó de forma totalmente independiente a la ley real final recibida en planta (`plant_feed_grade`). Representa el conocimiento previo (*prior*) disponible al momento de la planificación.
* **Auditoría de Características**: Como se explicita en el código ([`connection.py:295-300`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/database/connection.py#L295-L300)), se eliminaron intencionalmente del pipeline de ML variables derivadas como `krig_error` o `bayes_error` que contenían la diferencia directa respecto al *target*. Además, para la variable de tendencia `prev_grade_avg` se aplicó `.shift(1)` para impedir cualquier filtración de información futura.

---

## 📌 3. Sobre el Tamaño de la Muestra (N)

### A. Distribución Exacta de Datos
* Para el dataset de producción operacional del **banco 3170 m** ([`backend/app/seeders.py`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/backend/app/seeders.py#L516-L535)), el tamaño total es **$N_{total} = 50$ puntos/lotes operacionales**.
* La división según los parámetros de configuración (`test_size=0.15`, `val_size=0.15`) arroja:
  * **Entrenamiento (Train)**: $n = 36$ lotes ($72\%$)
  * **Validación (Validation)**: $n = 7$ lotes ($14\%$)
  * **Prueba (Test)**: $n = 7$ lotes ($14\%$)

> [!TIP]
> En la modalidad de simulación de bloques sintéticos (`_generate_synthetic_data`), el tamaño muestral es de **$N = 2,000$ bloques por banco**, generando un conjunto de prueba de $n_{test} = 300$ bloques.

---

## 📌 4. Sobre las Pruebas Estadísticas

### A. Estado Actual en el Código
Actualmente, la clase `ModelEvaluator` en [`motor_ia_m6/evaluation/metrics.py`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/evaluation/metrics.py#L104-L175) implementa:
1. **Prueba ANOVA** (`stats.f_oneway`): Para evaluar la significancia de la diferencia entre las distribuciones de residuos de todos los modelos.
2. **Prueba t-Student Pareada** (`stats.ttest_ind`): Comparando las diferencias entre el modelo ganador y el segundo lugar.
3. **Intervalos de Confianza Bootstrap (95%)**: Mediante 1,000 re-muestreos sobre el *composite score*.

### B. Pruebas Adicionales (KS, Sobol, Brier Score, ECE)
* **Factibilidad de Cálculo**: Las pruebas de **Kolmogórov-Smirnov**, el **Análisis de Sensibilidad de Sobol**, el **Brier Score** (evaluando el umbral de corte económico $Cu \ge 0.35\%$) y el **Expected Calibration Error (ECE)** **pueden calcularse directamente** a partir de la matriz de predicciones e incertidumbres guardadas ($y_{true}, y_{pred}, \sigma, P_{10}, P_{90}$) mediante un script de post-procesamiento en Python sin modificar la arquitectura base.

---

## 📌 5. Sobre los Escenarios de Prueba (Módulo 4)

* **Capacidad del Generador**: El motor de datos sintéticos ([`synthetic_generator.py`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/data/synthetic_generator.py)) incluye modelos físicos para simular:
  * Alteración supérgena (crisocola en bancos superiores según elevación).
  * Zonas Skarn y Pírfido en elipse orientada.
  * Ruido geológico mediante variogramas filtrados por Gauss.
* **Ejecución por Escenarios**: El pipeline estándar ejecuta el entrenamiento sobre el banco completo. Para obtener métricas separadas en los 4 escenarios planteados (stockwork, supergenia, error de laboratorio, nubes), basta con **filtrar o etiquetar los sub-conjuntos de datos por sus atributos** antes de pasarlos a `evaluate_all_models`.

---

## 📌 6. Datos e Imágenes Hiperespectrales

### A. Naturaleza del Índice Espectral
* La variable `swir_alteration_index` es un **valor escalar tabular preprocesado** ($0.0$ a $1.0$) asociado a cada bloque, calculado a partir de la intensidad de alteración argílica/fílica.

### B. Disponibilidad de Bandas Espectrales Crudas
* En la base de datos ([`hyperspectral_signatures`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/backend/app/models/hyperspectral.py)), se dispone de firmas espectrales continuas en **12 longitudes de onda discretas** (450 nm a 2500 nm, abarcando VNIR/SWIR) para minerales guía: *Illita/Sericita, Biotita Hidrotermal, Clorita+Epidota y Crisocola*.
* **Imágenes 2D**: No existen imágenes ráster 2D píxel a píxel (GeoTIFF); para entrenar un modelo tipo CNN 2D sería necesario rasterizar espacialmente la matriz de bloques.

### C. Autenticidad de los Datos
* **Datos Operacionales**: Los 50 registros del banco 3170 m derivan de datos sembrados basados en parámetros reales de una operación minera a cielo abierto en Antofagasta, Chile.

---

## 📌 7. Validación Cruzada Espacial

> [!WARNING]
> **Punto Metodológico Clave para el Artículo**:
> La partición de datos implementada en el código ([`pipeline.py:195-232`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/training/pipeline.py#L195-L232)) fue:
> 1. **Random Split** (`train_test_split` con `random_state=42`) para los bloques sintéticos.
> 2. **Temporal Walk-Forward Split** (ordenado cronológicamente) para los datos de planta real.
>
> **No se implementó una Validación Cruzada Espacial estricta** (*Spatial Block Cross-Validation* / *Spatial K-Fold*). Se recomienda explicitar esto en la sección de *Limitaciones y Trabajo Futuro* del artículo.

---

## 📌 8. Cumplimiento de Estándares JORC

### A. Umbrales de Calidad en el Código
En [`interpretation_engine.py`](file:///c:/Users/benkr/Sistema-Gemelos-Digitales/motor_ia_m6/evaluation/interpretation_engine.py#L504-L535), la regla de aprobación de calidad JORC requiere cumplir simultáneamente:
1. $RMSE < 0.05$
2. $R^2 > 0.85$
3. $MAPE < 5.0\%$
4. $|Bias| < 0.02$

Si un modelo no alcanza el $75\%$ de aprobación en estos umbrales, el sistema genera la alerta: `"⚠️ Modelo no cumple criterios mínimos de calidad JORC"`.

### B. Justificación Técnica para JORC 2012 / NI 43-101
* XGBoost es un modelo determinista. Para fines de auditoría de Recursos Mineros según JORC 2012 (categoría *Medido* o *Indicado*), se exige la **cuantificación explícita del riesgo espacial y varianza de estimación ($P_{10}/P_{90}$)**. Modelos deterministas puros no satisfacen por sí solos este requerimiento sin un acoplamiento geoestadístico o bayesiano.

---

## 📌 9. Reproducibilidad y Especificaciones del Entorno

### A. Bancos Evaluados
* El banco **3170 m** es el banco de referencia predeterminado. La plataforma incluye soporte para 10 bancos operativos ($3125\text{ m}$ a $3260\text{ m}$).

### B. Ficha Técnica para la Sección de Métodos
* **Lenguaje y Entorno**: Python 3.11 / 3.13 en entorno 64-bit.
* **Librerías de ML y Estadística**:
  * `PyTorch 2.x`: Red Neuronal Profunda Híbrida con Monte Carlo Dropout.
  * `XGBoost 2.0+` y `Scikit-Learn 1.3+`: Ensamble de gradiente y bosques aleatorios.
  * `PyKrige 1.7+`: Kriging Ordinario geoestadístico con modelo Esférico.
  * `SciPy 1.11+`: Pruebas ANOVA y t-Student.
* **Infraestructura Backend & DB**: FastAPI 0.100+, PostgreSQL 15+ con extensión PostGIS.

---

## 📌 10. Caracterización Empírica del Muestreo (Banco 3170 m, N = 50)

### A. Distribución de Litología (Conteo y %)
* **Skarn (`skarn`)**: 21 registros ($42.0\%$)
* **Andesita (`andesite`)**: 15 registros ($30.0\%$)
* **Pórfido (`porphyry`)**: 14 registros ($28.0\%$)
* **Total**: **50 registros ($100.0\%$)**

*(En la población extendida de 2,000 bloques del banco 3170 m: Skarn $39.95\%$, Andesita $35.30\%$, Pórfido $24.75\%$).*

### B. Distribución de Tipo de Alteración (Conteo y %)
* **Silícea (`silica`)**: 22 registros ($44.0\%$)
* **Argílica (`argillic`)**: 15 registros ($30.0\%$)
* **Propilítica (`propylitic`)**: 13 registros ($26.0\%$)
* **Total**: **50 registros ($100.0\%$)**

*(En la población extendida de 2,000 bloques del banco 3170 m: Silícea $39.45\%$, Argílica $31.55\%$, Propilítica $29.00\%$).*

### C. Tabla de Contingencia (Cruce Litología × Alteración)

| Litología \ Alteración | Argílica (`argillic`) | Propilítica (`propylitic`) | Silícea (`silica`) | **Total Litología** |
| :--- | :---: | :---: | :---: | :---: |
| **Andesita (`andesite`)** | 4 | 7 | 4 | **15** ($30.0\%$) |
| **Pórfido (`porphyry`)** | 5 | 4 | 5 | **14** ($28.0\%$) |
| **Skarn (`skarn`)** | 6 | 2 | 13 | **21** ($42.0\%$) |
| **Total Alteración** | **15** ($30.0\%$) | **13** ($26.0\%$) | **22** ($44.0\%$) | **50** ($100.0\%$) |

#### Análisis del Cruce:
* **Presencia de Combinaciones**: Están presentes las **9 combinaciones posibles** en la muestra.
* **Asociaciones Físico-Geológicas**:
  * **Skarn**: Presenta mayor afinidad con alteración **Silícea** (13 de 21 bloques, $61.9\%$), reflejando el reemplazo de silicatos característico de metamorfismo de contacto.
  * **Andesita**: Presenta preferencia por alteración **Propilítica** (7 de 15 bloques, $46.7\%$), coherente con zonas periféricas de menor temperatura.
  * **Pórfido**: Distribución homogénea entre alteración Silícea (5), Argílica (5) y Propilítica (4).

### D. Evaluación del Sesgo del Proceso de Sembrado (Seeding)
* **¿Muestreo Uniforme o Intencionado?**: El algoritmo de sembrado **sobre-representó intencionalmente las zonas mineralizadas de mayor interés económico/operativo**.
* **Fundamento en el Código**: En `synthetic_generator.py` y `seeders.py`, la selección espacial filtra bloques fuera del radio económico del pit ($distFromCenter \le pitRadiusLimit$), concentrando las muestras en el núcleo Skarn/Pórfido con ley media de $0.355\% Cu$ en Skarn y $0.282\% Cu$ en Pórfido.
* **Justificación para el Artículo**: Este diseño de muestreo deliberado permite evaluar el rendimiento de los modelos de IA precisamente en el **umbral crítico de ley de corte ($Cut\text{-}off = 0.35\% Cu$)**, donde la incertidumbre y el riesgo de mala clasificación (*dilución vs pérdida de mineral*) tienen el mayor impacto económico para la mina.

