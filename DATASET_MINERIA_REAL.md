# Dataset real GeoMet para el Motor IA M-6

## Archivos y procedencia

- `dataset/drillholes.csv`: archivo original, sin modificar, del [registro GeoMet en Zenodo](https://zenodo.org/records/7051975), versión v4 (DOI 10.5281/zenodo.7051975).
- Su MD5 es `bf48a6b1135113b6e6cf7b32f95315ad`, igual al publicado junto a `drillholes.csv` en Zenodo.
- `dataset/drillholes_m6.csv`: adaptación para el Motor IA. El cargador también puede convertir el CSV original directamente.
- El repositorio identifica las filas como análisis químicos de muestras de sondajes con coordenadas geoespaciales. El CSV no documenta CRS, método de laboratorio, QA/QC, fecha ni toneladas de bloque.

## Conversión

| GeoMet | M-6 | Significado |
| --- | --- | --- |
| `HOLEID` | `hole_id` | Identificador del sondaje; se usa para separar entrenamiento, validación y prueba. |
| `X`, `Y`, `Z` | `x`, `y`, `z` | Coordenadas originales sin transformación. |
| `Cu ppm` | `cu_bayesian` | Ensayo de Cu medido en %: `Cu ppm / 10 000`. El nombre `cu_bayesian` es una convención heredada del motor; aquí **no** es una predicción bayesiana. |

El archivo contiene 2 000 muestras y 119 sondajes. La ley de Cu convertida va de 0 a 6,02 %, con mediana 0,50 %. Las tres coordenadas y la ley están completas; no hay posiciones tridimensionales duplicadas. El original incluye otros elementos químicos, pero el modelo exploratorio **sólo usa `x`, `y`, `z`** para predecir la ley de Cu. La ley medida no se copia a una entrada.

## Uso en la aplicación

1. Abrir **Carga de Datos** y subir `dataset/drillholes_m6.csv`. También se puede subir `dataset/drillholes.csv`: el cargador lo convierte automáticamente.
2. Revisar el control de calidad. La puntuación 8/10 significa que el archivo es apto para un **experimento espacial exploratorio**, no que esté validado para operación.
3. En **Fase 4**, entrenar y comparar modelos. El motor reserva sondajes completos para validación y prueba, evitando intervalos del mismo sondaje en ambos lados. El selector de banco se oculta mientras está cargado GeoMet; el identificador 3170 se usa sólo como clave interna de la sesión.
4. Revisar las métricas en **Fase 5**. La validación cruzada habitual por filas se omite para este conjunto porque mezclaría intervalos de un sondaje.
5. En **Fase 6**, publicar el ganador por menor RMSE como **experimento GeoMet**. En el frontend, abrir **Sondajes GeoMet** para consultar coordenadas X/Y/Z dentro del rango observado. El lote multibanco y la activación operativa de un banco siguen reservados para datos de bloques y planta.

El frontend GeoMet consulta `/api/models/experiments/drillholes/*`, que el backend dirige al servicio `motor-inference`. El artefacto `drillholes_exploratory.joblib` es independiente de `winner_<banco>.joblib` y nunca escribe en `active_models` ni en `process_control_points`. En producción, reconstruir `motor-inference` con las dependencias declaradas antes de publicar un modelo nuevo; el servicio verifica las versiones usadas por `joblib`.

## Límites antes de uso minero real

- Faltan fechas, toneladas, densidad, litología, modelo de bloques, reconciliación de planta y mediciones independientes para construir `cu_base`, `predicted_bayesian`, `tonnage_norm`, `days_from_start` y `prev_grade_avg`.
- No se conoce aquí la referencia geográfica de las coordenadas ni se verificó la cadena de muestreo y QA/QC. No asignar bancos, tiempos o tonelajes sintéticos a estas filas.
- Para este CSV, Kriging y los componentes espaciales de los híbridos usan `x/y/z`. Los componentes Random Forest, XGBoost y NN de los híbridos reciben igualmente las tres coordenadas. El Kriging 3D selecciona de forma reproducible hasta 500 muestras del conjunto de entrenamiento y usa hasta 64 vecinos por predicción para limitar el tiempo de cálculo; los modelos de árboles reciben todas las muestras de entrenamiento.
- Los híbridos separan sondajes completos para ajustar su combinación interna. En Fase 5, comparar primero RMSE, MAE y R²; el Score compuesto es orientativo y no equivale a un porcentaje de acierto.
- Una buena métrica sobre sondajes reservados todavía no demuestra aptitud para estimar recursos, despacho, control de ley de planta ni decisiones económicas.

Para entrenar el flujo operativo de bloques del M-6 se sigue requiriendo `x`, `y`, `z`, `cu_base` y un `cu_bayesian` **medido independientemente**. El cargador ya no rellena objetivos ausentes copiando `cu_base`.
