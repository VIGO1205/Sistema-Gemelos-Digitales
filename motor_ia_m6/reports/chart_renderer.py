"""
Renderizador de graficos a PNG de alta resolucion para incrustar en reportes PDF
Genera imagenes temporales de 300 DPI con estilo profesional
"""

import matplotlib
matplotlib.use('Agg')  # Backend no-interactivo para generar imagenes sin display

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MODELS, MODEL_COLORS


# Configuracion profesional de matplotlib para reportes
REPORT_COLORS = {
    'bg': '#ffffff',
    'bg_secondary': '#f8fafc',
    'text': '#1e293b',
    'text_muted': '#64748b',
    'grid': '#e2e8f0',
    'accent_gold': '#b45309',
    'accent_green': '#15803d',
    'accent_red': '#dc2626',
    'accent_blue': '#0369a1',
}

CHART_COLORS = ['#b45309', '#15803d', '#0369a1', '#7c3aed', '#db2777']


def setup_report_style():
    """Configura matplotlib para graficos de reporte (fondo blanco, alta resolucion)"""
    plt.rcParams.update({
        'figure.facecolor': REPORT_COLORS['bg'],
        'axes.facecolor': REPORT_COLORS['bg'],
        'axes.edgecolor': REPORT_COLORS['grid'],
        'axes.labelcolor': REPORT_COLORS['text'],
        'axes.titlecolor': REPORT_COLORS['text'],
        'axes.grid': True,
        'grid.color': REPORT_COLORS['grid'],
        'grid.linewidth': 0.8,
        'grid.alpha': 0.8,
        'xtick.color': REPORT_COLORS['text_muted'],
        'ytick.color': REPORT_COLORS['text_muted'],
        'xtick.labelcolor': REPORT_COLORS['text'],
        'ytick.labelcolor': REPORT_COLORS['text'],
        'lines.linewidth': 2.2,
        'lines.markersize': 7,
        'lines.markeredgewidth': 1.5,
        'legend.facecolor': REPORT_COLORS['bg'],
        'legend.edgecolor': REPORT_COLORS['grid'],
        'legend.labelcolor': REPORT_COLORS['text'],
        'legend.framealpha': 0.95,
        'text.color': REPORT_COLORS['text'],
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size': 10,
        'axes.titlesize': 13,
        'axes.labelsize': 11,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.facecolor': REPORT_COLORS['bg'],
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.15,
    })


class ChartRenderer:
    """Renderiza todos los graficos necesarios para un reporte"""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="m6_charts_")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        setup_report_style()
        self.chart_paths = {}
    
    def render_all(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """Renderiza todos los graficos y retorna rutas a los archivos PNG"""
        benchmark = report_data.get('benchmark')
        predictions = report_data.get('predictions')
        stability = report_data.get('stability')
        bootstrap = report_data.get('bootstrap')
        
        if benchmark is not None and not benchmark.empty:
            self._render_rmse_comparison(benchmark)
            self._render_r2_comparison(benchmark)
            self._render_composite_ranking(benchmark)
        
        if predictions is not None:
            self._render_prediction_vs_real(predictions, benchmark)
            self._render_residuals(predictions)
            self._render_residual_histograms(predictions)
        
        if bootstrap:
            self._render_bootstrap_ci(bootstrap)
        
        if stability:
            self._render_stability(stability)
        
        cv = report_data.get('cross_validation')
        if cv and cv.get('long') is not None and not cv['long'].empty:
            self._render_cross_validation(cv)
        
        stat = report_data.get('stat_tests')
        if stat and stat.get('bootstrap'):
            self._render_stat_tests(stat)
        
        hp = report_data.get('hyperparameters')
        if hp and hp.get('table') is not None and not hp['table'].empty:
            self._render_hyperparameters(hp)
        
        return self.chart_paths
    
    def _save_chart(self, name: str, fig) -> str:
        """Guarda una figura como PNG de alta resolucion"""
        path = os.path.join(self.output_dir, f"{name}.png")
        fig.savefig(path, format='png', dpi=300)
        plt.close(fig)
        self.chart_paths[name] = path
        return path
    
    def _render_rmse_comparison(self, benchmark: pd.DataFrame):
        """Grafico de barras horizontal: RMSE por modelo"""
        fig, ax = plt.subplots(figsize=(8, 4.5))
        
        models = benchmark['model_name'].values
        rmse_vals = benchmark['rmse'].values
        colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(models))]
        
        bars = ax.barh(models, rmse_vals, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
        
        # Resaltar ganador
        winner_idx = benchmark['is_winner'].values.argmax()
        bars[winner_idx].set_edgecolor(REPORT_COLORS['accent_gold'])
        bars[winner_idx].set_linewidth(3)
        
        # Etiquetas de valor
        for bar, val in zip(bars, rmse_vals):
            ax.text(val + 0.001, bar.get_y() + bar.get_height()/2,
                   f'{val:.4f}', va='center', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('RMSE (% Cu)', fontweight='bold')
        ax.set_title('Precision Predictiva por Modelo (RMSE - menor es mejor)', fontweight='bold', pad=15)
        ax.set_xlim(0, max(rmse_vals) * 1.2)
        
        self._save_chart('rmse_comparison', fig)
    
    def _render_r2_comparison(self, benchmark: pd.DataFrame):
        """Grafico de barras horizontal: R2 por modelo"""
        fig, ax = plt.subplots(figsize=(8, 4.5))
        
        models = benchmark['model_name'].values
        r2_vals = benchmark['r2'].values
        colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(models))]
        
        bars = ax.barh(models, r2_vals, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
        
        winner_idx = benchmark['is_winner'].values.argmax()
        bars[winner_idx].set_edgecolor(REPORT_COLORS['accent_gold'])
        bars[winner_idx].set_linewidth(3)
        
        for bar, val in zip(bars, r2_vals):
            ax.text(val + 0.02, bar.get_y() + bar.get_height()/2,
                   f'{val:.3f}', va='center', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('R2 (Coeficiente de Determinacion)', fontweight='bold')
        ax.set_title('Capacidad Explicativa por Modelo (R2 - mayor es mejor)', fontweight='bold', pad=15)
        ax.set_xlim(0, 1.05)
        
        self._save_chart('r2_comparison', fig)
    
    def _render_composite_ranking(self, benchmark: pd.DataFrame):
        """Grafico de barras vertical: Ranking por score compuesto"""
        fig, ax = plt.subplots(figsize=(9, 5))
        
        df_sorted = benchmark.sort_values('composite_score', ascending=True)
        models = df_sorted['model_name'].values
        scores = df_sorted['composite_score'].values
        colors = [REPORT_COLORS['accent_gold'] if is_w else CHART_COLORS[i % len(CHART_COLORS)]
                  for i, is_w in enumerate(df_sorted['is_winner'].values)]
        
        bars = ax.barh(models, scores, color=colors, alpha=0.9, edgecolor='white', linewidth=1.5)
        
        # Etiquetas
        for bar, val in zip(bars, scores):
            ax.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                   f'{val:.3f}', va='center', fontsize=10, fontweight='bold')
        
        ax.set_xlabel('Score Compuesto (ponderado)', fontweight='bold')
        ax.set_title('Ranking Final de Modelos por Score Compuesto', fontweight='bold', pad=15)
        ax.set_xlim(0, max(scores) * 1.15)
        
        self._save_chart('composite_ranking', fig)
    
    def _render_prediction_vs_real(self, predictions: Dict, benchmark: Optional[pd.DataFrame] = None):
        """Scatter plot Prediccion vs Real para los 5 modelos"""
        pred_data = predictions['dataframe']
        model_keys = predictions['models']
        
        n_models = len(model_keys)
        n_cols = 3
        n_rows = (n_models + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4 * n_rows))
        if n_models == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if n_rows > 1 else axes.flatten()
        
        for idx, key in enumerate(model_keys):
            ax = axes[idx]
            y_true = pred_data['actual_cu'].values
            y_pred = pred_data[f'pred_{key}'].values
            
            ax.scatter(y_true, y_pred, alpha=0.4, s=15, color=CHART_COLORS[idx % len(CHART_COLORS)],
                      edgecolors='none')
            
            # Linea 1:1
            min_val = min(y_true.min(), y_pred.min())
            max_val = max(y_true.max(), y_pred.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', lw=1.5, alpha=0.7, label='1:1 Ideal')
            
            # R2 en titulo
            r2_val = ""
            if benchmark is not None:
                r2_row = benchmark[benchmark['model_key'] == key]
                if not r2_row.empty:
                    r2_val = f"R2 = {r2_row['r2'].values[0]:.3f}"
            
            ax.set_xlabel('Real (% Cu)')
            ax.set_ylabel('Predicho (% Cu)')
            ax.set_title(f"{MODELS[key]['name']}\n{r2_val}", fontsize=10)
            ax.legend(loc='upper left', fontsize=8)
        
        # Ocultar ejes sobrantes
        for idx in range(n_models, len(axes) if hasattr(axes, '__len__') else 1):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        self._save_chart('prediction_vs_real', fig)
    
    def _render_residuals(self, predictions: Dict):
        """Grafico de residuales vs predicho"""
        pred_data = predictions['dataframe']
        model_keys = predictions['models']
        
        n_models = len(model_keys)
        n_cols = 3
        n_rows = (n_models + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4 * n_rows))
        if n_models == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if n_rows > 1 else axes.flatten()
        
        for idx, key in enumerate(model_keys):
            ax = axes[idx]
            residuals = pred_data[f'residual_{key}'].values
            y_pred = pred_data[f'pred_{key}'].values
            
            ax.scatter(y_pred, residuals, alpha=0.4, s=15, color=CHART_COLORS[idx % len(CHART_COLORS)],
                      edgecolors='none')
            ax.axhline(y=0, color=REPORT_COLORS['accent_red'], linestyle='--', lw=2, alpha=0.8)
            
            ax.set_xlabel('Predicho (% Cu)')
            ax.set_ylabel('Residual (% Cu)')
            ax.set_title(f"{MODELS[key]['name']}", fontsize=10)
        
        for idx in range(n_models, len(axes) if hasattr(axes, '__len__') else 1):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        self._save_chart('residuals', fig)
    
    def _render_residual_histograms(self, predictions: Dict):
        """Histogramas de distribucion de residuales"""
        pred_data = predictions['dataframe']
        model_keys = predictions['models']
        
        n_models = len(model_keys)
        n_cols = 3
        n_rows = (n_models + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4 * n_rows))
        if n_models == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if n_rows > 1 else axes.flatten()
        
        for idx, key in enumerate(model_keys):
            ax = axes[idx]
            residuals = pred_data[f'residual_{key}'].values
            
            ax.hist(residuals, bins=30, color=CHART_COLORS[idx % len(CHART_COLORS)],
                   alpha=0.75, edgecolor='white', density=True)
            
            mean_res = residuals.mean()
            ax.axvline(mean_res, color=REPORT_COLORS['accent_red'], linestyle='--', lw=2,
                      label=f'Media: {mean_res:.4f}')
            
            ax.set_xlabel('Residual (% Cu)')
            ax.set_ylabel('Densidad')
            ax.set_title(f"{MODELS[key]['name']}", fontsize=10)
            ax.legend(fontsize=8)
        
        for idx in range(n_models, len(axes) if hasattr(axes, '__len__') else 1):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        self._save_chart('residual_histograms', fig)
    
    def _render_bootstrap_ci(self, bootstrap_data: List[Dict]):
        """Intervalos de confianza bootstrap para RMSE"""
        fig, ax = plt.subplots(figsize=(9, 5))
        
        y_pos = np.arange(len(bootstrap_data))
        colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(bootstrap_data))]
        
        for i, (br, color) in enumerate(zip(bootstrap_data, colors)):
            ax.errorbar(br['rmse_mean'], i,
                       xerr=[[br['rmse_mean'] - br['ci_lower']], [br['ci_upper'] - br['rmse_mean']]],
                       fmt='o', color=color, ecolor=color, capsize=6, capthick=2.5, markersize=10)
            ax.text(br['rmse_mean'], i + 0.2, f"{br['rmse_mean']:.4f}",
                   ha='center', fontsize=9, fontweight='bold')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels([br['model_name'] for br in bootstrap_data])
        ax.set_xlabel('RMSE (% Cu)', fontweight='bold')
        ax.set_title('Intervalos de Confianza Bootstrap 95% para RMSE', fontweight='bold', pad=15)
        
        self._save_chart('bootstrap_ci', fig)
    
    def _render_stability(self, stability_data: Dict[str, Dict]):
        """Grafico de estabilidad ante perturbaciones"""
        fig, ax = plt.subplots(figsize=(9, 5.5))
        
        for idx, (name, data) in enumerate(stability_data.items()):
            color = CHART_COLORS[idx % len(CHART_COLORS)]
            ax.plot(data['noise_levels'], data['rmse_by_noise'], 'o-',
                   label=MODELS[name]['name'], color=color, linewidth=2.5, markersize=7)
        
        ax.set_xlabel('Nivel de Ruido (desviacion estandar)', fontweight='bold')
        ax.set_ylabel('RMSE (% Cu)', fontweight='bold')
        ax.set_title('Estabilidad del Modelo ante Perturbaciones de Datos', fontweight='bold', pad=15)
        ax.legend(loc='best', framealpha=0.95)
        
        self._save_chart('stability', fig)
    
    def _render_cross_validation(self, cv_data: Dict):
        """Boxplot del RMSE por fold de cada modelo (validacion cruzada repetida)"""
        df_long = cv_data['long']
        fig, ax = plt.subplots(figsize=(9, 5.5))
        
        models_order = df_long['model_name'].unique()
        bp = ax.boxplot(
            [df_long.loc[df_long['model_name'] == m, 'rmse'].values for m in models_order],
            labels=list(models_order), patch_artist=True,
            medianprops=dict(color='#b45309', linewidth=2.5),
            flierprops=dict(markersize=5)
        )
        for patch, color in zip(bp['boxes'], CHART_COLORS):
            patch.set_facecolor(color)
            patch.set_alpha(0.55)
        
        ax.set_xlabel('Modelo', fontweight='bold')
        ax.set_ylabel('RMSE por Fold (% Cu)', fontweight='bold')
        ax.set_title(f"Validación Cruzada Repetida ({cv_data.get('n_total_folds', 0)} folds pareados)",
                     fontweight='bold', pad=15)
        ax.tick_params(axis='x', labelrotation=30)
        plt.tight_layout()
        self._save_chart('cross_validation', fig)
    
    def _render_stat_tests(self, stat_data: Dict):
        """Grafico de bootstrap pareado: diferencia de RMSE (ganador vs rivales) con IC95%"""
        bootstrap = stat_data.get('bootstrap', [])
        if not bootstrap:
            return
        
        fig, ax = plt.subplots(figsize=(9, 5))
        names = [f"{b['winner']} vs {b['rival']}" for b in bootstrap]
        diffs = [b['diff_mean'] for b in bootstrap]
        lows = [b['ci_lower'] for b in bootstrap]
        highs = [b['ci_upper'] for b in bootstrap]
        y = np.arange(len(names))
        colors = ['#15803d' if hi < 0 else '#dc2626' if lo > 0 else '#94a3b8'
                  for lo, hi in zip(lows, highs)]
        
        ax.barh(y, diffs, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
        ax.errorbar(diffs, y,
                    xerr=[np.abs(np.array(diffs) - np.array(lows)),
                          np.abs(np.array(highs) - np.array(diffs))],
                    fmt='none', ecolor='#1e293b', capsize=4)
        ax.axvline(0, color='#dc2626', linestyle='--', linewidth=2)
        ax.set_yticks(y)
        ax.set_yticklabels(names)
        ax.set_xlabel('ΔRMSE (ganador - rival, IC95%)', fontweight='bold')
        ax.set_title('Bootstrap Pareado: Diferencia de RMSE con IC95%', fontweight='bold', pad=15)
        ax.legend(['Δ = 0 (sin diferencia)'])
        ax.grid(True, axis='x', alpha=0.3)
        plt.tight_layout()
        self._save_chart('stat_tests_bootstrap', fig)
    
    def _render_hyperparameters(self, hp_data: Dict):
        """Curvas de validacion de la optimizacion de hiperparametros por modelo"""
        table = hp_data['table']
        fig, axes = plt.subplots(1, len(table), figsize=(max(12, 6 * len(table)), 5))
        if len(table) == 1:
            axes = [axes]
        
        for ax, (_, row) in zip(axes, table.iterrows()):
            evals = row['evaluations']
            if not evals:
                ax.axis('off')
                continue
            rmses = [e.get('val_rmse', np.nan) for e in evals]
            color = CHART_COLORS[len(evals) % len(CHART_COLORS)]
            ax.plot(range(len(evals)), rmses, 'o-', color=color, linewidth=2.2)
            ax.axhline(row['default_rmse'], color='#dc2626', linestyle='--', linewidth=1.5,
                       label=f"default {row['default_rmse']:.3f}")
            ax.set_title(row['model_name'], fontweight='bold')
            ax.set_xlabel('Candidato')
            ax.set_ylabel('val-RMSE (% Cu)')
            ax.legend(fontsize=8)
        
        fig.suptitle('Optimización de Hiperparámetros (curvas de validación)',
                     fontweight='bold', y=1.03)
        plt.tight_layout()
        self._save_chart('hyperparameters', fig)
    
    def cleanup(self):
        """Elimina archivos temporales de graficos"""
        for path in self.chart_paths.values():
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        try:
            os.rmdir(self.output_dir)
        except Exception:
            pass
