"""
Generador de Reportes Excel profesionales multi-hoja
Formato formal con colores, bordes, filtros y graficos incrustados
"""

import io
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def generate_excel_report(report_data: Dict[str, Any], bench: int) -> bytes:
    """
    Genera un reporte Excel profesional con 5 hojas.
    
    Returns:
        bytes del archivo Excel listo para descargar
    """
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    
    # ============================================================
    # ESTILOS PERSONALIZADOS
    # ============================================================
    
    # Colores del tema M-6
    COPPER = '#b45309'
    COPPER_LIGHT = '#f59e0b'
    DARK_BG = '#1e293b'
    WHITE = '#ffffff'
    GREEN = '#15803d'
    RED = '#dc2626'
    GRAY = '#64748b'
    
    # Formatos
    fmt_title = workbook.add_format({
        'bold': True, 'font_size': 16, 'font_color': COPPER,
        'bg_color': WHITE, 'align': 'center', 'valign': 'vcenter',
        'border': 0
    })
    fmt_subtitle = workbook.add_format({
        'bold': True, 'font_size': 12, 'font_color': DARK_BG,
        'bg_color': WHITE, 'align': 'left', 'valign': 'vcenter'
    })
    fmt_header = workbook.add_format({
        'bold': True, 'font_size': 11, 'font_color': WHITE,
        'bg_color': COPPER, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'border_color': COPPER
    })
    fmt_header_winner = workbook.add_format({
        'bold': True, 'font_size': 11, 'font_color': WHITE,
        'bg_color': GREEN, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'border_color': GREEN
    })
    fmt_cell = workbook.add_format({
        'font_size': 10, 'font_color': DARK_BG,
        'align': 'center', 'valign': 'vcenter',
        'border': 1, 'border_color': '#e2e8f0'
    })
    fmt_cell_left = workbook.add_format({
        'font_size': 10, 'font_color': DARK_BG,
        'align': 'left', 'valign': 'vcenter',
        'border': 1, 'border_color': '#e2e8f0'
    })
    fmt_winner = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': GREEN,
        'bg_color': '#f0fdf4', 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'border_color': GREEN
    })
    fmt_number = workbook.add_format({
        'font_size': 10, 'font_color': DARK_BG,
        'align': 'center', 'valign': 'vcenter',
        'border': 1, 'border_color': '#e2e8f0',
        'num_format': '0.0000'
    })
    fmt_number_2 = workbook.add_format({
        'font_size': 10, 'font_color': DARK_BG,
        'align': 'center', 'valign': 'vcenter',
        'border': 1, 'border_color': '#e2e8f0',
        'num_format': '0.00'
    })
    fmt_text_wrap = workbook.add_format({
        'font_size': 9, 'font_color': DARK_BG,
        'align': 'left', 'valign': 'top', 'text_wrap': True,
        'border': 1, 'border_color': '#e2e8f0'
    })
    fmt_section = workbook.add_format({
        'bold': True, 'font_size': 13, 'font_color': WHITE,
        'bg_color': COPPER, 'align': 'left', 'valign': 'vcenter'
    })
    
    benchmark = report_data.get('benchmark')
    predictions = report_data.get('predictions')
    interpretations = report_data.get('interpretations', {})
    metadata = report_data.get('metadata', {})
    
    # ============================================================
    # HOJA 1: RESUMEN EJECUTIVO
    # ============================================================
    ws_summary = workbook.add_worksheet('Resumen Ejecutivo')
    ws_summary.set_tab_color(COPPER)
    
    row = 0
    ws_summary.merge_range(row, 0, row, 7, f'MOTOR IA M-6 - REPORTE DE BENCHMARK', fmt_title)
    row += 2
    
    ws_summary.write(row, 0, 'Banco:', fmt_subtitle)
    ws_summary.write(row, 1, f"{metadata.get('bench', bench)} m", fmt_cell_left)
    row += 1
    ws_summary.write(row, 0, 'Fecha:', fmt_subtitle)
    ws_summary.write(row, 1, metadata.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), fmt_cell_left)
    row += 1
    ws_summary.write(row, 0, 'Metodologia:', fmt_subtitle)
    ws_summary.write(row, 1, metadata.get('methodology', 'CRISP-DM'), fmt_cell_left)
    row += 1
    ws_summary.write(row, 0, 'Motor Version:', fmt_subtitle)
    ws_summary.write(row, 1, metadata.get('motor_version', 'M-6 IA v1.0'), fmt_cell_left)
    row += 2
    
    if benchmark is not None and not benchmark.empty:
        ws_summary.merge_range(row, 0, row, 7, 'TABLA COMPARATIVA DE MODELOS', fmt_section)
        row += 1
        
        # Headers
        headers = ['Modelo', 'Tipo', 'RMSE', 'MAE', 'R2', 'MAPE (%)', 'Bias', 'Score Comp.']
        for col, h in enumerate(headers):
            ws_summary.write(row, col, h, fmt_header)
        row += 1
        
        # Datos
        for _, r in benchmark.iterrows():
            is_winner = r['is_winner']
            fmt = fmt_winner if is_winner else fmt_cell
            fmt_num = fmt_winner if is_winner else fmt_number
            fmt_num2 = fmt_winner if is_winner else fmt_number_2
            
            ws_summary.write(row, 0, r['model_name'], fmt)
            ws_summary.write(row, 1, r['model_type'], fmt)
            ws_summary.write(row, 2, r['rmse'], fmt_num)
            ws_summary.write(row, 3, r['mae'], fmt_num)
            ws_summary.write(row, 4, r['r2'], fmt_num)
            ws_summary.write(row, 5, r['mape'], fmt_num2)
            ws_summary.write(row, 6, r['bias'], fmt_num)
            ws_summary.write(row, 7, r['composite_score'], fmt_num)
            row += 1
        
        # Ganador destacado
        row += 1
        winner = benchmark.loc[benchmark['composite_score'].idxmax()]
        ws_summary.merge_range(row, 0, row, 7,
            f"🏆 MODELO GANADOR: {winner['model_name']} | Score: {winner['composite_score']:.4f} | Tipo: {winner['model_type']}",
            workbook.add_format({'bold': True, 'font_size': 12, 'font_color': GREEN,
                                'bg_color': '#f0fdf4', 'align': 'center', 'valign': 'vcenter'}))
    
    # Ajustar anchos
    ws_summary.set_column(0, 0, 28)
    ws_summary.set_column(1, 1, 12)
    ws_summary.set_column(2, 7, 14)
    
    # ============================================================
    # HOJA 2: BENCHMARK DETALLADO
    # ============================================================
    ws_detail = workbook.add_worksheet('Benchmark Detallado')
    ws_detail.set_tab_color('#0369a1')
    
    if benchmark is not None and not benchmark.empty:
        # Escribir DataFrame con formato
        detail_cols = ['rank', 'model_name', 'model_type', 'rmse', 'mae', 'r2', 'mape', 'bias', 'uncertainty', 'composite_score']
        detail_df = benchmark[detail_cols].copy()
        detail_df.columns = ['Ranking', 'Modelo', 'Tipo', 'RMSE (% Cu)', 'MAE (% Cu)', 'R2', 'MAPE (%)', 'Bias (% Cu)', 'Incertidumbre', 'Score Compuesto']
        
        detail_df.to_excel(writer, sheet_name='Benchmark Detallado', index=False, startrow=1, startcol=0)
        
        # Aplicar formato a la hoja
        ws_detail_obj = writer.sheets['Benchmark Detallado']
        ws_detail_obj.write(0, 0, 'RESULTADOS DETALLADOS DEL BENCHMARK', fmt_section)
        
        for col_num, value in enumerate(detail_df.columns.values):
            is_winner_col = value == 'Modelo'
            ws_detail_obj.write(1, col_num, value, fmt_header)
        
        for row_num in range(len(detail_df)):
            is_winner_row = benchmark.iloc[row_num]['is_winner']
            fmt_row = fmt_winner if is_winner_row else fmt_cell
            fmt_num_row = fmt_winner if is_winner_row else fmt_number
            
            for col_num in range(len(detail_df.columns)):
                val = detail_df.iloc[row_num, col_num]
                if col_num >= 3:  # Columnas numericas
                    ws_detail_obj.write(row_num + 2, col_num, val, fmt_num_row)
                else:
                    ws_detail_obj.write(row_num + 2, col_num, val, fmt_row)
        
        ws_detail_obj.set_column(0, 0, 10)
        ws_detail_obj.set_column(1, 1, 28)
        ws_detail_obj.set_column(2, 2, 12)
        ws_detail_obj.set_column(3, 9, 16)
    
    # ============================================================
    # HOJA 3: PREDICCIONES POR BLOQUE
    # ============================================================
    ws_preds = workbook.add_worksheet('Predicciones')
    ws_preds.set_tab_color('#15803d')
    
    if predictions is not None:
        pred_df = predictions['dataframe']
        
        ws_preds.write(0, 0, 'PREDICCIONES POR BLOQUE (TODOS LOS MODELOS)', fmt_section)
        pred_df.to_excel(writer, sheet_name='Predicciones', index=False, startrow=1, startcol=0)
        
        ws_preds_obj = writer.sheets['Predicciones']
        
        for col_num, value in enumerate(pred_df.columns.values):
            ws_preds_obj.write(1, col_num, value, fmt_header)
        
        for row_num in range(len(pred_df)):
            for col_num in range(len(pred_df.columns)):
                ws_preds_obj.write(row_num + 2, col_num, pred_df.iloc[row_num, col_num], fmt_number)
        
        # Ajustar anchos
        ws_preds_obj.set_column(0, 0, 12)
        ws_preds_obj.set_column(1, len(pred_df.columns)-1, 16)
        
        # Congelar paneles
        ws_preds_obj.freeze_panes(2, 0)
        
        # Filtros automaticos
        ws_preds_obj.autofilter(1, 0, len(pred_df) + 1, len(pred_df.columns) - 1)
    
    # ============================================================
    # HOJA 4: INTERPRETACIONES
    # ============================================================
    ws_interp = workbook.add_worksheet('Interpretaciones')
    ws_interp.set_tab_color('#7c3aed')
    
    row = 0
    ws_interp.merge_range(row, 0, row, 2, 'INTERPRETACIONES AUTOMATICAS DE METRICAS', fmt_section)
    row += 2
    
    # Interpretacion comparativa
    if '__comparison__' in interpretations:
        comp = interpretations['__comparison__'][0]
        ws_interp.merge_range(row, 0, row, 2, 'ANALISIS COMPARATIVO GLOBAL', fmt_subtitle)
        row += 1
        ws_interp.merge_range(row, 0, row, 2, comp['text'], fmt_text_wrap)
        ws_interp.set_row(row, 60)
        row += 2
    
    # Interpretacion del ganador
    if '__winner__' in interpretations:
        win = interpretations['__winner__'][0]
        ws_interp.merge_range(row, 0, row, 2, 'MODELO GANADOR', fmt_subtitle)
        row += 1
        ws_interp.merge_range(row, 0, row, 2, win['text'], fmt_text_wrap)
        ws_interp.set_row(row, 40)
        row += 2
    
    # Interpretaciones por modelo
    ws_interp.merge_range(row, 0, row, 2, 'DIAGNOSTICO POR MODELO', fmt_subtitle)
    row += 1
    
    for model_key, interps in interpretations.items():
        if model_key.startswith('__'):
            continue
        
        model_name = model_key
        ws_interp.merge_range(row, 0, row, 2, f"Modelo: {model_name}", fmt_subtitle)
        row += 1
        
        for interp in interps:
            ws_interp.write(row, 0, interp['icon'], fmt_cell)
            ws_interp.merge_range(row, 1, row, 2, interp['text'], fmt_text_wrap)
            ws_interp.set_row(row, 50)
            row += 1
        
        row += 1
    
    ws_interp.set_column(0, 0, 6)
    ws_interp.set_column(1, 2, 55)
    
    # ============================================================
    # HOJA 5: METADATOS
    # ============================================================
    ws_meta = workbook.add_worksheet('Metadatos')
    ws_meta.set_tab_color(GRAY)
    
    row = 0
    ws_meta.merge_range(row, 0, row, 1, 'METADATOS DEL EXPERIMENTO', fmt_section)
    row += 2
    
    meta_items = [
        ('Banco Operativo (m)', metadata.get('bench', bench)),
        ('Fecha y Hora', metadata.get('timestamp', 'N/A')),
        ('Sistema Operativo', metadata.get('system', 'N/A')),
        ('Version Python', metadata.get('python_version', 'N/A')),
        ('Version del Motor', metadata.get('motor_version', 'N/A')),
        ('Metodologia', metadata.get('methodology', 'CRISP-DM')),
        ('Numero de Features', metadata.get('n_features', 'N/A')),
        ('Features Utilizadas', ', '.join(metadata.get('features_used', []))),
    ]
    
    for label, value in meta_items:
        ws_meta.write(row, 0, label, fmt_subtitle)
        ws_meta.write(row, 1, value, fmt_cell_left)
        row += 1
    
    if predictions:
        row += 1
        ws_meta.write(row, 0, 'Muestras de Test', fmt_subtitle)
        ws_meta.write(row, 1, predictions.get('n_samples', 'N/A'), fmt_cell_left)
        row += 1
        ws_meta.write(row, 0, 'Modelos Evaluados', fmt_subtitle)
        ws_meta.write(row, 1, ', '.join(predictions.get('models', [])), fmt_cell_left)
    
    ws_meta.set_column(0, 0, 25)
    ws_meta.set_column(1, 1, 60)
    
    # ============================================================
    # HOJA 6: VALIDACION CRUZADA
    # ============================================================
    cv_data = report_data.get('cross_validation')
    if cv_data and cv_data.get('summary') is not None and not cv_data['summary'].empty:
        ws_cv = workbook.add_worksheet('Validación Cruzada')
        ws_cv.set_tab_color(COPPER_LIGHT)
        
        ws_cv.merge_range(0, 0, 0, 7,
            f"VALIDACION CRUZADA REPETIDA ({cv_data.get('n_total_folds', 0)} folds pareados "
            f"- {cv_data.get('n_repeats', 3)}x{cv_data.get('n_splits', 5)}-fold)", fmt_section)
        
        headers = ['Modelo', 'RMSE medio', 'Std', 'IC95% inf', 'IC95% sup', 'MAE', 'R2', 'Folds']
        for col, h in enumerate(headers):
            ws_cv.write(1, col, h, fmt_header)
        
        cv_sum = cv_data['summary']
        best_model = cv_sum.loc[cv_sum['rmse_mean'].idxmin(), 'model_name']
        row = 2
        for _, r in cv_sum.iterrows():
            is_best = r['model_name'] == best_model
            fmt = fmt_winner if is_best else fmt_cell
            fmt_num = fmt_winner if is_best else fmt_number
            curr_row = row
            ws_cv.write(curr_row, 0, r['model_name'], fmt)
            ws_cv.write(curr_row, 1, r['rmse_mean'], fmt_num)
            ws_cv.write(curr_row, 2, r['rmse_std'], fmt_num)
            ws_cv.write(curr_row, 3, r['ci_lower'], fmt_num)
            ws_cv.write(curr_row, 4, r['ci_upper'], fmt_num)
            ws_cv.write(curr_row, 5, r['mae_mean'], fmt_num)
            ws_cv.write(curr_row, 6, r['r2_mean'], fmt_num)
            ws_cv.write(curr_row, 7, r['n_folds'], fmt_cell)
            row += 1
        
        row += 1
        ws_cv.merge_range(row, 0, row, 2, f"MEJOR MODELO POR CV: {best_model} (menor RMSE medio)", fmt_subtitle)
        row += 1
        if cv_data.get('interpretation'):
            ws_cv.merge_range(row, 0, row, 7, cv_data['interpretation']['text'], fmt_text_wrap)
            ws_cv.set_row(row, 60)
        
        ws_cv.set_column(0, 0, 28)
        ws_cv.set_column(1, 7, 14)
    
    # ============================================================
    # HOJA 7: PRUEBAS ESTADISTICAS
    # ============================================================
    stat_tests = report_data.get('stat_tests')
    if stat_tests:
        ws_stat = workbook.add_worksheet('Pruebas Estadísticas')
        ws_stat.set_tab_color(RED)
        
        ws_stat.merge_range(0, 0, 0, 5, 'PRUEBAS ESTADISTICAS ROBUSTAS (DATOS REALES)', fmt_section)
        row = 2
        
        friedman = stat_tests.get('friedman', {})
        if friedman.get('p_value') is not None:
            ws_stat.merge_range(row, 0, row, 5, 'TEST DE FRIEDMAN (comparacion global pareada)', fmt_subtitle)
            row += 1
            headers = ['Estadistico chi2', 'p-valor', 'Folds', 'Conclusion', '', '']
            for col, h in enumerate(headers):
                ws_stat.write(row, col, h, fmt_header)
            row += 1
            ws_stat.write(row, 0, friedman.get('statistic', 0.0), fmt_number)
            ws_stat.write(row, 1, friedman.get('p_value', 1.0), fmt_number)
            ws_stat.write(row, 2, friedman.get('n_folds', 0), fmt_cell)
            ws_stat.merge_range(row, 3, row, 5,
                'Diferencias significativas' if friedman.get('significant') else 'Sin diferencias significativas',
                fmt_cell_left)
            row += 2
        
        if stat_tests.get('wilcoxon'):
            ws_stat.merge_range(row, 0, row, 5, 'COMPARACIONES PAREADAS (WILCOXON + BONFERRONI)', fmt_subtitle)
            row += 1
            headers = ['Modelo A', 'Modelo B', 'Estadistico', 'p (crudo)', 'p (Bonferroni)', 'Significativo']
            for col, h in enumerate(headers):
                ws_stat.write(row, col, h, fmt_header)
            row += 1
            for w in stat_tests['wilcoxon']:
                ws_stat.write(row, 0, w['model_a'], fmt_cell)
                ws_stat.write(row, 1, w['model_b'], fmt_cell)
                ws_stat.write(row, 2, round(w['statistic'], 3) if w['statistic'] is not None else '-', fmt_cell)
                ws_stat.write(row, 3, round(w['p_value'], 4) if w['p_value'] is not None else 1.0, fmt_number)
                ws_stat.write(row, 4, round(w['bonferroni_alpha'], 4), fmt_number)
                ws_stat.write(row, 5, 'SI' if w['significant'] else 'NO', fmt_cell)
                row += 1
            row += 1
        
        if stat_tests.get('bootstrap'):
            ws_stat.merge_range(row, 0, row, 5, 'BOOTSTRAP PAREADO (IC95% DE ΔRMSE GANADOR VS RIVAL)', fmt_subtitle)
            row += 1
            headers = ['Ganador', 'Rival', 'ΔRMSE', 'IC95% inf', 'IC95% sup', 'Ganador mejor']
            for col, h in enumerate(headers):
                ws_stat.write(row, col, h, fmt_header)
            row += 1
            for b in stat_tests['bootstrap']:
                ws_stat.write(row, 0, b['winner'], fmt_cell)
                ws_stat.write(row, 1, b['rival'], fmt_cell)
                ws_stat.write(row, 2, round(b['diff_mean'], 5), fmt_number)
                ws_stat.write(row, 3, round(b['ci_lower'], 5), fmt_number)
                ws_stat.write(row, 4, round(b['ci_upper'], 5), fmt_number)
                ws_stat.write(row, 5, 'SI' if b['ci_upper'] < 0 else 'NO', fmt_cell)
                row += 1
            row += 1
        
        if stat_tests.get('interpretation'):
            ws_stat.merge_range(row, 0, row, 5, stat_tests['interpretation']['text'], fmt_text_wrap)
            ws_stat.set_row(row, 60)
        
        ws_stat.set_column(0, 0, 24)
        ws_stat.set_column(1, 5, 22)
    
    # ============================================================
    # HOJA 8: HIPERPARAMETROS
    # ============================================================
    hp_data = report_data.get('hyperparameters')
    if hp_data and hp_data.get('table') is not None and not hp_data['table'].empty:
        ws_hp = workbook.add_worksheet('Hiperparámetros')
        ws_hp.set_tab_color(GREEN)
        
        ws_hp.merge_range(0, 0, 0, 5, 'OPTIMIZACION DE HIPERPARAMETROS (GRIDSEARCH SOBRE VALIDATION)', fmt_section)
        
        headers = ['Modelo', 'Mejores parametros', 'val-RMSE', 'Default', 'Mejora %', 'Candidatos']
        for col, h in enumerate(headers):
            ws_hp.write(1, col, h, fmt_header)
        
        hp_table = hp_data['table']
        row = 2
        for _, r in hp_table.iterrows():
            ws_hp.write(row, 0, r['model_name'], fmt_cell)
            ws_hp.write(row, 1, str(r['best_params']), fmt_cell_left)
            ws_hp.write(row, 2, r['best_rmse'], fmt_number)
            ws_hp.write(row, 3, r['default_rmse'] if pd.notna(r['default_rmse']) else '-', fmt_number)
            ws_hp.write(row, 4, r['improvement_pct'], fmt_number_2)
            ws_hp.write(row, 5, int(r['n_candidates']), fmt_cell)
            row += 1
        
        row += 1
        if hp_data.get('interpretation'):
            ws_hp.merge_range(row, 0, row, 5, hp_data['interpretation']['text'], fmt_text_wrap)
            ws_hp.set_row(row, 60)
        
        if hp_data.get('used'):
            row += 1
            ws_hp.merge_range(row, 0, row, 5, 'PARAMETROS FINALES USADOS POR MODELO', fmt_subtitle)
            row += 1
            for key, params in hp_data['used'].items():
                ws_hp.merge_range(row, 0, row, 1, key, fmt_cell)
                ws_hp.merge_range(row, 2, row, 5, str(params), fmt_text_wrap)
                ws_hp.set_row(row, 40)
                row += 1
        
        ws_hp.set_column(0, 0, 28)
        ws_hp.set_column(1, 1, 42)
        ws_hp.set_column(2, 5, 14)
    
    # Cerrar y retornar bytes
    writer.close()
    output.seek(0)
    return output.getvalue()
