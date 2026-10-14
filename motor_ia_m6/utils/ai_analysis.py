"""
Analisis con IA usando Groq API (modelo Qwen)
Genera interpretaciones avanzadas en lenguaje natural profesional
"""

import os
import json
from typing import Dict, Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def generate_ai_interpretation(df_results, bench: int, model_name: str = "qwen/qwen3.8-27b") -> str:
    """
    Genera una interpretacion avanzada usando el modelo de lenguaje via Groq API.
    
    Args:
        df_results: DataFrame con resultados de benchmark
        bench: Numero de banco
        model_name: Modelo de Groq a usar
    
    Returns:
        Texto de interpretacion en español profesional
    """
    if not HAS_HTTPX:
        raise ImportError("httpx no esta instalado. Instala con: pip install httpx")
    
    # Obtener API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Intentar leer desde backend/.env
        try:
            backend_env = Path(__file__).parent.parent.parent / "backend" / ".env"
            if backend_env.exists():
                with open(backend_env, 'r') as f:
                    for line in f:
                        if line.startswith("GROQ_API_KEY="):
                            api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass
    
    if not api_key:
        raise ValueError("GROQ_API_KEY no encontrada. Configurala en variables de entorno o backend/.env")
    
    # Preparar datos para el prompt
    winner = df_results.loc[df_results['composite_score'].idxmax()]
    best_rmse = df_results.loc[df_results['rmse'].idxmin()]
    best_r2 = df_results.loc[df_results['r2'].idxmax()]
    
    # Crear prompt estructurado
    metrics_text = "\n".join([
        f"- {row['model_name']} ({row['model_type']}): RMSE={row['rmse']:.4f}, R²={row['r2']:.4f}, "
        f"MAE={row['mae']:.4f}, MAPE={row['mape']:.2f}%, Bias={row['bias']:.4f}, Score={row['composite_score']:.4f}"
        for _, row in df_results.iterrows()
    ])
    
    prompt = f"""Eres un experto geoestadístico y data scientist especializado en minería de cobre a cielo abierto. 
Estás evaluando modelos predictivos para un Sistema de Gemelo Digital (M-6) que estima leyes de cobre (% Cu) en bloques mineros.

## DATOS DEL BANCO {bench}m

Resultados de benchmark de 5 modelos predictivos:

{metrics_text}

## GANADORES POR METRICA
- Mejor RMSE (precision): {best_rmse['model_name']} ({best_rmse['rmse']:.4f})
- Mejor R² (explicacion de varianza): {best_r2['model_name']} ({best_r2['r2']:.4f})
- Mejor Score Compuesto (ganador): {winner['model_name']} ({winner['composite_score']:.4f})

## TU TAREA
Genera un análisis profesional en ESPAÑOL de máximo 300 palabras que incluya:

1. **Resumen ejecutivo**: Quién ganó y por qué
2. **Análisis comparativo**: Fortalezas y debilidades de los modelos clásicos vs híbridos
3. **Recomendación operacional**: Si el modelo ganador es apto para planificación minera
4. **Riesgos**: Qué métricas deberían preocupar al geólogo de planificación

Usa lenguaje técnico pero claro. Menciona conceptos como reconciliación Mine-to-Mill, estimación de recursos JORC, y control de dilución cuando sea relevante.
"""
    
    # Llamar a Groq API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "Eres un experto en geoestadística y machine learning aplicado a minería de cobre. Respondes en español técnico profesional."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 800
    }
    
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("GROQ_API_KEY invalida. Verifica tu API key.")
        elif e.response.status_code == 429:
            raise ValueError("Rate limit de Groq alcanzado. Intenta mas tarde.")
        else:
            raise ValueError(f"Error de API Groq: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise ValueError(f"Error conectando con Groq: {str(e)}")


from pathlib import Path


def generate_chart_interpretation(chart_type: str, chart_data: dict, bench: int = None) -> str:
    """
    Genera interpretacion con IA para un grafico especifico usando datos reales.
    
    Args:
        chart_type: Tipo de grafico ('histogram', 'scatter', 'correlation', 'metrics_comparison', etc.)
        chart_data: Diccionario con datos especificos del grafico
        bench: Banco operativo
    
    Returns:
        Texto de interpretacion generado por IA
    """
    if not HAS_HTTPX:
        return "[IA no disponible: instala httpx con 'pip install httpx']"
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            backend_env = Path(__file__).parent.parent.parent / "backend" / ".env"
            if backend_env.exists():
                with open(backend_env, 'r') as f:
                    for line in f:
                        if line.startswith("GROQ_API_KEY="):
                            api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass
    
    if not api_key:
        return "[IA no disponible: configura GROQ_API_KEY en backend/.env]"
    
    # Construir prompt segun tipo de grafico
    data_summary = json.dumps(chart_data, indent=2, ensure_ascii=False)
    
    prompts = {
        'descriptive_stats': """Eres un geólogo experto en análisis de datos mineros.
Interpreta estas estadísticas descriptivas de un dataset de control de procesos.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué indican las estadísticas principales (media, std, min, max)
2. Si hay valores atípicos o datos faltantes
3. Implicaciones para la calidad del dataset
Usa lenguaje técnico profesional.""",
        
        'histogram': """Eres un geólogo experto en análisis de datos mineros. 
Interpreta este histograma de leyes de cobre para un banco de mina a cielo abierto.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué forma tiene la distribución y qué significa geológicamente
2. Si hay valores atípicos o sesgos
3. Implicaciones para la planificación minera
Usa lenguaje técnico profesional.""",

        'upload_copper_histogram': """Interpreta en español (máximo 140 palabras) esta distribución de leyes de cobre.
Datos: {data}
Describe los valores observables: cantidad, media, mediana, percentil 95, rango y diferencias entre series si las hay.
Si son sondajes, son ensayos puntuales; no infieras tonelaje, reservas ni ley de planta.
No afirmes normalidad, enriquecimiento geológico ni errores de laboratorio sólo por la forma del histograma.
Separa observaciones de hipótesis y no inventes umbrales de corte ni bancos operativos.""",

        'upload_spatial_coverage': """Interpreta en español (máximo 140 palabras) este gráfico de cobertura espacial.
Datos: {data}
Describe únicamente la extensión X/Y y qué variable representa el color.
Si son sondajes, los trazos son proyecciones XY de muestras del mismo hoyo y el color representa Z, no Cu.
No deduzcas zonas de alta ley, fallas, orientación de perforación, CRS, unidades, bancos operativos ni calidad de muestreo que los datos no documenten.
Separa claramente observaciones de limitaciones.""",
        
        'spatial_map': """Eres un geólogo estructural. 
Interpreta este mapa espacial/temporal de leyes de cobre.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué patrones observas en la distribución
2. Si hay zonas de enriquecimiento o dispersion
3. Implicaciones para el control de calidad del modelo
Usa lenguaje técnico profesional.""",
        
        'correlation_matrix': """Eres un data scientist especializado en minería.
Interpreta esta matriz de correlación de features.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué features están más correlacionadas con el target
2. Si hay multicolinealidad entre features
3. Recomendaciones para el modelado
Usa lenguaje técnico profesional.""",
        
        'metrics_comparison': """Eres un experto en evaluación de modelos predictivos para minería.
Interpreta estas métricas de comparación de modelos.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Cuál modelo es mejor y por qué
2. Qué métricas son más importantes en este contexto
3. Si las métricas son aceptables para producción
Usa lenguaje técnico profesional.""",
        
        'prediction_vs_real': """Eres un geoestadístico experto.
Interpreta este gráfico de predicción vs valores reales.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué tan bien se ajustan las predicciones a la línea 1:1
2. Si hay sesgos sistemáticos (sobre/subestimación)
3. En qué rango de leyes el modelo funciona mejor/peor
Usa lenguaje técnico profesional.""",
        
        'residuals': """Eres un estadístico aplicado a minería.
Interpreta este análisis de residuales.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Si los residuales están balanceados alrededor de cero
2. Si hay patrones que indican problemas del modelo
3. Recomendaciones para mejorar
Usa lenguaje técnico profesional.""",
        
        'bootstrap': """Eres un experto en incertidumbre y validación de modelos.
Interpreta estos intervalos de confianza bootstrap.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué tan estables son las métricas del modelo
2. Si hay modelos con alta incertidumbre
3. Confianza en la selección del ganador
Usa lenguaje técnico profesional.""",
        
        'stability': """Eres un ingeniero de machine learning robusto.
Interpreta este análisis de estabilidad ante perturbaciones.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Qué tan robusto es cada modelo ante ruido
2. Cuál modelo es más confiable en producción
3. Recomendaciones de despliegue
Usa lenguaje técnico profesional.""",
        
        'winner_diagnostic': """Eres un consultor senior en gemelos digitales mineros.
Interpreta el diagnóstico completo del modelo ganador.
Datos: {data}
Genera una interpretación concisa (max 150 palabras) en español que explique:
1. Si el modelo está listo para activación
2. Qué riesgos tiene
3. Recomendaciones de monitoreo post-despliegue
Usa lenguaje técnico profesional.""",
    }
    
    prompt_template = prompts.get(chart_type, prompts['metrics_comparison'])
    prompt = prompt_template.format(data=data_summary)
    
    if bench:
        prompt += f"\n\nContexto: Banco {bench}m, Mina Esperanza Sur."
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": "Eres un experto en geoestadística y minería de cobre. Respondes en español técnico profesional. Interpretaciones concisas y directas."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 400
    }
    
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Error de IA: {str(e)}]"
