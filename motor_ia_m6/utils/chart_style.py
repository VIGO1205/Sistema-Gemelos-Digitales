"""
Utilidades de estilo para graficos matplotlib de alta calidad
Tema oscuro profesional compatible con Streamlit dark mode
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import font_manager as fm
import numpy as np


def setup_professional_style():
    """
    Configura matplotlib para graficos de alta calidad con tema oscuro.
    Debe llamarse UNA VEZ al inicio de la aplicacion.
    """
    # Colores del tema oscuro M-6
    DARK_BG = '#0f172a'
    DARK_BG_SECONDARY = '#1e293b'
    TEXT_COLOR = '#e2e8f0'
    TEXT_COLOR_MUTED = '#94a3b8'
    GRID_COLOR = '#334155'
    ACCENT_GOLD = '#f59e0b'
    
    # Configuracion global de rcParams
    plt.rcParams.update({
        # Figure
        'figure.facecolor': DARK_BG,
        'figure.dpi': 150,
        'figure.autolayout': True,
        
        # Axes
        'axes.facecolor': DARK_BG_SECONDARY,
        'axes.edgecolor': GRID_COLOR,
        'axes.labelcolor': TEXT_COLOR,
        'axes.titlecolor': TEXT_COLOR,
        'axes.grid': True,
        'axes.grid.axis': 'both',
        'axes.axisbelow': True,
        
        # Grid
        'grid.color': GRID_COLOR,
        'grid.linewidth': 0.5,
        'grid.alpha': 0.5,
        
        # Ticks
        'xtick.color': TEXT_COLOR_MUTED,
        'ytick.color': TEXT_COLOR_MUTED,
        'xtick.labelcolor': TEXT_COLOR_MUTED,
        'ytick.labelcolor': TEXT_COLOR_MUTED,
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        
        # Lines
        'lines.linewidth': 2.0,
        'lines.markersize': 6,
        'lines.markeredgewidth': 1.5,
        
        # Legend
        'legend.facecolor': DARK_BG_SECONDARY,
        'legend.edgecolor': GRID_COLOR,
        'legend.labelcolor': TEXT_COLOR,
        'legend.framealpha': 0.9,
        
        # Text
        'text.color': TEXT_COLOR,
        
        # Font
        'font.family': 'sans-serif',
        'font.sans-serif': ['Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
    })
    
    # Aplicar style personalizado
    plt.style.use('dark_background')
    
    # Sobreescribir con nuestros colores especificos
    mpl.rcParams['figure.facecolor'] = DARK_BG
    mpl.rcParams['axes.facecolor'] = DARK_BG_SECONDARY


def create_figure(figsize=(10, 6), title=None, xlabel=None, ylabel=None):
    """
    Crea una figura con estilo profesional pre-configurado
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    
    if title:
        ax.set_title(title, fontweight='bold', pad=15)
    if xlabel:
        ax.set_xlabel(xlabel, fontweight='medium')
    if ylabel:
        ax.set_ylabel(ylabel, fontweight='medium')
    
    # Mejorar spines
    for spine in ax.spines.values():
        spine.set_color('#334155')
        spine.set_linewidth(1.0)
    
    return fig, ax


def style_bar_chart(ax, colors=None, highlight_best=False, best_idx=None):
    """
    Aplica estilo profesional a graficos de barras
    """
    if colors:
        for bar, color in zip(ax.patches, colors):
            bar.set_edgecolor('white')
            bar.set_linewidth(0.5)
            bar.set_alpha(0.85)
    
    if highlight_best and best_idx is not None:
        bars = ax.patches
        if best_idx < len(bars):
            bars[best_idx].set_edgecolor('#f59e0b')
            bars[best_idx].set_linewidth(3)
            bars[best_idx].set_alpha(1.0)
    
    ax.set_axisbelow(True)
    return ax


def style_scatter_plot(ax, color='#38bdf8', alpha=0.6, size=25):
    """
    Aplica estilo profesional a scatter plots
    """
    # El scatter ya se creo, solo mejoramos estetica
    ax.set_axisbelow(True)
    return ax


def add_value_labels(ax, fmt='{:.3f}', rotation=0, offset=5):
    """
    Agrega etiquetas de valor encima de barras
    """
    for bar in ax.patches:
        height = bar.get_height()
        if height > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height + offset,
                fmt.format(height),
                ha='center', va='bottom',
                fontsize=8, fontweight='bold',
                color='white'
            )
    return ax


def color_gradient(n, cmap_name='viridis'):
    """
    Genera una paleta de n colores de un colormap
    """
    cmap = plt.cm.get_cmap(cmap_name)
    return [cmap(i / (n - 1)) for i in range(n)]


# Colores tematicos profesionales
PRO_COLORS = {
    'primary': ['#38bdf8', '#34d399', '#fbbf24', '#f472b6', '#a78bfa', '#fb923c'],
    'warm': ['#f59e0b', '#f97316', '#ef4444', '#dc2626', '#b91c1c'],
    'cool': ['#0ea5e9', '#06b6d4', '#10b981', '#84cc16', '#22c55e'],
    'mining': ['#f59e0b', '#92400e', '#78350f', '#b45309', '#d97706'],  # Tonos cobre/oro
}
