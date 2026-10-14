"""Evaluación preliminar de un CSV para entrenamiento (puntaje 0-10).

El puntaje detecta coherencia interna, pero no certifica origen, muestreo ni
ensayos de laboratorio para uso minero real.

Devuelve un dict con:
- score  : float 0-10
- verdict: str (recomendacion)
- checks : lista de dicts {label, status: 'ok'|'warn'|'error', detail, points}
"""
import numpy as np
import pandas as pd

from config import FEATURES, TARGET

# Columnas que tipicamente causan data leakage (la respuesta ya esta en la feature)
_LEAK_HARD = ["krig_error", "bayes_error", "residual", "resid", "prediction_error"]
_LEAK_SOFT = ["epistemic_unc", "aleatoric", "total_unc", "blasthole_density", "_unc"]

_MANDATORY = ["x", "y", "z", "cu_base"]


def _score_drillholes(df: pd.DataFrame) -> dict:
    """Control específico de ensayos: sólo las coordenadas predicen Cu.

    El archivo no contiene una segunda ley de Cu, fechas ni bloques mineros.
    La puntuación permite experimentos espaciales, nunca certifica QA/QC.
    """
    checks = []
    errors = []
    points = 0.0
    n = len(df)
    required = ("hole_id", "x", "y", "z", TARGET)
    missing = [c for c in required if c not in df.columns]
    if missing or not n:
        errors.append("columnas_obligatorias")
        checks.append({"label": "Ensayos de sondajes", "status": "error",
                       "detail": f"Faltan {missing}; filas: {n}.", "points": 0.0})
    else:
        numeric = df.loc[:, list(required)].apply(pd.to_numeric, errors="coerce")
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            errors.append("valores_obligatorios")
            checks.append({"label": "Ensayos de sondajes", "status": "error",
                           "detail": "Hay identificadores, coordenadas o leyes no finitos.", "points": 0.0})
        else:
            points += 2.0
            checks.append({"label": "Ensayos de sondajes", "status": "ok",
                           "detail": "Identificador, tres coordenadas y ley medida completos.", "points": 2.0})
            grade = numeric[TARGET]
            if grade.nunique() < 2:
                errors.append("objetivo_invalido")
                checks.append({"label": "Variación de Cu", "status": "error",
                               "detail": "La ley de Cu es constante.", "points": 0.0})
            else:
                points += 2.0
                checks.append({"label": "Variación de Cu", "status": "ok",
                               "detail": "La ley medida varía entre muestras.", "points": 2.0})
            high_ratio = float((grade > 10).mean())
            if (grade < 0).any() or (grade > 100).any() or high_ratio >= 0.10:
                errors.append("ley_o_unidades")
                checks.append({"label": "Rango de Cu", "status": "error",
                               "detail": f"{high_ratio:.1%} supera 10 % Cu; comprobar unidades.", "points": 0.0})
            else:
                points += 1.0
                checks.append({"label": "Rango de Cu", "status": "ok",
                               "detail": "Valores entre 0 y 100 % Cu, sin concentración masiva >10 %.", "points": 1.0})
            copied = [c for c in ("x", "y", "z") if np.isclose(
                numeric[c], grade, rtol=1e-6, atol=1e-8).mean() >= 0.995]
            if copied:
                errors.append("fuga_del_objetivo")
                checks.append({"label": "Objetivo copiado", "status": "error",
                               "detail": f"Cu coincide con {copied}.", "points": 0.0})
            holes = numeric["hole_id"].nunique()
            if n >= 1000 and holes >= 20:
                points += 2.0
                checks.append({"label": "Cobertura de sondajes", "status": "ok",
                               "detail": f"{n:,} muestras en {holes} sondajes; separar por sondaje.", "points": 2.0})
            else:
                errors.append("muestra_insuficiente")
                checks.append({"label": "Cobertura de sondajes", "status": "error",
                               "detail": f"Sólo {n:,} muestras en {holes} sondajes (mínimo 1 000 y 20).", "points": 0.0})
            duplicates = int(numeric.duplicated(["x", "y", "z"]).sum())
            if duplicates:
                errors.append("coordenadas_duplicadas")
                checks.append({"label": "Coordenadas únicas", "status": "error",
                               "detail": f"{duplicates} posiciones repetidas.", "points": 0.0})
            else:
                points += 1.0
                checks.append({"label": "Coordenadas únicas", "status": "ok",
                               "detail": "Cada muestra tiene una posición distinta.", "points": 1.0})
            if all(numeric[c].nunique() > 1 for c in ("x", "y", "z")):
                points += 1.0
                checks.append({"label": "Cobertura espacial", "status": "ok",
                               "detail": "Las tres coordenadas varían.", "points": 1.0})
            else:
                errors.append("coordenadas_constantes")
                checks.append({"label": "Cobertura espacial", "status": "error",
                               "detail": "Alguna coordenada es constante.", "points": 0.0})
    checks.append({"label": "Alcance de uso", "status": "warn",
                   "detail": "Sin fechas, tonelaje, banco, QA/QC ni CRS verificable: sólo estimación espacial exploratoria.",
                   "points": 0.0})
    score = round(min(points, 8.0 if not errors else 2.9), 1)
    return {"score": score, "raw_score": round(points, 1),
            "score_cap": 8.0 if not errors else 2.9,
            "verdict": ("Apto para entrenamiento espacial exploratorio; no para operación"
                        if not errors and score >= 7.0 else "No apto para entrenar: fallos críticos"),
            "n_rows": n, "checks": checks, "critical_errors": errors,
            "usable_for_training": not errors and score >= 7.0,
            "real_world_validated": False, "training_scope": "drillholes_exploratory"}


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    """Convierte números sin dejar que cadenas no numéricas pasen inadvertidas."""
    return pd.to_numeric(df[column], errors="coerce")


def _unique_ratio(s: pd.Series) -> float:
    if s.dtype == object or s.dtype.name == "category":
        vals = s.astype(str).fillna("")
    else:
        vals = s.dropna()
    if len(vals) == 0:
        return 0.0
    try:
        return vals.nunique() / len(vals)
    except Exception:
        return 0.5


def score_dataset(df: pd.DataFrame) -> dict:
    if "hole_id" in df.columns and "cu_base" not in df.columns:
        return _score_drillholes(df)
    checks: list = []
    total = 0.0
    score_cap = 10.0
    critical_errors = []
    n = len(df)

    # 1) Columnas obligatorias (2.0 pts)
    missing = [c for c in _MANDATORY if c not in df.columns]
    if missing or n == 0:
        checks.append({
            "label": "Columnas obligatorias",
            "status": "error",
            "detail": f"Faltan: {', '.join(missing)}." if missing else "El archivo no tiene filas.",
            "points": 0.0,
        })
        critical_errors.append("columnas_obligatorias")
        score_cap = min(score_cap, 2.9)
    else:
        invalid = {c: int((~np.isfinite(_numeric(df, c).to_numpy(dtype=float))).sum())
                   for c in _MANDATORY}
        invalid = {c: count for c, count in invalid.items() if count}
        if invalid:
            checks.append({
                "label": "Columnas obligatorias (x, y, z, cu_base)",
                "status": "error",
                "detail": f"Valores no numéricos o no finitos: {invalid}.",
                "points": 0.0,
            })
            critical_errors.append("valores_obligatorios")
            score_cap = min(score_cap, 2.9)
        else:
            checks.append({
                "label": "Columnas obligatorias (x, y, z, cu_base)",
                "status": "ok",
                "detail": "Presentes con números finitos.",
                "points": 2.0,
            })
            total += 2.0

    # 2) Target (1.5 pts)
    if TARGET in df.columns and n:
        target = _numeric(df, TARGET)
        valid_target = target[np.isfinite(target.to_numpy(dtype=float))]
        if len(valid_target) == n and valid_target.nunique() >= 2:
            checks.append({
                "label": f"Objetivo {TARGET}",
                "status": "ok",
                "detail": "Presente y variable; su procedencia medida aún debe verificarse.",
                "points": 1.5,
            })
            total += 1.5
        else:
            checks.append({
                "label": f"Objetivo {TARGET}",
                "status": "error",
                "detail": "Contiene valores inválidos o no tiene variación.",
                "points": 0.0,
            })
            critical_errors.append("objetivo_invalido")
            score_cap = min(score_cap, 2.9)
    else:
        checks.append({
            "label": f"Objetivo {TARGET}",
            "status": "error",
            "detail": "Falta una ley independiente: copiar cu_base produciría un objetivo ficticio.",
            "points": 0.0,
        })
        critical_errors.append("objetivo_ausente")
        score_cap = min(score_cap, 2.9)

    # 3) Cobertura de features del modelo (1.5 pts)
    present_feats = [f for f in FEATURES if f in df.columns]
    ratio_feats = len(present_feats) / len(FEATURES)
    if ratio_feats == 1.0:
        feature_points = 1.5
        checks.append({
            "label": f"Features del modelo ({len(FEATURES)}/{len(FEATURES)})",
            "status": "ok",
            "detail": "Todas las features definidas en config.py estan presentes.",
            "points": feature_points,
        })
    elif ratio_feats >= 0.7:
        feature_points = 1.0
        checks.append({
            "label": f"Features del modelo ({len(present_feats)}/{len(FEATURES)})",
            "status": "warn",
            "detail": f"Faltan: {', '.join(set(FEATURES) - set(present_feats))}. El modelo perdera poder predictivo.",
            "points": feature_points,
        })
    else:
        feature_points = 0.3 * ratio_feats
        checks.append({
            "label": f"Features del modelo ({len(present_feats)}/{len(FEATURES)})",
            "status": "error",
            "detail": "Pocas features: el entrenamiento podria degradarse.",
            "points": feature_points,
        })
    total += feature_points

    # 4) Completitud (sin NaN/Inf) (1.5 pts)
    cols_num = [c for c in df.columns if c not in ("date", "id")]
    finite = 1.0
    try:
        sub = df[cols_num].select_dtypes(include=[np.number])
        if len(sub) > 0:
            mask = np.isfinite(sub.to_numpy(dtype=float))
            finite = mask.sum() / mask.size
    except Exception:
        finite = 0.5
    if finite >= 0.995:
        completeness_points = 1.5
        checks.append({
            "label": "Completitud de datos",
            "status": "ok",
            "detail": f"{finite*100:.1f}% de celdas validas.",
            "points": completeness_points,
        })
    elif finite >= 0.9:
        completeness_points = 1.0
        checks.append({
            "label": "Completitud de datos",
            "status": "warn",
            "detail": f"{finite*100:.1f}% de celdas validas. Se descartaran filas incompletas.",
            "points": completeness_points,
        })
    else:
        completeness_points = 0.3
        checks.append({
            "label": "Completitud de datos",
            "status": "error",
            "detail": f"{finite*100:.1f}% celdas validas: demasiados vacios/errores.",
            "points": completeness_points,
        })
    total += completeness_points

    # 5) Volumen de datos (1.0 pt); una muestra pequeña no puede aprobar.
    size_pts = 1.0 if n >= 50000 else 0.8 if n >= 20000 else 0.6 if n >= 5000 else 0.4 if n >= 1000 else 0.2 if n >= 100 else 0.0
    checks.append({
        "label": "Volumen de muestras",
        "status": "ok" if n >= 5000 else ("warn" if n >= 1000 else "error"),
        "detail": f"{n:,} filas.",
        "points": size_pts,
    })
    total += size_pts
    if n < 1000:
        score_cap = min(score_cap, 2.9 if n < 30 else 6.9)

    # 6) Variabilidad (features con valores repetidos/constantes) (1.5 pts)
    feats_check = [f for f in FEATURES if f in df.columns] or list(df.columns)
    ratios = [_unique_ratio(df[f]) for f in feats_check]
    var_score = float(min(1.5, np.mean(ratios) * 4 * 1.5)) if ratios else 0.0
    const_cols = [f for f, r in zip(feats_check, ratios) if r < 1e-5]
    if var_score >= 1.0 and not const_cols:
        checks.append({
            "label": "Variabilidad de features",
            "status": "ok",
            "detail": f"Promedio {float(np.mean(ratios))*100:.1f}% valores unicos.",
            "points": var_score,
        })
    elif const_cols:
        checks.append({
            "label": "Variabilidad de features",
            "status": "warn",
            "detail": f"Columnas (casi) constantes: {', '.join(const_cols[:5])}. Aportan ruido.",
            "points": 0.6,
        })
    else:
        checks.append({
            "label": "Variabilidad de features",
            "status": "warn",
            "detail": "Baja variabilidad en varias features.",
            "points": var_score,
        })
    total += var_score if not const_cols else 0.6

    # 7) Features temporales (0.5 pts)
    has_time = all(f in df.columns for f in ("days_from_start", "prev_grade_avg"))
    time_span = 0.0
    zero_ratio = 0.0
    t = pd.Series(dtype=float)
    if has_time and n > 0:
        try:
            t = _numeric(df, "days_from_start")
            time_span = float(t.max() - t.min())
            zero_ratio = float((t == 0).mean())
        except Exception:
            time_span = 0.0
    if has_time and n and (zero_ratio >= 0.95 or t.isna().any() or (t < 0).any()):
        checks.append({
            "label": "Contexto temporal",
            "status": "error",
            "detail": f"{zero_ratio:.1%} de days_from_start es cero, o hay días inválidos; el máximo no prueba cobertura temporal.",
            "points": 0.0,
        })
        score_cap = min(score_cap, 6.9)
    elif has_time and time_span >= 20 and ("timestamp" in df.columns or "date" in df.columns):
        date_col = "timestamp" if "timestamp" in df.columns else "date"
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        date_ratio = float(parsed.notna().mean())
        valid_dates = date_ratio >= 0.95 and parsed.nunique() >= 2
        checks.append({
            "label": "Contexto temporal",
            "status": "ok" if valid_dates else "error",
            "detail": (f"{date_col}: {date_ratio:.1%} fechas interpretables; verifica que prev_grade_avg use solo el pasado."
                       if valid_dates else f"{date_col} no permite comprobar una secuencia temporal fiable."),
            "points": 0.5 if valid_dates else 0.0,
        })
        if valid_dates:
            total += 0.5
        else:
            score_cap = min(score_cap, 6.9)
    elif has_time and time_span >= 20:
        checks.append({
            "label": "Contexto temporal",
            "status": "warn",
            "detail": "No hay fecha original para verificar days_from_start ni el promedio de leyes anteriores.",
            "points": 0.0,
        })
        score_cap = min(score_cap, 8.4)
    elif has_time and time_span > 0:
        checks.append({
            "label": "Contexto temporal",
            "status": "warn",
            "detail": f"Solo {int(time_span)} días de cobertura; la serie aporta poco.",
            "points": 0.2,
        })
        total += 0.2
    else:
        checks.append({
            "label": "Contexto temporal",
            "status": "warn",
            "detail": "Sin days_from_start/prev_grade_avg: faltan features de proceso.",
            "points": 0.0,
        })

    # 8) Rango plausible de la ley (0.5 pts)
    grade_columns = [col for col in ("cu_base", TARGET) if col in df.columns]
    grade_values = pd.concat([_numeric(df, col) for col in grade_columns], ignore_index=True) if grade_columns else pd.Series(dtype=float)
    finite_grades = grade_values[np.isfinite(grade_values.to_numpy(dtype=float))]
    outside = int(((finite_grades < 0) | (finite_grades > 100)).sum())
    high_ratio = float((finite_grades > 10).mean()) if len(finite_grades) else 0.0
    pure_ratio = float((finite_grades >= 99).mean()) if len(finite_grades) else 0.0
    range_pts = 0.5 if len(finite_grades) and not outside and high_ratio < 0.01 and pure_ratio == 0 else 0.0
    if range_pts:
        checks.append({
            "label": "Rango de la ley",
            "status": "ok",
            "detail": "Sin concentración masiva de leyes extremas; confirma mineral y unidades con la fuente.",
            "points": 0.5,
        })
    else:
        severe_grade = not len(finite_grades) or outside > 0 or high_ratio >= 0.10 or pure_ratio >= 0.01
        checks.append({
            "label": "Rango de la ley",
            "status": "error" if severe_grade else "warn",
            "detail": (f"{high_ratio:.1%} supera 10 % Cu; {pure_ratio:.1%} llega a 99 % Cu; "
                       f"{outside} valores quedan fuera de 0–100 %. Verifica mineral, unidades y ensayos."),
            "points": 0.0,
        })
        if severe_grade:
            critical_errors.append("ley_o_unidades")
            score_cap = min(score_cap, 4.9 if outside == 0 else 2.9)
        else:
            score_cap = min(score_cap, 6.9)
    total += range_pts

    # 9) Deteccion de data leakage (penaliza fuerte)
    leak_hard = [c for c in df.columns if any(s in str(c).lower() for s in _LEAK_HARD)]
    leak_soft = [c for c in df.columns if any(s in str(c).lower() for s in _LEAK_SOFT)]
    if leak_hard:
        checks.append({
            "label": "Posible data leakage",
            "status": "warn",
            "detail": f"Columnas de error/residuo: {', '.join(leak_hard[:5])}. Verifica que no se incluyan entre las variables del modelo.",
            "points": 0.0,
        })
    elif leak_soft:
        checks.append({
            "label": "Variables de incertidumbre/ruido",
            "status": "warn",
            "detail": f"Columnas como {', '.join(leak_soft[:4])} pueden correlacionarse con la respuesta. Considera omitirlas del entrenamiento.",
            "points": 0.0,
        })
    else:
        checks.append({
            "label": "Sin columnas de residuo por nombre",
            "status": "ok",
            "detail": "No se detectaron nombres de error/residuo; aún se comprueban los valores de las entradas.",
            "points": 0.0,
        })

    # Una columna con otro nombre puede contener exactamente la respuesta.
    if TARGET in df.columns and n >= 30:
        target_array = _numeric(df, TARGET).to_numpy(dtype=float)
        copied, nearly_copied = [], []
        for column in present_feats:
            feature_array = _numeric(df, column).to_numpy(dtype=float)
            valid = np.isfinite(target_array) & np.isfinite(feature_array)
            if valid.sum() < max(30, int(0.95 * n)):
                continue
            equal_ratio = float(np.isclose(target_array[valid], feature_array[valid],
                                           rtol=1e-6, atol=1e-8).mean())
            if equal_ratio >= 0.995:
                copied.append(f"{column} ({equal_ratio:.1%})")
            elif equal_ratio >= 0.95:
                nearly_copied.append(f"{column} ({equal_ratio:.1%})")
        if copied:
            checks.append({
                "label": "Objetivo copiado en entradas",
                "status": "error",
                "detail": f"{TARGET} coincide fila a fila con {', '.join(copied)}. Las métricas serían artificiales.",
                "points": 0.0,
            })
            critical_errors.append("fuga_del_objetivo")
            score_cap = min(score_cap, 2.9)
        elif nearly_copied:
            checks.append({
                "label": "Posible copia del objetivo",
                "status": "warn",
                "detail": f"Coincidencia casi exacta: {', '.join(nearly_copied)}; verifica su origen.",
                "points": 0.0,
            })
            score_cap = min(score_cap, 6.9)
        if (np.isfinite(target_array).all() and len(np.unique(target_array)) >= 20
                and np.all(np.diff(target_array) <= 0)):
            checks.append({
                "label": "Orden de las filas",
                "status": "warn",
                "detail": f"Las filas están ordenadas de mayor a menor por {TARGET}; no uses el orden como tiempo.",
                "points": 0.0,
            })
            score_cap = min(score_cap, 8.4)

    # La misma coordenada puede tener varias muestras; sin identificador hay que resolverlas.
    if n and all(col in df.columns for col in ("x", "y", "z", TARGET)):
        spatial = df[["x", "y", "z", TARGET]].apply(pd.to_numeric, errors="coerce")
        spatial = spatial.replace([np.inf, -np.inf], np.nan).dropna()
        if len(spatial):
            grouped = spatial.groupby(["x", "y", "z"], sort=False)[TARGET].agg(["size", "nunique"])
            conflicts = grouped[(grouped["size"] > 1) & (grouped["nunique"] > 1)]
            conflict_rows = int(conflicts["size"].sum())
            if conflict_rows:
                severe = conflict_rows / n >= 0.005
                checks.append({
                    "label": "Coordenadas con leyes distintas",
                    "status": "error" if severe else "warn",
                    "detail": f"{len(conflicts)} posiciones x/y/z repetidas contienen leyes distintas ({conflict_rows} filas). Identifica muestras o versiones.",
                    "points": 0.0,
                })
                score_cap = min(score_cap, 6.9 if severe else 8.4)
            span_x = float(spatial["x"].max() - spatial["x"].min())
            span_y = float(spatial["y"].max() - spatial["y"].min())
            if max(span_x, span_y) > 100_000 and not any(col in df.columns for col in ("mine_id", "site_id", "project_id")):
                checks.append({
                    "label": "Extensión espacial sin identificación de mina",
                    "status": "warn",
                    "detail": f"Extensión x/y de {span_x/1000:.0f} × {span_y/1000:.0f} km si las unidades son metros; verifica CRS y origen.",
                    "points": 0.0,
                })
                score_cap = min(score_cap, 8.4)

    if "tonnage_norm" in df.columns and not any(c in df.columns for c in ("tonnage", "tonnes", "tonelaje")):
        extreme = int((_numeric(df, "tonnage_norm").abs() > 10).sum())
        checks.append({
            "label": "Tonelaje no verificable",
            "status": "warn",
            "detail": f"Solo hay tonelaje normalizado, sin toneladas originales; {extreme} valores superan 10 desviaciones estándar.",
            "points": 0.0,
        })
        score_cap = min(score_cap, 8.4 if extreme == 0 else 7.9)

    rock_col = next((c for c in ("lithology", "rock_type") if c in df.columns), None)
    if rock_col and n:
        unknown = {"", "desconocido", "unknown", "nan", "none", "null", "n/a", "sin dato"}
        rock = df[rock_col].astype("string").str.strip().str.lower()
        unknown_ratio = float((rock.isna() | rock.isin(unknown)).mean())
        if unknown_ratio >= 0.8:
            checks.append({
                "label": "Litología mayormente desconocida",
                "status": "warn",
                "detail": f"{unknown_ratio:.1%} de {rock_col} no identifica la roca.",
                "points": 0.0,
            })
            score_cap = min(score_cap, 7.9)

    # Verdict
    score = round(float(max(0.0, min(10.0, total, score_cap))), 1)
    usable_for_training = not critical_errors and score >= 7.0
    if critical_errors:
        verdict = "No apto para entrenar: fallos críticos"
    elif score >= 8.5:
        verdict = "Calidad automática alta; verifica procedencia"
    elif score >= 7.0:
        verdict = "Calidad automática aceptable con reservas"
    elif score >= 5.0:
        verdict = "Calidad insuficiente; revisa las alertas"
    elif score >= 3.0:
        verdict = "Calidad deficiente; revisa los errores"
    else:
        verdict = "Riesgoso / no recomendado"

    return {
        "score": score,
        "raw_score": round(float(total), 1),
        "score_cap": score_cap,
        "verdict": verdict,
        "n_rows": int(n),
        "checks": checks,
        "critical_errors": critical_errors,
        "usable_for_training": usable_for_training,
        "real_world_validated": False,
    }
