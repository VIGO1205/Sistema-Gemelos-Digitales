"""
Motor de Interpretacion Automatica para Graficos y Metricas del Motor IA M-6
Genera interpretaciones profesionales basadas en reglas deterministicas (auditable)
Compatible con estandares JORC/NI 43-101
"""

import numpy as np
from typing import Dict, List, Tuple, Any


class InterpretationResult:
    """Resultado estructurado de una interpretacion"""
    def __init__(self, text: str, severity: str = "info", icon: str = "ℹ️", action: str = None):
        self.text = text
        self.severity = severity  # success, warning, danger, info
        self.icon = icon
        self.action = action  # Recomendacion de accion
    
    def to_dict(self):
        return {
            'text': self.text,
            'severity': self.severity,
            'icon': self.icon,
            'action': self.action
        }


class InterpretationEngine:
    """
    Motor de interpretacion basado en reglas para metricas de modelos predictivos mineros.
    
    Umbrales basados en experiencia en mineria de cobre a cielo abierto:
    - RMSE < 0.03: Excelente (±0.03% Cu es muy preciso para planificacion)
    - RMSE 0.03-0.05: Bueno
    - RMSE 0.05-0.08: Aceptable
    - RMSE > 0.08: Deficiente
    
    - R2 > 0.90: Excelente explicacion de varianza
    - R2 0.80-0.90: Bueno
    - R2 0.70-0.80: Regular
    - R2 < 0.70: Insuficiente
    
    - MAPE < 3%: Excelente
    - MAPE 3-5%: Bueno
    - MAPE 5-10%: Regular
    - MAPE > 10%: Deficiente
    
    - |Bias| < 0.01: Sin sesgo significativo
    - |Bias| 0.01-0.02: Sesgo leve
    - |Bias| 0.02-0.03: Sesgo moderado
    - |Bias| > 0.03: Sesgo fuerte (riesgo de sobre/sub-estimacion)
    """
    
    # Umbrales de calidad
    THRESHOLDS = {
        'rmse': {'excellent': 4.0, 'good': 5.5, 'acceptable': 9.0},
        'r2': {'excellent': 0.90, 'good': 0.80, 'acceptable': 0.70},
        'mape': {'excellent': 3.0, 'good': 5.0, 'acceptable': 9.0},
        'mae': {'excellent': 2.5, 'good': 3.7, 'acceptable': 6.0},
        'bias': {'excellent': 0.10, 'good': 0.30, 'acceptable': 0.60},
    }
    
    @staticmethod
    def _get_level(value: float, thresholds: Dict[str, float], higher_is_better: bool = False) -> Tuple[str, str, str]:
        """
        Determina nivel de calidad: (nivel, severity, icon)
        """
        if higher_is_better:
            if value >= thresholds['excellent']:
                return 'excelente', 'success', '🟢'
            elif value >= thresholds['good']:
                return 'bueno', 'success', '✅'
            elif value >= thresholds['acceptable']:
                return 'aceptable', 'warning', '⚠️'
            else:
                return 'deficiente', 'danger', '🔴'
        else:
            if value <= thresholds['excellent']:
                return 'excelente', 'success', '🟢'
            elif value <= thresholds['good']:
                return 'bueno', 'success', '✅'
            elif value <= thresholds['acceptable']:
                return 'aceptable', 'warning', '⚠️'
            else:
                return 'deficiente', 'danger', '🔴'
    
    # =================================================================
    # INTERPRETACIONES POR METRICA INDIVIDUAL
    # =================================================================
    
    @classmethod
    def interpret_rmse(cls, rmse: float, context: str = "general") -> InterpretationResult:
        """
        Interpreta el RMSE (Root Mean Square Error)
        """
        level, severity, icon = cls._get_level(rmse, cls.THRESHOLDS['rmse'], higher_is_better=False)
        
        interpretations = {
            'excelente': (
                f"RMSE de {rmse:.4f}% Cu indica **excelente precision predictiva**. "
                f"El error cuadratico medio es muy bajo, lo que significa que las predicciones "
                f"se desvian en promedio solo ±{rmse:.4f}% del valor real. "
                f"Para planificacion minera, este nivel de precision permite estimaciones de tonelaje "
                f"y ley confiables con bajo riesgo de desviacion economica."
            ),
            'bueno': (
                f"RMSE de {rmse:.4f}% Cu es **bueno**. El modelo comete errores moderados "
                f"pero aceptables para la mayoria de aplicaciones operacionales. "
                f"En reconciliacion Mine-to-Mill, este nivel permite identificar zonas de interes "
                f"mineralizado con razonable confianza. Se recomienda monitorear zonas de alta ley "
                f"donde pequenos errores pueden tener alto impacto economico."
            ),
            'aceptable': (
                f"RMSE de {rmse:.4f}% Cu es **aceptable pero mejorable**. "
                f"El error es significativo para decisiones criticas de planificacion. "
                f"Podria indicar que el modelo no captura completamente la variabilidad geologica "
                f"o que hay heterocedasticidad (varianza no constante) en los residuales. "
                f"Se sugiere revisar features de entrada o considerar modelos mas complejos."
            ),
            'deficiente': (
                f"RMSE de {rmse:.4f}% Cu es **deficiente**. El modelo tiene alta incertidumbre "
                f"predictiva que podria generar **riesgo economico significativo** en la planificacion. "
                f"Un error de {rmse:.4f}% en ley de cobre puede traducirse en millones de dolares "
                f"de desviacion en valor del concentrado. **NO se recomienda usar este modelo "
                f"para decisiones criticas sin validacion adicional.**"
            )
        }
        
        actions = {
            'excelente': "Modelo apto para despliegue en produccion. Mantener monitoreo continuo.",
            'bueno': "Apto para operacion. Considerar recalibracion trimestral.",
            'aceptable': "Revisar features de entrada. Evaluar transformaciones o modelos alternativos.",
            'deficiente': "REQUIERE ACCION: Re-entrenar con mas datos, features adicionales o arquitectura diferente."
        }
        
        return InterpretationResult(
            text=interpretations[level],
            severity=severity,
            icon=icon,
            action=actions[level]
        )
    
    @classmethod
    def interpret_r2(cls, r2: float) -> InterpretationResult:
        """Interpreta el coeficiente de determinacion R²"""
        level, severity, icon = cls._get_level(r2, cls.THRESHOLDS['r2'], higher_is_better=True)
        
        variance_explained = r2 * 100
        variance_unexplained = (1 - r2) * 100
        
        interpretations = {
            'excelente': (
                f"R² = {r2:.3f} indica **excelente capacidad explicativa**. "
                f"El modelo explica el **{variance_explained:.1f}% de la varianza** en la ley de cobre. "
                f"Solo un {variance_unexplained:.1f}% de la variabilidad se debe a factores no modelados "
                f"(ruido geologico, errores de muestreo, variabilidad a micro-escala). "
                f"Este nivel es comparable con los mejores modelos de bloques validados JORC."
            ),
            'bueno': (
                f"R² = {r2:.3f} es **bueno**. El modelo captura el **{variance_explained:.1f}% de la varianza**, "
                f"dejando un {variance_unexplained:.1f}% de variabilidad no explicada. "
                f"Es adecuado para estimacion de recursos en categorias Indicada e Inferida. "
                f"Para categorias Medida, considerar aumentar densidad de datos o mejorar features."
            ),
            'aceptable': (
                f"R² = {r2:.3f} es **aceptable pero limitado**. Solo explica el **{variance_explained:.1f}%** "
                f"de la varianza, lo que indica que hay factores importantes no capturados por el modelo. "
                f"El {variance_unexplained:.1f}% restante podria deberse a: (1) variables geologicas omitidas, "
                f"(2) ruido en datos de sondajes, o (3) no-estacionariedad espacial no modelada."
            ),
            'deficiente': (
                f"R² = {r2:.3f} es **deficiente**. El modelo solo explica el **{variance_explained:.1f}%** "
                f"de la varianza, lo que sugiere que **no hay relacion predictiva util** entre los features "
                f"y la ley de cobre. Posibles causas: (1) features irrelevantes, (2) ruido excesivo en datos, "
                f"(3) relacion no lineal no capturada, o (4) dominios geologicos mezclados."
            )
        }
        
        actions = {
            'excelente': "Optimo para estimacion de recursos y reservas.",
            'bueno': "Apto para planificacion operacional.",
            'aceptable': "Agregar features geologicos (alteracion, estructural) o segmentar por dominio.",
            'deficiente': "URGENTE: Revisar completamente el enfoque de modelado. Considerar cambio de paradigma."
        }
        
        return InterpretationResult(
            text=interpretations[level],
            severity=severity,
            icon=icon,
            action=actions[level]
        )
    
    @classmethod
    def interpret_mae(cls, mae: float) -> InterpretationResult:
        """Interpreta el Mean Absolute Error"""
        level, severity, icon = cls._get_level(mae, cls.THRESHOLDS['mae'], higher_is_better=False)
        
        return InterpretationResult(
            text=(
                f"MAE de {mae:.4f}% Cu significa que, en promedio, las predicciones se desvian "
                f"**{mae:.4f} puntos porcentuales** del valor real. "
                f"A diferencia del RMSE, el MAE no penaliza errores grandes de forma desproporcionada, "
                f"por lo que refleja mejor el error 'tipico' de prediccion. "
                + (f" Es un valor {'excelente' if level=='excelente' else level} para control de ley." if level in ['excelente', 'bueno'] else
                   f" Este nivel de error puede afectar la selectividad minera y el blending de mineral." if level == 'aceptable' else
                   f" ERROR CRITICO: Este nivel de desviacion sistematica compromete la viabilidad economica.")
            ),
            severity=severity,
            icon=icon
        )
    
    @classmethod
    def interpret_mape(cls, mape: float) -> InterpretationResult:
        """Interpreta el Mean Absolute Percentage Error"""
        level, severity, icon = cls._get_level(mape, cls.THRESHOLDS['mape'], higher_is_better=False)
        
        if mape < 1.0:
            text = (
                f"MAPE de {mape:.2f}% es **excepcional**. El error porcentual promedio es menor al 1%, "
                f"lo que indica predicciones practicamente perfectas en terminos relativos. "
                f"Esto es raro en mineria y sugiere que el deposito tiene baja variabilidad "
                f"o que los datos son muy representativos."
            )
        else:
            texts = {
                'excelente': (
                    f"MAPE de {mape:.2f}% es **excelente**. El error relativo promedio es bajo, "
                    f"lo que significa que las predicciones mantienen precision tanto en zonas de alta "
                    f"como baja ley. Ideal para control de dilucion y recuperacion metalurgica."
                ),
                'bueno': (
                    f"MAPE de {mape:.2f}% es **bueno**. En zonas de ley media (~0.5% Cu), "
                    f"un error de {mape:.2f}% representa ±{(mape/100)*0.5:.4f}% Cu absoluto. "
                    f"Es aceptable para la mayoria de decisiones operacionales."
                ),
                'aceptable': (
                    f"MAPE de {mape:.2f}% es **moderado**. Atencion: en zonas de baja ley "
                    f"(<0.3% Cu), un MAPE de {mape:.2f}% puede representar errores relativos muy grandes, "
                    f"confundiendo mineral con esteril. Se recomienda analizar MAPE por rango de ley."
                ),
                'deficiente': (
                    f"MAPE de {mape:.2f}% es **alto**. El modelo tiene dificultades para predecir "
                    f"correctamente la ley, especialmente en zonas de bajo tenor donde el error relativo "
                    f"se magnifica. Esto puede generar problemas de clasificacion de material (ore vs waste)."
                )
            }
            text = texts[level]
        
        return InterpretationResult(text=text, severity=severity, icon=icon)
    
    @classmethod
    def interpret_bias(cls, bias: float) -> InterpretationResult:
        """Interpreta el sesgo sistematico"""
        abs_bias = abs(bias)
        level, severity, icon = cls._get_level(abs_bias, cls.THRESHOLDS['bias'], higher_is_better=False)
        
        direction = "sobreestima" if bias > 0 else "subestima"
        
        interpretations = {
            'excelente': (
                f"Sesgo de {bias:+.4f}% Cu es **negligible**. El modelo no tiene tendencia sistematica "
                f"a sobreestimar ni subestimar. Las predicciones son **centrales** (unbiased), "
                f"lo cual es esencial para estimacion de recursos JORC."
            ),
            'bueno': (
                f"Sesgo de {bias:+.4f}% Cu es **leve**. El modelo {direction} ligeramente las leyes. "
                f"En reconciliacion Mine-to-Mill, esto puede compensarse con un factor de correccion. "
                f"No representa riesgo significativo para la toma de decisiones."
            ),
            'aceptable': (
                f"Sesgo de {bias:+.4f}% Cu es **moderado**. El modelo {direction} consistentemente. "
                f"Si se {direction}n las leyes, la planificacion podria clasificar incorrectamente tonelaje "
                f"como mineral cuando es esteril (o viceversa). Se recomienda aplicar correccion de sesgo "
                f"antes de usar en produccion."
            ),
            'deficiente': (
                f"Sesgo de {bias:+.4f}% Cu es **FUERTE**. El modelo {direction} sistematicamente las leyes "
                f"en {abs_bias:.4f} puntos porcentuales. Esto es **INACEPTABLE** para planificacion: "
                f"podria resultar en envio de esteril a la planta (perdida de costos de procesamiento) "
                f"o dejar mineral en la mina (perdida de ingresos). **REQUIERE RECALIBRACION INMEDIATA.**"
            )
        }
        
        actions = {
            'excelente': "Sin accion requerida.",
            'bueno': f"Aplicar correccion de {abs_bias:.4f}% si es necesario para alta precision.",
            'aceptable': f"Aplicar correccion de sesgo de {-bias:.4f}% antes de despliegue.",
            'deficiente': f"URGENTE: Investigar causa del sesgo. Revisar calibracion de datos de entrada."
        }
        
        return InterpretationResult(
            text=interpretations[level],
            severity=severity,
            icon=icon,
            action=actions[level]
        )
    
    @classmethod
    def interpret_residuals(cls, residuals: np.ndarray) -> InterpretationResult:
        """
        Interpreta la distribucion de residuales
        """
        skewness = float(np.mean(((residuals - residuals.mean()) / residuals.std()) ** 3))
        kurtosis = float(np.mean(((residuals - residuals.mean()) / residuals.std()) ** 4) - 3)
        pct_positive = float(np.mean(residuals > 0) * 100)
        
        # Determinar calidad
        if abs(skewness) < 0.5 and abs(kurtosis) < 1.0 and 45 < pct_positive < 55:
            severity = "success"
            icon = "🟢"
            text = (
                f"Distribucion de residuales **ideal**: simetria={skewness:.2f}, curtosis={kurtosis:.2f}. "
                f"Los residuales estan balanceados ({pct_positive:.1f}% positivos), lo que confirma "
                f"que el modelo no tiene sesgo sistematico. La forma cercana a Gauss indica que "
                f"el error es aleatorio y no contiene patrones no modelados."
            )
        elif abs(skewness) < 1.0 and abs(kurtosis) < 2.0 and 40 < pct_positive < 60:
            severity = "success"
            icon = "✅"
            text = (
                f"Distribucion de residuales **aceptable**: simetria={skewness:.2f}, curtosis={kurtosis:.2f}. "
                f"El {pct_positive:.1f}% de residuales son positivos, indicando balance razonable. "
                f"Pequenas desviaciones de la normalidad pueden deberse a outliers geologicos legítimos."
            )
        else:
            severity = "warning"
            icon = "⚠️"
            issues = []
            if abs(skewness) >= 1.0:
                issues.append(f"asimetria significativa ({skewness:+.2f})")
            if abs(kurtosis) >= 2.0:
                issues.append(f"colas pesadas (curtosis={kurtosis:+.2f})")
            if pct_positive <= 40 or pct_positive >= 60:
                issues.append(f"desbalance ({pct_positive:.1f}% positivos)")
            
            text = (
                f"Distribucion de residuales con **anomalias**: {', '.join(issues)}. "
                f"Esto sugiere que el modelo no captura completamente la estructura de los datos. "
                f"Patrones en residuales indican informacion sistematica que podria usarse para mejorar el modelo."
            )
        
        return InterpretationResult(text=text, severity=severity, icon=icon)
    
    @classmethod
    def interpret_stability(cls, noise_levels: List[float], rmse_by_noise: List[float], 
                           model_name: str = "Modelo") -> InterpretationResult:
        """
        Interpreta el analisis de estabilidad ante perturbaciones
        """
        initial_rmse = rmse_by_noise[0]
        final_rmse = rmse_by_noise[-1]
        max_rmse = max(rmse_by_noise)
        degradation = (final_rmse - initial_rmse) / initial_rmse * 100 if initial_rmse > 0 else 0
        
        # Determinar si es lineal o exponencial
        diffs = np.diff(rmse_by_noise)
        is_accelerating = np.mean(diffs[-3:]) > np.mean(diffs[:3]) * 1.5
        
        if degradation < 20:
            severity = "success"
            icon = "🛡️"
            text = (
                f"**{model_name} es ROBUSTO**. Degradacion del RMSE de solo {degradation:.1f}% "
                f"ante ruido maximo de {noise_levels[-1]}. El modelo mantiene su precision "
                f"incluso con datos ruidosos, lo que indica buena generalizacion y bajo riesgo "
                f"de overfitting. Ideal para condiciones operacionales reales donde los datos "
                f"de sondajes tienen error de muestreo."
            )
        elif degradation < 50 and not is_accelerating:
            severity = "success"
            icon = "✅"
            text = (
                f"**{model_name} es ACEPTABLE**. Degradacion del {degradation:.1f}%. "
                f"Mantiene rendimiento razonable ante perturbaciones moderadas. "
                f"Adecuado para operacion con control de calidad de datos de entrada."
            )
        elif is_accelerating:
            severity = "warning"
            icon = "⚠️"
            text = (
                f"**{model_name} muestra FRAGILIDAD CRECIENTE**. La degradacion se acelera "
                f"con niveles altos de ruido (de {initial_rmse:.4f} a {max_rmse:.4f}). "
                f"Esto sugiere que el modelo ha capturado ruido como si fuera senal (overfitting). "
                f"Recomendacion: aumentar regularizacion o reducir complejidad del modelo."
            )
        else:
            severity = "danger"
            icon = "🔴"
            text = (
                f"**{model_name} es FRAGIL**. Degradacion del {degradation:.1f}% ante ruido. "
                f"El RMSE se dispara de {initial_rmse:.4f} a {max_rmse:.4f}. "
                f"Este modelo probablemente sufre de overfitting severo y no generalizara bien "
                f"a datos reales con incertidumbre de muestreo. **NO recomendado para produccion.**"
            )
        
        return InterpretationResult(text=text, severity=severity, icon=icon)
    
    @classmethod
    def interpret_bootstrap_ci(cls, rmse_mean: float, ci_lower: float, ci_upper: float,
                               model_name: str = "Modelo") -> InterpretationResult:
        """Interpreta intervalos de confianza bootstrap"""
        ci_width = ci_upper - ci_lower
        relative_width = (ci_width / rmse_mean * 100) if rmse_mean > 0 else 0
        
        if relative_width < 10:
            severity = "success"
            icon = "🎯"
            text = (
                f"**{model_name} tiene alta precision en la estimacion de RMSE**. "
                f"IC 95% estrecho: [{ci_lower:.4f}, {ci_upper:.4f}] (amplitud relativa {relative_width:.1f}%). "
                f"Esto indica que con los datos disponibles, la metrica es estable y reproducible. "
                f"Baja incertidumbre en la evaluacion del modelo."
            )
        elif relative_width < 20:
            severity = "success"
            icon = "✅"
            text = (
                f"**{model_name} tiene precision moderada en RMSE**. "
                f"IC 95%: [{ci_lower:.4f}, {ci_upper:.4f}] (amplitud relativa {relative_width:.1f}%). "
                f"La estimacion es razonablemente estable."
            )
        elif relative_width < 30:
            severity = "warning"
            icon = "⚠️"
            text = (
                f"**{model_name} tiene incertidumbre moderada**. "
                f"IC 95% amplio: [{ci_lower:.4f}, {ci_upper:.4f}] (amplitud relativa {relative_width:.1f}%). "
                f"La metrica RMSE varia significativamente segun la muestra bootstrap, "
                f"indicando que el dataset de test es pequeno o heterogeneo."
            )
        else:
            severity = "warning"
            icon = "🔴"
            text = (
                f"**{model_name} tiene ALTA incertidumbre en RMSE**. "
                f"IC 95% muy amplio: [{ci_lower:.4f}, {ci_upper:.4f}] (amplitud relativa {relative_width:.1f}%). "
                f"La evaluacion del modelo es poco confiable. Se necesitan mas datos de test "
                f"o una validacion cruzada mas rigurosa."
            )
        
        return InterpretationResult(text=text, severity=severity, icon=icon)
    
    @classmethod
    def interpret_composite_ranking(cls, model_name: str, score: float, rank: int,
                                     total_models: int) -> InterpretationResult:
        """Interpreta el ranking por score compuesto"""
        if rank == 1:
            severity = "info"
            icon = "📊"
            text = (
                f"**{model_name} ocupa el primer lugar entre {total_models} modelos evaluados** "
                f"con score compuesto de {score:.4f}. El score sirve para ordenar estos modelos; "
                f"no es un porcentaje de acierto ni certifica uso operativo. "
                f"Revisa R² y RMSE/MAE en datos reservados frente a una referencia simple "
                f"antes de considerar cualquier despliegue."
            )
        elif rank == 2:
            severity = "info"
            icon = "📊"
            text = (
                f"**{model_name} ocupa el segundo lugar** con score de {score:.4f}. "
                f"La posición es relativa; comprueba sus métricas y su diferencia frente a una referencia simple."
            )
        elif rank <= total_models // 2:
            severity = "info"
            icon = "📊"
            text = (
                f"**{model_name} ocupa el lugar {rank}** con score de {score:.4f}. "
                f"La posición no permite juzgar por sí sola su utilidad predictiva."
            )
        else:
            severity = "warning"
            icon = "📉"
            text = (
                f"**{model_name} ocupa el lugar {rank} de {total_models}** con score de {score:.4f}. "
                f"Compáralo con una referencia simple y revisa sus errores antes de descartarlo."
            )
        
        return InterpretationResult(text=text, severity=severity, icon=icon)
    
    # =================================================================
    # INTERPRETACIONES AGREGADAS
    # =================================================================
    
    @classmethod
    def interpret_model_full(cls, metrics: Dict[str, float], model_name: str = "Modelo") -> List[InterpretationResult]:
        """
        Genera interpretacion completa de un modelo a partir de todas sus metricas
        """
        results = []
        
        # Metricas individuales
        if 'rmse' in metrics:
            results.append(cls.interpret_rmse(metrics['rmse']))
        if 'r2' in metrics:
            results.append(cls.interpret_r2(metrics['r2']))
        if 'mae' in metrics:
            results.append(cls.interpret_mae(metrics['mae']))
        if 'mape' in metrics:
            results.append(cls.interpret_mape(metrics['mape']))
        if 'bias' in metrics:
            results.append(cls.interpret_bias(metrics['bias']))
        
        # Interpretacion agregada (umbrales alineados con cls.THRESHOLDS, escala del dataset)
        scores = []
        if 'rmse' in metrics:
            scores.append(1 if metrics['rmse'] < cls.THRESHOLDS['rmse']['good'] else 0)
        if 'r2' in metrics:
            scores.append(1 if metrics['r2'] > 0.85 else 0)
        if 'mape' in metrics:
            scores.append(1 if metrics['mape'] < cls.THRESHOLDS['mape']['acceptable'] else 0)
        if 'bias' in metrics:
            scores.append(1 if abs(metrics['bias']) < cls.THRESHOLDS['bias']['good'] else 0)
        
        if len(scores) >= 3 and sum(scores) == len(scores):
            results.append(InterpretationResult(
                text=f"🌟 **{model_name} aprueba todos los criterios de calidad JORC**. "
                     f"Es candidato para estimacion de recursos en categoria Indicada o superior.",
                severity="success",
                icon="⭐"
            ))
        elif len(scores) >= 3 and sum(scores) >= len(scores) * 0.75:
            results.append(InterpretationResult(
                text=f"✅ **{model_name} cumple la mayoria de criterios de calidad**. "
                     f"Apto para planificacion operacional y estimacion Inferida.",
                severity="success",
                icon="✅"
            ))
        else:
            results.append(InterpretationResult(
                text=f"⚠️ **{model_name} no cumple criterios minimos de calidad JORC**. "
                     f"Requiere mejoras antes de usar en estimacion formal de recursos.",
                severity="warning",
                icon="⚠️"
            ))
        
        return results
    
    @classmethod
    def interpret_model_comparison(cls, results_df, rank_metric='composite_score') -> InterpretationResult:
        """
        Interpreta comparacion entre modelos
        """
        # Manejar NaN: filtrar antes de idxmin/idxmax
        df_valid = results_df.dropna(subset=['rmse', 'r2', 'composite_score'])
        if df_valid.empty:
            return InterpretationResult(
                text="⚠️ No se pueden comparar modelos: todas las métricas contienen valores nulos. Verifica los datos de entrenamiento.",
                severity="warning",
                icon="⚠️"
            )
        
        best_rmse = df_valid.loc[df_valid['rmse'].idxmin()]
        best_r2 = df_valid.loc[df_valid['r2'].idxmax()]
        if rank_metric == 'rmse':
            return InterpretationResult(
                text=(f"Menor RMSE en sondajes no vistos: **{best_rmse['model_name']}** "
                      f"({best_rmse['rmse']:.4f} % Cu; R²={best_rmse['r2']:.4f}). "
                      "Compare también MAE y repita la evaluación con otros grupos de sondajes. "
                      "El Score compuesto es orientativo y no representa porcentaje de acierto."),
                severity="info", icon="📊"
            )
        winner = df_valid.loc[df_valid['composite_score'].idxmax()]
        
        # Verificar si el ganador domina o es mixto
        same_winner = (winner['model_name'] == best_rmse['model_name'] == best_r2['model_name'])
        
        if same_winner:
            text = (
                f"🏆 **Dominancia clara**: {winner['model_name']} gana en TODAS las metricas principales "
                f"(mejor RMSE, mejor R2, y mejor Score Compuesto). Este es un caso ideal donde "
                f"un solo modelo supera a todos los demas consistentemente. La decision de seleccion es obvia."
            )
        else:
            text = (
                f"🤝 **Victoria por consenso**: El ganador por Score Compuesto es **{winner['model_name']}**, "
                f"pero no domina en todas las metricas. "
                f"Mejor RMSE: {best_rmse['model_name']} ({best_rmse['rmse']:.4f}). "
                f"Mejor R2: {best_r2['model_name']} ({best_r2['r2']:.4f}). "
                f"Esto indica que diferentes modelos capturan diferentes aspectos de la variabilidad geologica. "
                f"Considerar un ensemble ponderado como alternativa."
            )
        
        return InterpretationResult(text=text, severity="info", icon="📊")
    
    # =================================================================
    # INTERPRETACIONES DE VALIDACION CRUZADA, PRUEBAS ESTADISTICAS E HIPERPARAMETROS
    # =================================================================
    
    @classmethod
    def interpret_cross_validation(cls, cv_df, n_folds: int) -> InterpretationResult:
        """
        Interpreta la tabla resumen de validacion cruzada (media +/- std y IC95).
        cv_df: DataFrame con columnas model/rmse_mean/rmse_std/ci...
        """
        import pandas as pd
        if cv_df is None or cv_df.empty:
            return InterpretationResult(
                text="No hay resultados de validacion cruzada para este banco.",
                severity="info", icon="ℹ️"
            )
        
        best = cv_df.loc[cv_df['rmse_mean'].idxmin()]
        kriging_row = cv_df[cv_df['model'] == 'kriging']
        gain = 0.0
        
        # Distancia del mejor modelo respecto al baseline kriging
        if not kriging_row.empty:
            k_rmse = kriging_row['rmse_mean'].values[0]
            gain = (k_rmse - best['rmse_mean']) / k_rmse * 100
            baseline_txt = (f" Frente al baseline geostatistico (Kriging, RMSĒ={k_rmse:.3f}), "
                            f"el ganador de CV reduce el error un **{gain:.1f}%**.")
        else:
            baseline_txt = ""
        
        stable = best['rmse_std'] / best['rmse_mean'] < 0.15 if best['rmse_mean'] else False
        stab_txt = (" La baja dispersion entre folds (coef. variacion<15%) indica un modelo **estable** "
                    "ante distintas particiones de los datos." if stable else
                    " La dispersion entre folds es notable, se recomienda revisar la estabilidad del modelo.")
        
        return InterpretationResult(
            text=(
                f"🔀 **Validación cruzada repetida ({n_folds} folds):** el modelo con menor "
                f"RMSE promedio es **{best['model']}** (RMSĒ = {best['rmse_mean']:.4f} ± "
                f"{best['rmse_std']:.4f}, IC95% [{best['ci_lower']:.4f}, {best['ci_upper']:.4f}])."
                f"{baseline_txt}{stab_txt}"
            ),
            severity="success" if gain >= 10 else "info",
            icon="🔀",
            action="Documentar que la seleccion se confirma (o descarta) con CV pareada, no solo con el split unico."
        )
    
    @classmethod
    def interpret_statistical_tests(cls, stat: Dict) -> InterpretationResult:
        """
        Interpreta el bloque de pruebas estadisticas (Friedman, Wilcoxon+Bonferroni, bootstrap pareado).
        """
        if not stat:
            return InterpretationResult(
                text="No hay pruebas estadisticas disponibles para este banco.",
                severity="info", icon="ℹ️"
            )
        
        friedman = stat.get('friedman', {})
        bootstrap = stat.get('bootstrap', [])
        wilcoxon = stat.get('wilcoxon', [])
        
        parts = []
        if friedman.get('p_value') is not None:
            sig = friedman.get('significant', False)
            parts.append(
                f"**Friedman**: χ²={friedman.get('statistic', 0):.3f}, p={friedman.get('p_value', 1):.4f} "
                f"sobre {friedman.get('n_folds', 0)} folds pareados → "
                + ("existen **diferencias estadisticamente significativas** entre los modelos (p<0.05)."
                   if sig else "no se detectan diferencias estadisticamente significativas entre los modelos (p≥0.05).")
            )
        
        # Pares significativos despues de Bonferroni
        sig_pairs = [w for w in wilcoxon if w.get('significant')]
        if sig_pairs:
            melhor_pairs = []
            for w in sig_pairs:
                mejor = w['model_a'] if w['mean_rmse_a'] <= w['mean_rmse_b'] else w['model_b']
                melhor_pairs.append(f"{mejor}")
            parts.append(
                f"**Wilcoxon pareado + Bonferroni**: después de corregir por "
                f"{len(wilcoxon)} comparaciones, los modelos **{', '.join(sorted(set(melhor_pairs)))}** "
                f"resultaron significativamente superiores a sus rivales."
            )
        else:
            parts.append(
                "**Wilcoxon pareado + Bonferroni**: tras la correccion por comparaciones multiples, "
                "ninguna diferencia entre pares alcanza significancia estadistica."
            )
        
        # Bootstrap pareado ganador vs rivales
        if bootstrap:
            better = [b for b in bootstrap if b.get('ci_upper') is not None and b['ci_upper'] < 0]
            worse = [b for b in bootstrap if b.get('ci_lower') is not None and b['ci_lower'] > 0]
            inconclusive = [b for b in bootstrap if b not in better and b not in worse]
            if better:
                rivals = ", ".join(b['rival'] for b in better)
                parts.append(
                    f"**Bootstrap pareado (IC95% de ΔRMSE)**: el ganador **{bootstrap[0]['winner']}** "
                    f"tiene menor RMSE que **{rivals}** (IC de ganador − rival totalmente negativo)."
                )
            if worse:
                rivals = ", ".join(b['rival'] for b in worse)
                parts.append(
                    f"**Bootstrap pareado (IC95% de ΔRMSE)**: el supuesto ganador "
                    f"**{bootstrap[0]['winner']}** tiene mayor RMSE que **{rivals}** "
                    f"(IC totalmente positivo)."
                )
            if inconclusive:
                rivals = ", ".join(b['rival'] for b in inconclusive)
                parts.append(
                    f"**Bootstrap pareado (IC95% de ΔRMSE)**: la comparación con "
                    f"**{rivals}** no es concluyente (el IC incluye 0)."
                )
        
        text = "\n\n".join(parts)
        has_sig = friedman.get('significant', False) or bool(sig_pairs) or bool(
            [b for b in bootstrap if b.get('ci_upper') is not None and b['ci_upper'] < 0])
        winner_worse = any(b.get('ci_lower') is not None and b['ci_lower'] > 0 for b in bootstrap)
        return InterpretationResult(
            text=f"🧪 **Pruebas estadísticas (datos reales):**\n{text}",
            severity="warning" if winner_worse else "success" if has_sig else "info",
            icon="🧪",
            action="Incluir estas pruebas en el reporte para respaldar la seleccion del modelo ganador."
        )
    
    @classmethod
    def interpret_hyperparameters(cls, tuning: Dict) -> InterpretationResult:
        """
        Interpreta los resultados de la optimizacion de hiperparametros.
        tuning: dict por modelo con best_params/best_rmse/default_rmse/improvement_pct.
        """
        results = tuning.get('tuning', {}) if 'tuning' in tuning else tuning
        if not results:
            return InterpretationResult(
                text="La optimizacion de hiperparametros no se ejecuto para este banco.",
                severity="info", icon="ℹ️"
            )
        
        parts = []
        total_improve = 0.0
        count = 0
        for key, r in results.items():
            if not isinstance(r, dict) or 'best_rmse' not in r:
                continue
            improve = r.get('improvement_pct', 0.0)
            total_improve += improve
            count += 1
            params_txt = ", ".join(f"{k}={v}" for k, v in r.get('best_params', {}).items())
            parts.append(
                f"**{key}**: mejor con {{{params_txt}}} → val-RMSE {r['best_rmse']:.4f} "
                f"(vs default {r['default_rmse']:.4f}, méjora {improve:.1f}%)."
            )
        
        text = "\n".join(parts)
        avg = total_improve / count if count else 0.0
        return InterpretationResult(
            text=(
                f"🔧 **Optimización de hiperparámetros (validación):**\n{text}\n\n"
                f"En promedio la sintonización mejoró el val-RMSE un **{avg:.1f}%** frente a los "
                f"valores por defecto, lo que demuestra que los modelos finales fueron configurados "
                f"con evidencia y no con valores arbitrarios."
            ),
            severity="success" if avg > 0 else "info",
            icon="🔧",
            action="Reportar los parametros finales usados por cada modelo en el anexo tecnico."
        )
