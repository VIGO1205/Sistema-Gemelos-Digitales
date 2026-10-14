"""
Motor IA M-6 - Aplicacion Streamlit Principal
Dashboard interactivo para entrenamiento, evaluacion y seleccion
 de 5 modelos predictivos para estimacion de ley de cobre.
"""

import hashlib

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys
from pathlib import Path

# Agregar directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent))

from config import MODELS, BENCHES, MODEL_COLORS, DB_CONFIG, TRAIN_CONFIG
from training.pipeline import TrainingPipeline
from evaluation.metrics import ModelEvaluator
from evaluation.statistical_tests import run_statistical_analysis, rmse_bootstrap
from evaluation.diagnostics import stability_curve
from evaluation.archive import evaluation_archive
from evaluation.interpretation_engine import InterpretationEngine
from database.connection import get_benchmark_results, get_active_model, activate_model, send_predictions_to_api
from data.synthetic_generator import generate_realistic_mining_data, generate_multi_bench_dataset
from utils.chart_style import setup_professional_style, create_figure, style_bar_chart, add_value_labels
from reports.report_data import ReportDataCollector
from reports.chart_renderer import ChartRenderer
from reports.excel_generator import generate_excel_report
from reports.pdf_generator import generate_pdf_report
from utils.ai_analysis import generate_chart_interpretation
from dataset_quality import score_dataset

DRILLHOLE_MODEL_REVISION = "geomet-xyz3d-grouped-v1"


def drillhole_dataset_fingerprint(df):
    """Identifica el CSV que produjo los modelos guardados en la sesión."""
    columns = ['hole_id', 'x', 'y', 'z', 'cu_bayesian']
    if df is None or any(column not in df.columns for column in columns):
        return None
    row_hashes = pd.util.hash_pandas_object(df[columns], index=False).to_numpy()
    return hashlib.sha256(row_hashes.tobytes()).hexdigest()

# Inicializar session state
if 'dataset' not in st.session_state:
    st.session_state.dataset = None
if 'dataset_source' not in st.session_state:
    st.session_state.dataset_source = None
if 'dataset_quality' not in st.session_state:
    st.session_state.dataset_quality = None

# Configuracion de pagina
st.set_page_config(
    page_title="Motor IA M-6 - Gemelo Digital",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    /* Sidebar: sigue el tema de Streamlit (claro/oscuro automatico) - solo borde sutil */
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(148, 163, 184, 0.25);
    }
    /* Opcion seleccionada: encapsulada en ambar (visible en ambos temas) */
    [data-testid="stSidebar"] button[kind="primary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important;
        color: #ffffff !important;
        border: 1px solid #d97706 !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(217, 119, 6, 0.35) !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover,
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
        border-color: #f59e0b !important;
        color: #d97706 !important;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #f59e0b;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #334155;
    }
    .winner-badge {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        text-align: center;
    }
    .phase-complete {
        color: #10b981;
        font-weight: bold;
    }
    .phase-pending {
        color: #64748b;
    }

    /* ═══ Cards de Inicio - Modo Claro (default) ═══ */
    .kpi-card {
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid;
        text-align: center;
    }
    .kpi-card .kpi-value { font-size: 2.5rem; font-weight: bold; }
    .kpi-card .kpi-label { font-size: 1rem; margin-top: 0.5rem; font-weight: 600; }
    .kpi-card .kpi-sub { font-size: 0.85rem; margin-top: 0.3rem; }

    .kpi-amber { background: #fef3c7; border-color: #fde68a; }
    .kpi-amber .kpi-value { color: #d97706; }
    .kpi-amber .kpi-label { color: #92400e; }
    .kpi-amber .kpi-sub { color: #a16207; }

    .kpi-blue { background: #dbeafe; border-color: #bfdbfe; }
    .kpi-blue .kpi-value { color: #0284c7; }
    .kpi-blue .kpi-label { color: #1e40af; }
    .kpi-blue .kpi-sub { color: #1d4ed8; }

    .kpi-green { background: #d1fae5; border-color: #a7f3d0; }
    .kpi-green .kpi-value { color: #059669; }
    .kpi-green .kpi-label { color: #065f46; }
    .kpi-green .kpi-sub { color: #047857; }

    .objetivo-box {
        background-color: #f8fafc;
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #d97706;
        border: 1px solid #e2e8f0;
    }
    .twin-card {
        background-color: #f8fafc;
        border-radius: 12px;
        padding: 1.25rem;
        border-left: 4px solid #0284c7;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .fusion-card {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
        height: 100%;
    }
    .fusion-card .fusion-title { font-weight: bold; font-size: 0.88rem; color: #d97706; margin-bottom: 0.3rem; }
    .fusion-card .fusion-desc { font-size: 0.78rem; color: #475569; line-height: 1.4; }
    .flow-card {
        text-align: center;
        padding: 1rem;
        background: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .flow-card .flow-icon { font-size: 1.5rem; }
    .flow-card .flow-title { color: #d97706; font-size: 0.8rem; font-weight: bold; margin-top: 0.25rem; }
    .flow-card .flow-label { color: #475569; font-size: 0.7rem; margin-top: 0.1rem; }

    /* ═══ Cards de Inicio - Modo Oscuro ═══ */
    html[data-m6theme="dark"] .kpi-amber { background: #46290a; border-color: #7c4a03; }
    html[data-m6theme="dark"] .kpi-amber .kpi-value { color: #fbbf24; }
    html[data-m6theme="dark"] .kpi-amber .kpi-label { color: #fef3c7; }
    html[data-m6theme="dark"] .kpi-amber .kpi-sub { color: #fcd34d; }

    html[data-m6theme="dark"] .kpi-blue { background: #16254a; border-color: #27437e; }
    html[data-m6theme="dark"] .kpi-blue .kpi-value { color: #60a5fa; }
    html[data-m6theme="dark"] .kpi-blue .kpi-label { color: #bfdbfe; }
    html[data-m6theme="dark"] .kpi-blue .kpi-sub { color: #93c5fd; }

    html[data-m6theme="dark"] .kpi-green { background: #06372a; border-color: #0b5d47; }
    html[data-m6theme="dark"] .kpi-green .kpi-value { color: #34d399; }
    html[data-m6theme="dark"] .kpi-green .kpi-label { color: #a7f3d0; }
    html[data-m6theme="dark"] .kpi-green .kpi-sub { color: #6ee7b7; }

    html[data-m6theme="dark"] .objetivo-box {
        background-color: rgba(148, 163, 184, 0.10);
        border-left: 4px solid #f59e0b;
        border: 1px solid rgba(148, 163, 184, 0.25);
    }
    html[data-m6theme="dark"] .twin-card {
        background-color: rgba(148, 163, 184, 0.10);
        border-left: 4px solid #38bdf8;
        border: 1px solid rgba(148, 163, 184, 0.25);
    }
    html[data-m6theme="dark"] .fusion-card {
        background-color: rgba(148, 163, 184, 0.10);
        border: 1px solid rgba(148, 163, 184, 0.25);
    }
    html[data-m6theme="dark"] .fusion-card .fusion-title { color: #fbbf24; }
    html[data-m6theme="dark"] .fusion-card .fusion-desc { color: #cbd5e1; }
    html[data-m6theme="dark"] .flow-card {
        background: rgba(148, 163, 184, 0.10);
        border: 1px solid rgba(148, 163, 184, 0.25);
    }
    html[data-m6theme="dark"] .flow-card .flow-title { color: #fbbf24; }
    html[data-m6theme="dark"] .flow-card .flow-label { color: #cbd5e1; }

    /* ═══ Fase 6 - Metricas del Modelo Ganador (claro) ═══ */
    .kpi-rmse { background: #dbeafe; border-color: #bfdbfe; }
    .kpi-rmse .kpi-value { color: #0284c7; }
    .kpi-rmse .kpi-label { color: #1e40af; }
    .kpi-rmse .kpi-sub { color: #1d4ed8; }

    .kpi-r2 { background: #d1fae5; border-color: #a7f3d0; }
    .kpi-r2 .kpi-value { color: #059669; }
    .kpi-r2 .kpi-label { color: #065f46; }
    .kpi-r2 .kpi-sub { color: #047857; }

    .kpi-mae { background: #cffafe; border-color: #a5f3fc; }
    .kpi-mae .kpi-value { color: #0891b2; }
    .kpi-mae .kpi-label { color: #155e75; }
    .kpi-mae .kpi-sub { color: #0e7490; }

    .kpi-mape { background: #ffedd5; border-color: #fed7aa; }
    .kpi-mape .kpi-value { color: #ea580c; }
    .kpi-mape .kpi-label { color: #9a3412; }
    .kpi-mape .kpi-sub { color: #c2410c; }

    .winner-card {
        background: #fef3c7;
        border: 1px solid #fde68a;
        border-radius: 12px;
        padding: 1.25rem;
        margin-top: 2rem;
        text-align: center;
    }
    .winner-card .winner-name { color: #92400e; font-size: 1.2rem; font-weight: bold; }
    .winner-card .winner-type { color: #a16207; font-size: 0.85rem; margin-top: 0.4rem; }
    .winner-card .winner-score-box { margin-top: 0.9rem; padding-top: 0.6rem; border-top: 1px dashed #fcd34d; }
    .winner-card .winner-score-value { color: #d97706; font-size: 2rem; font-weight: bold; }
    .winner-card .winner-score-label { color: #92400e; font-size: 0.85rem; margin-top: 0.25rem; font-weight: 600; }

    /* ═══ Fase 6 - Modo Oscuro ═══ */
    html[data-m6theme="dark"] .kpi-rmse { background: #16254a; border-color: #27437e; }
    html[data-m6theme="dark"] .kpi-rmse .kpi-value { color: #60a5fa; }
    html[data-m6theme="dark"] .kpi-rmse .kpi-label { color: #bfdbfe; }
    html[data-m6theme="dark"] .kpi-rmse .kpi-sub { color: #93c5fd; }

    html[data-m6theme="dark"] .kpi-r2 { background: #06372a; border-color: #0b5d47; }
    html[data-m6theme="dark"] .kpi-r2 .kpi-value { color: #34d399; }
    html[data-m6theme="dark"] .kpi-r2 .kpi-label { color: #a7f3d0; }
    html[data-m6theme="dark"] .kpi-r2 .kpi-sub { color: #6ee7b7; }

    html[data-m6theme="dark"] .kpi-mae { background: #083344; border-color: #155e75; }
    html[data-m6theme="dark"] .kpi-mae .kpi-value { color: #22d3ee; }
    html[data-m6theme="dark"] .kpi-mae .kpi-label { color: #a5f3fc; }
    html[data-m6theme="dark"] .kpi-mae .kpi-sub { color: #67e8f9; }

    html[data-m6theme="dark"] .kpi-mape { background: #431407; border-color: #7c2d12; }
    html[data-m6theme="dark"] .kpi-mape .kpi-value { color: #fb923c; }
    html[data-m6theme="dark"] .kpi-mape .kpi-label { color: #fed7aa; }
    html[data-m6theme="dark"] .kpi-mape .kpi-sub { color: #fdba74; }

    html[data-m6theme="dark"] .winner-card { background: #46290a; border-color: #7c4a03; }
    html[data-m6theme="dark"] .winner-card .winner-name { color: #fef3c7; }
    html[data-m6theme="dark"] .winner-card .winner-type { color: #fcd34d; }
    html[data-m6theme="dark"] .winner-card .winner-score-value { color: #fbbf24; }
    html[data-m6theme="dark"] .winner-card .winner-score-label { color: #fef3c7; }
</style>
""", unsafe_allow_html=True)

# Detector de tema de Streamlit (marca <html data-m6theme="light|dark"> para el CSS)
components.html(
    """
    <script>
    (function(){
        function apply(){
            try {
                var d = window.parent.document;
                if (!d) return;
                var app = d.querySelector('[data-testid="stApp"]') || d.body;
                var bg = getComputedStyle(app).backgroundColor || '';
                var m = bg.match(/rgba?\\((\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)/);
                var lum = 255;
                if (m) {
                    lum = 0.2126 * parseFloat(m[1]) + 0.7152 * parseFloat(m[2]) + 0.0722 * parseFloat(m[3]);
                }
                d.documentElement.setAttribute('data-m6theme', lum > 127 ? 'light' : 'dark');
            } catch (e) {}
        }
        apply();
    })();
    </script>
    """,
    height=1,
)


# Aplicar estilo profesional a matplotlib
setup_professional_style()


def render_interpretation(interp_result, key_suffix=""):
    """Renderiza un resultado de interpretacion con el color apropiado"""
    icon = interp_result.icon
    text = interp_result.text
    action = interp_result.action
    severity = interp_result.severity
    
    # Mapear severidad a componente Streamlit
    if severity == "success":
        st.success(f"{icon} {text}")
    elif severity == "warning":
        st.warning(f"{icon} {text}")
    elif severity == "danger":
        st.error(f"{icon} {text}")
    else:
        st.info(f"{icon} {text}")
    
    if action:
        st.caption(f"💡 **Accion recomendada:** {action}")


def render_dual_interpretation(chart_type: str, chart_data: dict, bench: int, key_suffix: str,
                               static_text: str = None, stacked: bool = False):
    """Renderiza IA y análisis determinístico, en paralelo o apilados."""
    col_ai, col_static = (st.container(), st.container()) if stacked else st.columns(2)
    
    # ─── Izquierda: Interpretación con IA ───
    with col_ai:
        cache_key = f"ai_interp_{chart_type}_{bench}_{key_suffix}"
        
        if cache_key in st.session_state and st.session_state[cache_key]:
            st.success("🧠 Interpretación con IA")
            st.write(st.session_state[cache_key])
            if st.button("🔄 Regenerar", key=f"regen_{cache_key}"):
                del st.session_state[cache_key]
                st.rerun()
        else:
            if st.button("🧠 Interpretación con IA (Groq)", key=f"btn_{cache_key}"):
                with st.spinner("Consultando al experto de IA..."):
                    try:
                        result = generate_chart_interpretation(chart_type, chart_data, bench)
                        st.session_state[cache_key] = result
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generando interpretación: {e}")
    
    # ─── Derecha: Interpretación Determinística ───
    with col_static:
        if static_text:
            with st.expander("📝 Interpretación Determinística", expanded=False):
                st.info(static_text)


def render_header():
    """Renderiza el header principal"""
    st.markdown('<div class="main-header">Motor IA M-6</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        'Gemelo Digital Predictivo para Control de Ley en Mineria a Cielo Abierto<br>'
        '<span style="font-size: 0.9rem;">Comparacion de 5 Modelos (3 Clasicos + 2 Hibridos)</span>'
        '</div>', 
        unsafe_allow_html=True
    )


def render_sidebar():
    """Renderiza la barra lateral de navegacion"""
    with st.sidebar:
        logo_path = Path(__file__).resolve().parent.parent / "frontend" / "public" / "logo" / "LOGO-M6.png"
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;font-size:60px;margin-bottom:10px;'>⛏️</div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center;color:#d97706;margin-top:0.75rem;margin-bottom:0.15rem;'>Motor IA M-6</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#64748b;font-size:12px;margin-bottom:20px;'>Estimacion predictiva de ley de cobre</p>", unsafe_allow_html=True)
        
        # Menu de fases CRISP-DM - lista de botones (sin radiobutton, el seleccionado queda encapsulado)
        phase_options = [
            "🏠 Inicio",
            "📁 Carga de Datos",
            "📊 Fase 1: Entendimiento",
            "🔍 Fase 2: Exploracion de Datos",
            "🛠️ Fase 3: Preparacion",
            "🤖 Fase 4: Modelado",
            "📈 Fase 5: Evaluacion",
            "🏆 Fase 6: Seleccion & Despliegue",
            "⚡ Lote Multi-Banco",
        ]
        if "phase" not in st.session_state:
            st.session_state["phase"] = "🏠 Inicio"
        st.markdown("<p style='margin:0 0 0.25rem 0;color:#64748b;font-size:0.85rem;font-weight:600;'>Fase del Proyecto:</p>", unsafe_allow_html=True)
        for opt in phase_options:
            if st.button(
                opt,
                key=f"nav_{opt}",
                use_container_width=True,
                type="primary" if opt == st.session_state["phase"] else "secondary",
            ):
                st.session_state["phase"] = opt
                st.rerun()
        phase = st.session_state["phase"]
        
        st.divider()

        # El CSV GeoMet no representa ninguno de los bancos del proyecto operativo.
        loaded = st.session_state.get('dataset')
        drillhole_mode = (loaded is not None and 'hole_id' in loaded.columns
                          and 'cu_base' not in loaded.columns)
        if drillhole_mode:
            selected_bench = 3170  # Identificador interno de sesión, nunca banco GeoMet.
            st.info("Sondajes · evaluación espacial sin banco operativo")
            st.caption(st.session_state.get('dataset_source') or 'Dataset de sondajes cargado')
        else:
            st.markdown("<p style='margin:0 0 0.25rem 0;color:#64748b;font-size:0.85rem;font-weight:600;'>Banco Operativo:</p>", unsafe_allow_html=True)
            selected_bench = st.selectbox(
                "Seleccionar Banco:",
                BENCHES,
                index=BENCHES.index(3170) if 3170 in BENCHES else 0,
                label_visibility="collapsed",
                help="Nivel operativo activo para el analisis",
            )

        st.divider()

        # ─── Estado del Sistema ───
        st.markdown("<p style='margin:0 0 0.35rem 0;color:#64748b;font-size:0.85rem;font-weight:600;'>Estado del Sistema:</p>", unsafe_allow_html=True)
        st.markdown(
            "<div style='background:rgba(148,163,184,0.12);border:1px solid rgba(148,163,184,0.28);border-radius:12px;padding:0.9rem;'>"
            "<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.45rem;'>"
            "<span style='width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 6px #10b981;'></span>"
            f"<span style='color:#64748b;font-size:0.82rem;'>Base de datos: <b>{DB_CONFIG['host']}:{DB_CONFIG['port']}</b></span>"
            "</div>"
            "<div style='display:flex;align-items:center;gap:0.5rem;'>"
            "<span style='width:8px;height:8px;border-radius:50%;background:#10b981;'></span>"
            f"<span style='color:#64748b;font-size:0.82rem;'>Actualizado: <b>{datetime.now().strftime('%d-%m-%Y %H:%M')}</b></span>"
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        st.divider()

        # Boton de mantenimiento
        if st.button("🧹 Limpiar Caches", type="secondary", use_container_width=True, help="Borra archivos __pycache__ y .pyc si hay errores extraños"):
            import shutil
            import os
            count = 0
            for root, dirs, files in os.walk('.'):
                for d in dirs:
                    if d == '__pycache__':
                        try:
                            shutil.rmtree(os.path.join(root, d))
                            count += 1
                        except Exception:
                            pass
                for f in files:
                    if f.endswith('.pyc'):
                        try:
                            os.remove(os.path.join(root, f))
                            count += 1
                        except Exception:
                            pass
            st.success(f"Caches limpiados: {count} items. Reinicia Streamlit.")

        return phase, selected_bench


def render_data_upload():
    """Pagina de carga de datos"""
    st.header("📁 Carga de Datos Mineros")
    
    st.info("""
    **Instrucciones:**
    - Sube tu propio dataset (CSV o Excel) con datos de bloques mineros
    - O genera datos sintéticos realistas para demostración
    - Para bloques: `x`, `y`, `z`, `cu_base` y una `cu_bayesian` medida de forma independiente
    - Para sondajes GeoMet: puedes subir `drillholes.csv` directamente; se convierte Cu ppm a % Cu y se evalúa por sondaje
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Subir Archivo")
        uploaded_file = st.file_uploader(
            "Selecciona archivo CSV o Excel",
            type=['csv', 'xlsx', 'xls'],
            help="Acepta bloques con dos leyes independientes o drillholes.csv de GeoMet"
        )
        
        if uploaded_file is not None:
            try:
                pipeline = TrainingPipeline()
                uploaded_file.seek(0)
                df = pipeline.load_from_file(uploaded_file)
                st.session_state.dataset = df
                st.session_state.dataset_source = f"Archivo: {uploaded_file.name}"
                st.session_state.dataset_quality = score_dataset(df)
                st.success(f"✅ Dataset cargado: {len(df)} muestras, {len(df.columns)} columnas")
            except Exception as e:
                st.error(f"❌ Error cargando archivo: {e}")
    
    with col2:
        st.subheader("🎲 Generar Datos Sintéticos")
        
        col_samples, col_benches = st.columns(2)
        with col_samples:
            n_samples = st.number_input("Muestras por banco", min_value=100, max_value=10000, value=2000, step=100)
        with col_benches:
            n_benches = st.number_input("Número de bancos", min_value=1, max_value=10, value=3, step=1)
        
        bench_start = st.selectbox("Banco inicial", BENCHES[:8], index=6)
        selected_benches = [bench_start - i*15 for i in range(n_benches)]
        st.caption(f"Bancos: {selected_benches}")
        
        if st.button("🚀 Generar Dataset Sintético", type="primary", use_container_width=True):
            with st.spinner(f"Generando {n_samples * n_benches} muestras realistas..."):
                dfs = []
                for bench in selected_benches:
                    df = generate_realistic_mining_data(bench, n_samples=n_samples)
                    dfs.append(df)
                
                df_total = pd.concat(dfs, ignore_index=True)
                st.session_state.dataset = df_total
                st.session_state.dataset_source = f"Sintético: {n_samples * n_benches} muestras ({n_benches} bancos)"
                st.session_state.dataset_quality = score_dataset(df_total)
                st.success(f"✅ Dataset generado: {len(df_total)} muestras")
    
    # Mostrar info del dataset cargado
    if st.session_state.dataset is not None:
        st.markdown("---")
        st.subheader("📊 Dataset Actual")
        
        df = st.session_state.dataset
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Muestras", f"{len(df):,}")
        with col2:
            st.metric("Columnas", len(df.columns))
        with col3:
            if 'hole_id' in df.columns and 'cu_base' not in df.columns:
                st.metric("Sondajes", df['hole_id'].nunique())
            else:
                st.metric("Bancos", df['z'].nunique() if 'z' in df.columns else "N/A")
        with col4:
            grade_col = 'cu_base' if 'cu_base' in df.columns else 'cu_bayesian'
            st.metric("Ley Media (% Cu)", f"{df[grade_col].mean():.3f}" if grade_col in df.columns else "N/A")
        
        st.caption(f"Fuente: {st.session_state.dataset_source}")
        
        # ── Evaluación de calidad del dataset (score 0-10) ──
        if st.session_state.dataset_quality is not None:
            q = st.session_state.dataset_quality
            score = q['score']
            verdict = q['verdict']
            if q.get('critical_errors'):
                score_color, emoji = "#ef4444", "🔴"
            elif score >= 8.5:
                score_color, emoji = "#10b981", "🟢"
            elif score >= 7.0:
                score_color, emoji = "#22c55e", "🟢"
            elif score >= 5.0:
                score_color, emoji = "#f59e0b", "🟡"
            elif score >= 3.0:
                score_color, emoji = "#f97316", "🟠"
            else:
                score_color, emoji = "#ef4444", "🔴"
            
            st.markdown("---")
            col_q1, col_q2 = st.columns([1, 3])
            with col_q1:
                st.markdown(
                    f"<div style='background:{score_color};color:white;border-radius:14px;"
                    f"text-align:center;padding:1.1rem 0;'>"
                    f"<div style='font-size:2.1rem;font-weight:800;line-height:1;'>{score}/10</div>"
                    f"<div style='font-size:0.72rem;opacity:.9;margin-top:.3rem;'>CALIDAD AUTOMÁTICA</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_q2:
                st.markdown(f"**{emoji} {verdict}**")
                st.progress(min(score / 10.0, 1.0))
                st.caption(f"{q['n_rows']:,} muestras evaluadas")
                st.caption("El CSV por sí solo no acredita origen, unidades, ensayos ni QA/QC para uso real.")
                if q.get('score_cap', 10) < q.get('raw_score', score):
                    st.caption(f"Puntaje limitado a {q['score_cap']}/10 por alertas graves.")
                with st.expander("🔍 Detalle de la evaluación"):
                    for c in q['checks']:
                        icon = "✅" if c['status'] == 'ok' else ("⚠️" if c['status'] == 'warn' else "❌")
                        fw = "600" if c['status'] == 'error' else "400"
                        st.markdown(
                            f"<div style='display:flex;justify-content:space-between;gap:8px;'>"
                            f"<span style='font-weight:{fw};'>{icon} {c['label']}</span>"
                            f"<span style='font-size:.85rem;color:#94a3b8;white-space:nowrap;'>{c['points']:.1f} pts</span>"
                            f"</div><div style='font-size:.83rem;color:#64748b;margin:0 0 .4rem 22px;'>{c['detail']}</div>",
                            unsafe_allow_html=True,
                        )
        
        with st.expander("👁️ Vista Previa de Datos"):
            st.dataframe(df.head(20), use_container_width=True)
        
        with st.expander("📈 Estadísticas Descriptivas"):
            st.dataframe(df.describe(), use_container_width=True)
        
        # Boton para descargar template
        st.markdown("---")
        st.subheader("📥 Descargar Template")
        
        template_df = generate_realistic_mining_data(3170, n_samples=50)
        csv = template_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Descargar Template CSV (50 filas de ejemplo)",
            data=csv,
            file_name='template_mining_dataset.csv',
            mime='text/csv'
        )
        
        # Dos gráficos en una fila, cada uno con la misma interpretación de Fase 2.
        st.markdown("---")
        is_drillhole_map = 'hole_id' in df.columns and 'cu_base' not in df.columns
        signature_cols = [c for c in ('hole_id', 'x', 'y', 'z', 'cu_base', 'cu_bayesian') if c in df.columns]
        dataset_key = hashlib.sha256(
            pd.util.hash_pandas_object(df[signature_cols], index=False).values.tobytes()
        ).hexdigest()[:12]
        col_map, col_hist = st.columns(2, gap="large")

        with col_map:
            st.subheader("🗺️ Mapa de sondajes" if is_drillhole_map
                         else "🗺️ Mapa de Distribución Espacial")
            fig, ax = plt.subplots(figsize=(7.2, 5))
            if is_drillhole_map:
                for _, hole in df.groupby('hole_id', sort=False):
                    trace = hole.sort_values('z', ascending=False)
                    ax.plot(trace['x'], trace['y'], color='#cbd5e1', alpha=0.25,
                            linewidth=0.8, zorder=1)
                scatter = ax.scatter(df['x'], df['y'], c=df['z'], cmap='viridis',
                                     s=18, alpha=0.9, edgecolors='none', zorder=2)
                collars = df.loc[df.groupby('hole_id')['z'].idxmax()]
                ax.scatter(collars['x'], collars['y'], s=32, facecolors='none',
                           edgecolors='#f8fafc', linewidths=0.8, zorder=3)
                fig.colorbar(scatter, ax=ax, label='Z (coordenada original)')
                ax.set_xlabel("X (coordenada original)")
                ax.set_ylabel("Y (coordenada original)")
                ax.set_title("Proyección XY de sondajes")
            else:
                scatter = ax.scatter(df['x'], df['y'], c=df['z'], cmap='viridis',
                                     s=24, alpha=0.7, edgecolors='black', linewidth=0.2)
                fig.colorbar(scatter, ax=ax, label='Z')
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.set_title("Distribución espacial de bloques")
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            st.pyplot(fig)
            plt.close(fig)

            map_data = {
                'tipo': 'sondajes' if is_drillhole_map else 'bloques',
                'muestras': len(df),
                'sondajes': int(df['hole_id'].nunique()) if is_drillhole_map else None,
                'color': 'coordenada Z',
                'x_rango': [float(df['x'].min()), float(df['x'].max())],
                'y_rango': [float(df['y'].min()), float(df['y'].max())],
                'z_rango': [float(df['z'].min()), float(df['z'].max())],
                'unidades_y_crs_verificados': False if is_drillhole_map else None,
            }
            if is_drillhole_map:
                st.caption("Vista XY: cada trazo une muestras de un sondaje; el círculo marca su punto con mayor Z. "
                           "El color es Z, no Cu. Las unidades y el CRS no están documentados en el CSV.")
                static_map = (f"**Cobertura observada:** {len(df):,} muestras en "
                              f"{df['hole_id'].nunique()} sondajes. X va de "
                              f"{df['x'].min():.1f} a {df['x'].max():.1f}; Y, de "
                              f"{df['y'].min():.1f} a {df['y'].max():.1f}. "
                              "Las franjas son proyecciones de trayectorias sobre XY. "
                              "El color representa Z; este mapa no muestra leyes de Cu ni permite "
                              "identificar zonas de enriquecimiento. El CSV no acredita unidades ni CRS.")
            else:
                static_map = (f"**Cobertura observada:** {len(df):,} puntos; "
                              f"X de {df['x'].min():.1f} a {df['x'].max():.1f} y "
                              f"Y de {df['y'].min():.1f} a {df['y'].max():.1f}. "
                              "El color corresponde a Z, no a la ley de Cu. "
                              "La distribución espacial por sí sola no demuestra continuidad de la ley.")
            st.divider()
            render_dual_interpretation('upload_spatial_coverage', map_data, None,
                                       f'upload_map_{dataset_key}', static_map, stacked=True)

        with col_hist:
            st.subheader("📊 Distribución de Leyes de Cobre")
            fig2, ax2 = plt.subplots(figsize=(7.2, 5))
            hist_series = {}
            for column, label, color in (
                ('cu_base', 'Kriging Base', '#f59e0b'),
                ('cu_bayesian', 'Ensayo Cu medido' if is_drillhole_map else 'Bayesiano M-6', '#10b981'),
            ):
                if column not in df.columns:
                    continue
                values = pd.to_numeric(df[column], errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
                if values.empty:
                    continue
                ax2.hist(values, bins=50, color=color, alpha=0.65,
                         edgecolor='black', linewidth=0.25, label=label)
                hist_series[label] = {
                    'n': int(len(values)), 'mean': float(values.mean()),
                    'median': float(values.median()), 'p95': float(values.quantile(0.95)),
                    'min': float(values.min()), 'max': float(values.max()),
                }
            ax2.set_xlabel("Ley de Cobre (% Cu)")
            ax2.set_ylabel("Frecuencia")
            ax2.set_title("Distribución de Leyes de Cobre")
            ax2.grid(True, alpha=0.3)
            if hist_series:
                ax2.legend()
            st.pyplot(fig2)
            plt.close(fig2)

            if hist_series:
                hist_data = {'tipo': 'sondajes' if is_drillhole_map else 'bloques',
                             'unidad': '% Cu', 'series': hist_series}
                summaries = [
                    f"**{label}:** {stats['n']:,} valores; media {stats['mean']:.3f} %, "
                    f"mediana {stats['median']:.3f} %, P95 {stats['p95']:.3f} %, "
                    f"rango {stats['min']:.3f}–{stats['max']:.3f} %."
                    for label, stats in hist_series.items()
                ]
                static_hist = "\n\n".join(summaries)
                if is_drillhole_map:
                    measured = hist_series['Ensayo Cu medido']
                    skew_note = ("La media supera la mediana, compatible con una cola de leyes altas. "
                                 if measured['mean'] > measured['median'] else
                                 "La media no supera la mediana; revisa la forma completa de las barras. ")
                    static_hist += ("\n\nSon ensayos puntuales de sondajes. " + skew_note +
                                    "El histograma no aporta tonelaje ni demuestra la ley "
                                    "de alimentación a planta.")
                else:
                    static_hist += ("\n\nEl histograma permite comparar centro, dispersión y extremos. "
                                    "La forma de las barras no demuestra por sí sola continuidad geológica.")
                st.divider()
                render_dual_interpretation('upload_copper_histogram', hist_data, None,
                                           f'upload_hist_{dataset_key}', static_hist, stacked=True)
            else:
                st.warning("No hay valores de ley de cobre válidos para interpretar.")


def render_home():
    """Pagina de inicio mejorada"""
    
    # Metricas principales con cards - COLORES CLAROS SOLIDOS
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="kpi-card kpi-amber">
            <div class="kpi-value">5</div>
            <div class="kpi-label">Modelos Disponibles</div>
            <div class="kpi-sub">3 Clasicos + 2 Hibridos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="kpi-card kpi-blue">
            <div class="kpi-value">6</div>
            <div class="kpi-label">Bancos Activos</div>
            <div class="kpi-sub">3260m - 3125m</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="kpi-card kpi-green">
            <div class="kpi-value">6</div>
            <div class="kpi-label">Metricas de Evaluacion</div>
            <div class="kpi-sub">Score Compuesto</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ¿Qué es este Gemelo Digital? (Diseño unificado en card)
    st.subheader("💡 Concepto del Gemelo Digital M-6")
    st.markdown("""
    <div class="twin-card">
        <strong>🤖 Clon Digital 3D de la Mina:</strong> Un Gemelo Digital es una representación virtual en tiempo real de la montaña real. 
        Permite simular qué cubos de roca son ricos en Cobre (% Cu) o estériles <em>antes de mover la maquinaria pesada</em>, 
        evitando gastar millones en procesar tierra inútil (<strong>dilución</strong>) o tirar mineral a la basura (<strong>pérdida de mineral</strong>).
    </div>
    """, unsafe_allow_html=True)

    # Fusión Multifuente de Datos (Tarjetas unificadas)
    st.subheader("🌐 Fusión de Datos Multifuente (5 Fuentes)")
    st.markdown("""
    A diferencia de la minería tradicional que solo usa pozos de perforación, el Gemelo Digital M-6 integra <strong>5 fuentes de datos</strong> simultáneamente:
    """)

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.markdown("""
        <div class="fusion-card">
            <div class="fusion-title">🕳️ 1. Sondajes & Perforaciones</div>
            <div class="fusion-desc">Muestras químicas directas de laboratorio de pozos DDH, RC y perforaciones de tronadura (<em>blastholes</em>).</div>
        </div>
        """, unsafe_allow_html=True)
    with f_col2:
        st.markdown("""
        <div class="fusion-card">
            <div class="fusion-title">🛰️ 2. Firmas Hiperespectrales</div>
            <div class="fusion-desc">Espectrometría VNIR/SWIR (drones/satélite) para detectar minerales de alteración (Crisocola, Illita, Clorita, Biotita).</div>
        </div>
        """, unsafe_allow_html=True)
    with f_col3:
        st.markdown("""
        <div class="fusion-card">
            <div class="fusion-title">🪨 3. Geología & Estructura</div>
            <div class="fusion-desc">Litología (Skarn, Pórfido, Andesita), tipo de alteración y cercanía a fallas estructurales.</div>
        </div>
        """, unsafe_allow_html=True)

    f_col4, f_col5 = st.columns(2)
    with f_col4:
        st.markdown("""
        <div class="fusion-card" style="margin-top: 0.75rem;">
            <div class="fusion-title">📈 4. Control de Procesos (SPC)</div>
            <div class="fusion-desc">Datos operacionales reales de planta concentradora, tonelaje del bloque y promedios móviles históricos (EWMA/CUSUM).</div>
        </div>
        """, unsafe_allow_html=True)
    with f_col5:
        st.markdown("""
        <div class="fusion-card" style="margin-top: 0.75rem;">
            <div class="fusion-title">🧮 5. Kernel Bayesiano Espacial (Matérn 5/2)</div>
            <div class="fusion-desc">Simulación Monte Carlo (200 iteraciones) para cuantificar la incertidumbre epistémica y aleatoria (intervalos P10-P50-P90).</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Objetivo - FONDO ADAPTABLE AL TEMA
    st.subheader("🎯 Objetivo Principal")
    st.markdown("""
    <div class="objetivo-box" style="margin-bottom: 2.5rem;">
        Desarrollar un <strong>Gemelo Digital predictivo (M-6)</strong> que integre modelos de bloques, 
        ensayos de voladura e imagenes hiperespectrales para estimar la ley de cobre (% Cu) 
        con incertidumbre cuantificada, comparando 5 modelos predictivos mediante metricas 
        estadisticas robustas, seleccionando el mejor modelo por banco operativo para minimizar 
        la dilucion minera, reducir perdidas de mineral y optimizar la alimentacion a la planta concentradora.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Parámetros evaluados por el Gemelo Digital
    st.subheader("🧪 Parámetros Físicos, Químicos y Geológicos Evaluados")
    st.markdown("""
    El Gemelo Digital M-6 procesa y evalúa 5 categorías fundamentales de parámetros de la roca:
    """)
    
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.markdown("""
        * 🧪 **Ensayos Químicos y Mineralógicos:** Ley de Cobre Total (% Cu) y Cobre Soluble (% CuSol).
        * 🔬 **Firmas Espectrométricas (SWIR/VNIR):** Índice de alteración espectral (Crisocola, Illita, Clorita, Biotita).
        * 🪨 **Parámetros Geológicos:** Litología (*Skarn, Pórfido, Andesita*) y Tipo de Alteración (*Silícea, Argílica, Propilítica*).
        """)
    with p_col2:
        st.markdown("""
        * 📏 **Parámetros Espaciales 3D:** Coordenadas (X, Y, Z), Kernel Matérn 5/2, distancia a sondajes y fallas geológicas.
        * ⛏️ **Parámetros Operacionales:** Tonelaje del bloque, densidad de pozos de tronadura (*Blasthole density*) y Ley de Corte (*Cut-off 0.35% Cu*).
        * 🎲 **Simulación Bayesiana (Monte Carlo 200 iteraciones):** Incertidumbre Epistémica (muestreable) y Aleatoria (intrínseca).
        """)
    
    st.markdown("---")
    st.subheader("🤖 Modelos a Evaluar")
    
    models_df = pd.DataFrame([
        {"#": 1, "Modelo": "Ordinary Kriging", "Tipo": "Clasico", "Descripcion": "Baseline geostadistico estandar JORC"},
        {"#": 2, "Modelo": "Random Forest", "Tipo": "Clasico", "Descripcion": "Manejo de no linealidades espaciales"},
        {"#": 3, "Modelo": "XGBoost", "Tipo": "Clasico", "Descripcion": "Estado del arte en datos tabulares"},
        {"#": 4, "Modelo": "Stacking Ensemble", "Tipo": "Hibrido", "Descripcion": "Fusion Kriging + RF + XGBoost"},
        {"#": 5, "Modelo": "NN + Bayesian Kriging", "Tipo": "Hibrido", "Descripcion": "Red Neuronal + Incertidumbre Bayesiana"},
    ])
    
    st.dataframe(models_df, use_container_width=True, hide_index=True)
    
    # Metricas
    st.subheader("📊 Metricas de Comparacion")
    
    metrics_df = pd.DataFrame([
        {"Metrica": "RMSE", "Peso": "25%", "Descripcion": "Error cuadratico medio (penaliza errores grandes)"},
        {"Metrica": "MAE", "Peso": "20%", "Descripcion": "Error absoluto medio (interpretable en % Cu)"},
        {"Metrica": "R²", "Peso": "20%", "Descripcion": "Coeficiente de determinacion"},
        {"Metrica": "MAPE", "Peso": "15%", "Descripcion": "Error porcentual absoluto medio"},
        {"Metrica": "Bias", "Peso": "10%", "Descripcion": "Sesgo sistematico (sobre/subestimacion)"},
        {"Metrica": "Incertidumbre", "Peso": "10%", "Descripcion": "Intervalo de prediccion P90-P10"},
    ])
    
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    # Flujo del proceso - FONDO CLARO
    st.subheader("🔄 Flujo de Trabajo CRISP-DM")
    
    flow_col1, flow_col2, flow_col3, flow_col4, flow_col5, flow_col6 = st.columns(6)
    
    with flow_col1:
        st.markdown("""
        <div class="flow-card">
            <div class="flow-icon">📊</div>
            <div class="flow-title">Fase 1</div>
            <div class="flow-label">Entendimiento</div>
        </div>
        """, unsafe_allow_html=True)
    
    with flow_col2:
        st.markdown("""
        <div class="flow-card">
            <div class="flow-icon">🔍</div>
            <div class="flow-title">Fase 2</div>
            <div class="flow-label">Exploracion</div>
        </div>
        """, unsafe_allow_html=True)
    
    with flow_col3:
        st.markdown("""
        <div class="flow-card">
            <div class="flow-icon">🛠️</div>
            <div class="flow-title">Fase 3</div>
            <div class="flow-label">Preparacion</div>
        </div>
        """, unsafe_allow_html=True)
    
    with flow_col4:
        st.markdown("""
        <div class="flow-card">
            <div class="flow-icon">🤖</div>
            <div class="flow-title">Fase 4</div>
            <div class="flow-label">Modelado</div>
        </div>
        """, unsafe_allow_html=True)
    
    with flow_col5:
        st.markdown("""
        <div class="flow-card">
            <div class="flow-icon">📈</div>
            <div class="flow-title">Fase 5</div>
            <div class="flow-label">Evaluacion</div>
        </div>
        """, unsafe_allow_html=True)
    
    with flow_col6:
        st.markdown("""
        <div class="flow-card">
            <div class="flow-icon">🏆</div>
            <div class="flow-title">Fase 6</div>
            <div class="flow-label">Despliegue</div>
        </div>
        """, unsafe_allow_html=True)


def render_phase1_understanding():
    """Fase 1: Entendimiento del Negocio"""
    st.header("📊 Fase 1: Entendimiento del Negocio")
    
    st.subheader("Contexto Minero")
    st.markdown("""
    **Mina Esperanza Sur - Rajo Principal (Project ID: 4)**
    - Tipo de yacimiento: Skarn de Cu-Au-Ag (porfídico)
    - Método de explotación: Cielo abierto (open pit)
    - Bancos operativos: 3260m a 3125m (15m de altura)
    - Cut-off grade: 0.35% Cu
    - Datos reales de planta: 300 registros de control de procesos (50 por banco)
    
    **Problema:**
    El modelo de kriging tradicional presenta bias sistemático comparado con la alimentación 
    real de planta. Esto causa:
    - Dilución minera innecesaria (mezcla de estéril con mineral)
    - Pérdida de mineral económico enviado a botaderos
    - Alimentación subóptima a la planta concentradora
    - Dificultad para estimar leyes en zonas de alteración supérgena (crisocola)
    
    **Solución M-6 Gemelo Digital:**
    Comparar 5 modelos predictivos (3 clásicos + 2 híbridos) usando datos reales de planta,
    seleccionar el mejor por banco operativo y reconciliar predicciones vs. alimentación real.
    """)
    
    st.subheader("Flujo Mine-to-Mill Implementado")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Modelos Comparados", "5", delta="3 Clásicos + 2 Híbridos")
    with col2:
        st.metric("Datos Reales", "300 registros", delta="50 por banco")
    with col3:
        st.metric("Bancos Cubiertos", "6 activos", delta="3260m - 3125m")
    
    st.markdown("---")
    st.subheader("Arquitectura del Sistema")
    
    arch_col1, arch_col2, arch_col3 = st.columns(3)
    with arch_col1:
        st.markdown("""
        **🎨 Frontend React**
        - Dashboard Ejecutivo & SPC
        - Reconciliación Mine-to-Mill
        - Visualizador 3D WebGL
        - Centro de Alertas con notificaciones
        """)
    with arch_col2:
        st.markdown("""
        **⚙️ Backend FastAPI**
        - PostgreSQL: modelos de bloques, control de procesos, alertas
        - Reconciliación: métricas RMSE, MAE, R², bias
        - Activación de modelos ganadores por banco
        """)
    with arch_col3:
        st.markdown("""
        **🤖 Motor IA Streamlit**
        - Entrenamiento de 5 modelos predictivos
        - Selección configurable (1, 2, 3... o todos)
        - Activación y envío de predicciones al backend
        - Reportes PDF/Excel con interpretaciones
        """)
    
    st.markdown("---")
    st.subheader("Criterios de Éxito Actualizados")
    crit_col1, crit_col2, crit_col3 = st.columns(3)
    with crit_col1:
        st.metric("RMSE Objetivo", "≤ 0.10% Cu", delta="vs 0.22% kriging base")
    with crit_col2:
        st.metric("R² Mínimo", "≥ 0.80", delta="vs -0.42 kriging base")
    with crit_col3:
        st.metric("Bias Aceptable", "≤ 0.05% Cu", delta="vs 0.22% kriging base")
    
    st.info("""
    **Nota importante:** Los criterios se ajustaron basándose en datos reales de planta.
    Con 50 muestras por banco y features limpias (sin data leakage), un RMSE de 0.05-0.10% Cu
    y R² de 0.80-0.90 representan un modelo robusto y generalizable.
    """)


def render_phase2_exploration(bench):
    """Fase 2: Exploracion de Datos (EDA)"""
    st.header("🔍 Fase 2: Exploracion de Datos (EDA)")
    
    st.markdown("""
    **¿Para qué sirve esta fase?**
    El Análisis Exploratorio de Datos (EDA) te permite conocer la calidad, distribución y patrones 
    de los datos ANTES de entrenar los modelos. Aquí verificas si los datos son confiables, 
    si hay valores atípicos, y si las leyes de cobre siguen patrones geológicos coherentes.
    Esto evita que entrenes modelos con datos sucios o inconsistentes.
    """)
    
    st.info(f"Banco seleccionado: **{bench}m**")
    
    # Usar dataset cargado si existe
    if st.session_state.dataset is not None:
        df = st.session_state.dataset
        data_source = "Dataset cargado por el usuario"
        if 'z' in df.columns:
            df = df[df['z'] == bench]
            if len(df) == 0:
                st.warning(f"No hay datos para banco {bench}m en el dataset cargado. Mostrando todos los datos.")
                df = st.session_state.dataset
        st.success(f"📁 Usando dataset cargado: {len(df)} muestras")
    else:
        # Cargar datos por defecto
        pipeline = TrainingPipeline(bench=bench)
        try:
            df = pipeline.load_data(bench, use_real_data=True)
            data_source = "Datos reales de planta (Mine-to-Mill)"
            st.success(f"🏭 Usando datos reales de planta: {len(df)} muestras de control de procesos")
        except Exception:
            df = pipeline.load_data(bench, use_real_data=False)
            data_source = "Datos sintéticos de demostración"
            st.warning(f"⚠️ Usando datos sintéticos: {len(df)} muestras generadas (no reflejan la planta real)")
    
    st.markdown("---")
    
    # ─── 1. Vista Previa de Datos ───
    st.subheader("1️⃣ Vista Previa de Datos")
    st.caption(f"Fuente: {data_source} | Primeras 10 filas del dataset")
    st.dataframe(df.head(10), use_container_width=True)
    
    with st.expander("💡 Interpretación - Vista Previa de Datos", expanded=False):
        st.info("""
        **¿Qué estás viendo?**
        Esta tabla muestra las columnas (features) que alimentarán los modelos.
        - Si ves **datos reales**: columnas como `plant_feed_grade`, `predicted_base_krig`, `tonnage`, `timestamp`.
        - Si ves **datos sintéticos**: columnas como `x`, `y`, `z`, `cu_base`, `cu_bayesian`, `rock_type`.
        Revisa que no haya valores vacíos (NaN) ni valores imposibles (ej. leyes negativas).
        """)
    
    st.markdown("---")
    
    # ─── 2. Estadísticas Descriptivas ───
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("2️⃣ Estadísticas Descriptivas")
        st.caption("Resumen numérico de todas las columnas")
        st.dataframe(df.describe(), use_container_width=True)
        
        st.divider()
        stats_data = df.describe().to_dict()
        static_stats = """**¿Qué demuestra esta tabla?**
        - **count**: Número de registros válidos. Si es menor al total, hay datos faltantes.
        - **mean**: Ley promedio del banco. Compara con el cut-off (0.35% Cu) para saber si es mineral o estéril.
        - **std**: Desviación estándar. Un valor alto (>0.4) indica mucha variabilidad geológica.
        - **min / max**: Valores extremos. Si max > 2.0% o min < 0.0%, revisa si son errores de medición.
        - **25% / 50% / 75%**: Percentiles. El 50% (mediana) te dice el valor central; si difiere mucho de la media, la distribución está sesgada."""
        render_dual_interpretation('descriptive_stats', stats_data, bench, 'stats', static_stats)
    
    with col2:
        st.subheader("3️⃣ Distribución de Ley de Cobre")
        fig, ax = plt.subplots(figsize=(8, 5))
        target_col = 'cu_bayesian' if 'cu_bayesian' in df.columns else 'cu_base'
        ax.hist(df[target_col], bins=30, color='#f59e0b', alpha=0.7, edgecolor='black')
        ax.axvline(df[target_col].mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {df[target_col].mean():.3f}%')
        ax.axvline(0.35, color='green', linestyle='--', linewidth=2, label='Cut-off: 0.35%')
        ax.set_xlabel("% Cu")
        ax.set_ylabel("Frecuencia")
        ax.set_title(f"Histograma de Leyes - Banco {bench}m")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        
        st.divider()
        hist_data = {
            'mean': float(df[target_col].mean()),
            'std': float(df[target_col].std()),
            'min': float(df[target_col].min()),
            'max': float(df[target_col].max()),
            'median': float(df[target_col].median()),
            'samples': len(df),
            'target_column': target_col
        }
        static_hist = """**¿Qué demuestra este histograma?**
        - **Forma de campana**: Indica distribución normal (común en yacimientos porfídicos).
        - **Cola derecha larga**: Hay algunos puntos con leyes muy altas (zonas de enriquecimiento).
        - **Pico cerca del cut-off (0.35%)**: Muchos bloques están en el límite mineral/estéril; aquí el modelo debe ser muy preciso.
        - **Barras vacías**: Si hay huecos, puede haber problemas de muestreo o estratificación."""
        render_dual_interpretation('histogram', hist_data, bench, 'hist', static_hist)
    
    st.markdown("---")
    
    # ─── 4. Distribución Espacial ───
    st.subheader("4️⃣ Distribución Espacial")
    
    if 'x' in df.columns and ('y' in df.columns or 'z' in df.columns):
        col_map, col_interp = st.columns(2)
        
        has_real_coords = 'y' in df.columns
        
        with col_map:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            
            x = df['x'].values
            y_val = df['y'].values if has_real_coords else df['days_from_start'].values if 'days_from_start' in df.columns else np.zeros(len(df))
            cu = df[target_col].values
            
            scatter = ax.scatter(x, y_val, c=cu, cmap='YlOrRd', s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
            plt.colorbar(scatter, ax=ax, label='% Cu')
            
            if has_real_coords:
                ax.set_xlabel("X (m)")
                ax.set_ylabel("Y (m)")
                ax.set_title(f"Mapa Espacial de Leyes - Banco {bench}m")
                ax.set_aspect('equal')
            else:
                ax.set_xlabel("Coordenada X proxy (m)")
                ax.set_ylabel("Días desde inicio")
                ax.set_title(f"Tendencia Temporal de Leyes - Banco {bench}m")
            
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        
        with col_interp:
            spatial_data = {
                'has_real_coords': has_real_coords,
                'n_points': len(df),
                'cu_mean': float(cu.mean()),
                'cu_std': float(cu.std()),
                'cu_min': float(cu.min()),
                'cu_max': float(cu.max()),
                'x_range': [float(x.min()), float(x.max())],
                'y_range': [float(y_val.min()), float(y_val.max())] if len(y_val) > 0 else [0, 0]
            }
            if has_real_coords:
                static_spatial = """**🗺️ Interpretación - Mapa Espacial**
                Este gráfico muestra la distribución geográfica de las leyes de cobre en el banco.
                - **Patrones de agrupamiento**: Puntos rojos agrupados indican control geológico estructural (fallas, contactos).
                - **Gradientes de color**: Transiciones suaves de amarillo a rojo sugieren zonas de alteración potásica.
                - **Puntos aislados**: Rojos rodeados de amarillos pueden ser outliers o vetillas locales.
                - **Distribución uniforme**: Colores mezclados al azar = alta nugget effect (más difícil de predecir)."""
            else:
                static_spatial = """**📈 Interpretación - Tendencia Temporal**
                Este gráfico muestra cómo evolucionan las leyes de cobre a lo largo del tiempo (voladura por voladura).
                - **Línea diagonal clara**: Aparece porque el eje X también depende del tiempo. Esto es normal en datos reales de planta.
                - **Color progresivo**: Si los puntos cambian de amarillo a rojo, indica que las leyes están aumentando.
                - **Saltos de color**: Cambios bruscos pueden indicar cambios de zona geológica o problemas de muestreo.
                - **Uso práctico**: Valida si la secuencia de voladuras tiene sentido geológico antes de entrenar la IA."""
            render_dual_interpretation('spatial_map', spatial_data, bench, 'spatial', static_spatial)
    else:
        st.warning("No hay coordenadas espaciales (x, y) disponibles en este dataset para generar el mapa.")


def render_phase3_preparation(bench):
    """Fase 3: Preparacion de Datos"""
    st.header("🛠️ Fase 3: Preparacion de Datos")
    
    st.markdown("""
    **¿Para qué sirve esta fase?**
    Aquí se limpian, transforman y preparan los datos brutos para que los modelos de IA puedan entrenar correctamente.
    Se eliminan valores faltantes, se normalizan features, se codifican variables categóricas y se divide el dataset
    en entrenamiento/validación/prueba. Sin esta fase, los modelos aprenderían de datos sucios o inconsistentes.
    """)
    
    pipeline = TrainingPipeline(bench=bench)
    
    # Intentar cargar datos reales primero (igual que Fase 4)
    try:
        df = pipeline.load_data(bench, use_real_data=True)
        st.success(f"🏭 Datos reales de planta cargados: {len(df)} muestras")
    except Exception:
        df = pipeline.load_data(bench, use_real_data=False)
        st.warning(f"⚠️ Usando datos sintéticos: {len(df)} muestras (no reflejan la planta real)")
    
    st.info(f"Procesando banco {bench}m...")
    
    with st.spinner("Aplicando ingenieria de caracteristicas..."):
        X, y, feature_names, df_clean = pipeline.preprocess(df)
        X_train, X_val, X_test, y_train, y_val, y_test = pipeline.split_data(X, y)
    
    st.success("✅ Datos preparados exitosamente")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Features Generadas", str(len(feature_names)))
    with col2:
        st.metric("Muestras Totales", str(len(y)))
    with col3:
        st.metric("Split", f"{len(y_train)}/{len(y_val)}/{len(y_test)}")
    
    st.subheader("Features Utilizadas")
    st.write(feature_names)
    
    st.subheader("Matriz de Correlacion")
    corr_df = df_clean.select_dtypes(include=[np.number]).corr()
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(corr_df, annot=True, fmt='.2f', cmap='RdYlBu_r', center=0, ax=ax, annot_kws={"size": 8})
    plt.tight_layout()
    st.pyplot(fig)
    
    st.divider()
    corr_dict = corr_df.to_dict()
    # Extraer correlaciones más importantes con el target
    target_corr = {}
    if 'plant_feed_grade' in corr_dict:
        target_corr = {k: round(v, 3) for k, v in corr_dict['plant_feed_grade'].items() if k != 'plant_feed_grade'}
    elif 'cu_bayesian' in corr_dict:
        target_corr = {k: round(v, 3) for k, v in corr_dict['cu_bayesian'].items() if k != 'cu_bayesian'}
    
    corr_data = {
        'features': list(corr_df.columns),
        'target_correlations': target_corr,
        'n_features': len(corr_df.columns)
    }
    static_corr = """**¿Qué demuestra esta matriz?**
    Muestra qué tan relacionadas están las features entre sí y con el target.
    - **Valores cercanos a 1.0 (rojo)**: Correlación positiva fuerte. Si dos features están muy correlacionadas, una es redundante.
    - **Valores cercanos a -1.0 (azul)**: Correlación negativa fuerte. Una sube cuando la otra baja.
    - **Valores cercanos a 0 (blanco)**: Sin correlación. Son features independientes que aportan información única.
    - **Fila `plant_feed_grade` (target)**: Mira qué features tienen mayor correlación con la ley real. Esas serán las más importantes para el modelo."""
    render_dual_interpretation('correlation_matrix', corr_data, bench, 'corr', static_corr)


def render_phase4_modeling(bench):
    """Fase 4: Modelado"""
    st.header("🤖 Fase 4: Modelado - Entrenamiento de 5 Modelos")
    
    st.markdown("""
    **¿Para qué sirve esta fase?**
    Aquí se entrenan los modelos predictivos seleccionados usando los datos preparados en la Fase 3.
    Cada modelo aprende patrones ocultos entre las features (kriging, tonelaje, tendencias temporales)
    y el target (ley real de planta). Puedes elegir entrenar 1, 2, 3... o los 5 modelos a la vez.
    El resultado son modelos capaces de predecir la ley de cobre antes de que la voladura llegue a planta.
    """)
    
    # Opción para usar datos reales de planta (por defecto ACTIVADO)
    # Si el usuario cargó su propio dataset, Mine-to-Mill se desactiva automáticamente
    if st.session_state.dataset is not None:
        use_real_data = False
        st.info(f"📦 Dataset cargado detectado: se entrenará con tus datos ({len(st.session_state.dataset):,} muestras). 'Usar datos reales de planta' queda desactivado.")
    else:
        use_real_data = st.checkbox(
            "📊 Usar datos reales de planta (Mine-to-Mill)",
            value=True,
            help="Entrena los modelos con los datos reales de alimentación a planta en lugar de datos sintéticos de bloques"
        )
    
    if use_real_data:
        st.info("ℹ️ Se usarán datos reales de control de procesos (voladuras con leyes medidas en planta)")
    else:
        st.warning("⚠️ No se usan datos de planta: se usará tu dataset cargado o, a falta de él, datos sintéticos de demostración.")
    
    drillholes_loaded = (st.session_state.dataset is not None
                         and 'hole_id' in st.session_state.dataset.columns
                         and 'cu_base' not in st.session_state.dataset.columns)
    if drillholes_loaded:
        st.info("Experimento espacial con sondajes; el banco seleccionado sólo identifica este resultado.")
    else:
        st.info(f"Entrenando modelos para banco {bench}m...")
    
    # ─── Selección de Modelos a Entrenar ───
    st.markdown("---")
    st.subheader("🎯 Modelos a Entrenar")
    
    col_all, col_none = st.columns(2)
    with col_all:
        if st.button("✅ Seleccionar Todos", use_container_width=True, type="secondary"):
            for key in MODELS.keys():
                st.session_state[f"cb_train_{key}"] = True
            st.rerun()
    with col_none:
        if st.button("❌ Deseleccionar Todos", use_container_width=True, type="secondary"):
            for key in MODELS.keys():
                st.session_state[f"cb_train_{key}"] = False
            st.rerun()
    
    # Inicializar valores por defecto ANTES de crear los widgets
    for key in MODELS.keys():
        if f"cb_train_{key}" not in st.session_state:
            st.session_state[f"cb_train_{key}"] = True
    
    # Checkboxes individuales para cada modelo
    model_cols = st.columns(len(MODELS))
    selected_models = []
    for i, (key, info) in enumerate(MODELS.items()):
        with model_cols[i]:
            checked = st.checkbox(
                f"**{info['name']}**",
                key=f"cb_train_{key}",
                help=f"Tipo: {info['type']}"
            )
            if checked:
                selected_models.append(key)
            
            # Color badge según tipo
            color = "#10b981" if info['type'] == 'CLASSIC' else "#f59e0b"
            st.markdown(f"<span style='font-size:10px;color:{color};font-weight:bold;'>{info['type']}</span>", unsafe_allow_html=True)
    
    if len(selected_models) == 0:
        st.warning("⚠️ Selecciona al menos un modelo para entrenar.")
        st.stop()
    
    st.info(f"📦 {len(selected_models)} modelo(s) seleccionado(s): {', '.join(MODELS[k]['name'] for k in selected_models)}")
    
    # ─── Opciones Avanzadas: Validación Cruzada e Hiperparámetros ───
    st.markdown("---")
    st.subheader("⚙️ Opciones Avanzadas (Validación Cruzada e Hiperparámetros)")
    
    col_cv, col_tune = st.columns(2)
    loaded_dataset = st.session_state.get('dataset')
    grouped_dataset = (loaded_dataset is not None and 'hole_id' in loaded_dataset.columns
                       and 'cu_base' not in loaded_dataset.columns and not use_real_data)
    with col_cv:
        if grouped_dataset:
            st.info("Validación por sondajes completos: una partición de entrenamiento, "
                    "validación y prueba. La CV repetida por filas no se aplica a este dataset.")
        else:
            st.checkbox(
            "🔀 Validación Cruzada Repetida (5×3-fold)",
            value=True,
            key="opt_cv",
            help="Evalúa CADA modelo sobre los MISMOS 15 folds (diseño pareado). Habilita las "
                 "pruebas estadísticas robustas (Friedman, Wilcoxon+Bonferroni, bootstrap). "
                 "Submuestrea hasta 3,000 filas para acotar el tiempo."
        )
    with col_tune:
        st.checkbox(
            "🔧 Optimización de Hiperparámetros (GridSearch)",
            value=True,
            key="opt_tune",
            help="Barre rejillas de RandomForest, XGBoost y NN+Bayesian sobre el validation set "
                 "para elegir los mejores parámetros con evidencia (no valores arbitrarios). "
                 "Submuestrea hasta 3,000 filas."
        )
    
    st.caption("La optimización usa la reserva de validación. El informe identifica las pruebas "
               "efectivamente ejecutadas; una partición única no equivale a validación cruzada.")
    
    if st.button("🚀 Iniciar Entrenamiento", type="primary", use_container_width=True):
        source = st.session_state.get('dataset_source', '') or ''
        quality = st.session_state.get('dataset_quality')
        if source.startswith('Archivo:') and (quality is None or not quality.get('usable_for_training', False)):
            st.error("El CSV cargado no pasó el control de calidad para entrenamiento. Revisa los fallos en Carga de Datos.")
            return
        pipeline = TrainingPipeline(bench=bench)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Paso 1: Cargar datos
        status_text.text("Cargando datos...")
        
        try:
            # Usar dataset cargado si existe
            if st.session_state.dataset is not None and not use_real_data:
                df = st.session_state.dataset.copy()
                drillholes = 'hole_id' in df.columns and 'cu_base' not in df.columns
                bench_col = None if drillholes else ('bench' if 'bench' in df.columns else ('z' if 'z' in df.columns else None))
                if bench_col is not None:
                    df_bench = df[df[bench_col] == bench]
                    if len(df_bench) > 50:
                        df = df_bench
                        st.info(f"Usando dataset cargado: {len(df)} muestras para banco {bench}m")
                    else:
                        st.info(f"Dataset cargado no tiene banco {bench}m ({len(df_bench)} filas). Usando las {len(df)} muestras completas del dataset.")
                else:
                    if drillholes:
                        st.info(f"Sondajes: {len(df)} muestras en {df['hole_id'].nunique()} hoyos. "
                                "Se separan hoyos completos para la prueba; el banco seleccionado sólo identifica el experimento.")
                    else:
                        st.info(f"Usando dataset cargado (sin dimensión de banco): {len(df)} muestras")
            else:
                df = pipeline.load_data(bench, use_real_data=use_real_data)
                if use_real_data:
                    st.info(f"Datos reales de planta cargados: {len(df)} muestras")
        except ValueError as e:
            st.error(f"❌ {e}")
            st.info("💡 Solución: Ve a la pestaña '📁 Carga de Datos' y genera datos sintéticos, O verifica que existan registros de Control de Procesos en el backend para este banco.")
            return
        except Exception as e:
            st.error(f"❌ Error inesperado cargando datos: {e}")
            return
        
        progress_bar.progress(10)
        
        # Paso 2: Preprocesar
        status_text.text("Preprocesando datos...")
        X, y, feature_names, df_clean = pipeline.preprocess(df)
        X_train, X_val, X_test, y_train, y_val, y_test = pipeline.split_data(X, y, df=df_clean)
        progress_bar.progress(25)

        if pipeline.is_drillhole_dataset:
            st.caption("El modelo usa sólo x/y/z; no hay fechas, tonelaje ni bloques. "
                       "Resultados de exploración espacial, sin habilitación para operación.")
        
        if use_real_data:
            st.info(f"📅 Validación walk-forward: {len(y_train)} train / {len(y_val)} val / {len(y_test)} test (orden cronológico)")
        
        # Paso 3: Entrenar (+ optimización de hiperparámetros)
        status_text.text(f"Entrenando {len(selected_models)} modelo(s)... (esto puede tomar varios minutos)")
        
        tune_flag = st.session_state.get('opt_tune', True)
        if tune_flag:
            status_text.text("🔧 Optimizando hiperparámetros (RF / XGB / NN)...")
        
        models = pipeline.train_all_models(
            X_train, y_train, X_val, y_val, models_to_train=selected_models,
            tune_hyperparameters=tune_flag,
            tuning_max_points=TRAIN_CONFIG.get('tuning_max_points', 3000),
            tuning_n_candidates=TRAIN_CONFIG.get('tuning_n_candidates', 15)
        )
        progress_bar.progress(60)
        
        # Paso 3b: Validación cruzada repetida (pareada)
        cv_flag = st.session_state.get('opt_cv', True) and not pipeline.is_drillhole_dataset
        if pipeline.is_drillhole_dataset and st.session_state.get('opt_cv', True):
            st.info("La validación cruzada por filas se omite para evitar mezclar intervalos del mismo sondaje. "
                    "Se evalúa en sondajes completos no vistos.")
        if cv_flag and len(selected_models) > 1:
            status_text.text("🔀 Ejecutando Validación Cruzada Repetida (5×3-fold)...")
            X_cv = np.vstack([X_train[:, :3], X_val[:, :3]])
            y_cv = np.concatenate([y_train, y_val])
            pipeline.run_cross_validation(
                X_cv, y_cv, selected_models,
                max_points=TRAIN_CONFIG.get('cv_max_points', 3000)
            )
            progress_bar.progress(80)
        
        # Paso 4: Evaluar
        status_text.text("Evaluando modelos...")
        results = pipeline.evaluate_all_models(X_test, y_test, pipeline.get_test_frame(df_clean))
        progress_bar.progress(90)
        
        # Paso 5: Guardar
        status_text.text("Guardando resultados...")
        pipeline.save_results()
        
        # Guardar en session_state para persistencia entre paginas
        benchmark_key = f"benchmark_{bench}"
        st.session_state[benchmark_key] = results
        st.session_state['last_trained_bench'] = bench
        st.session_state[f'experiment_profile_{bench}'] = ('drillholes_exploratory'
                                                           if pipeline.is_drillhole_dataset else 'operational')
        st.session_state[f'experiment_revision_{bench}'] = (
            DRILLHOLE_MODEL_REVISION if pipeline.is_drillhole_dataset else None
        )
        st.session_state[f'evaluation_version_{bench}'] = 'group-bootstrap-frozen-batchnorm-v2'
        st.session_state[f'evaluation_date_{bench}'] = datetime.now().isoformat()
        st.session_state[f'experiment_dataset_hash_{bench}'] = (
            drillhole_dataset_fingerprint(df_clean) if pipeline.is_drillhole_dataset else None
        )
        
        # Guardar predicciones para graficos en Fase 5
        if hasattr(pipeline, 'predictions'):
            st.session_state[f"predictions_{bench}"] = pipeline.predictions
        if hasattr(pipeline, 'test_data'):
            st.session_state[f"testdata_{bench}"] = pipeline.test_data
        if hasattr(pipeline, 'models'):
            st.session_state[f"models_{bench}"] = pipeline.models
        # Persistir CV, pruebas estadísticas e hiperparámetros para Fase 5
        st.session_state[f"cv_{bench}"] = pipeline.cv_results or {}
        st.session_state[f"stat_tests_{bench}"] = pipeline.stat_tests or {}
        if hasattr(pipeline, 'hyperparameters') and pipeline.hyperparameters:
            st.session_state[f"hyperparameters_{bench}"] = pipeline.hyperparameters
        
        # Guardar datos completos para predicciones en Fase 6
        st.session_state[f"X_full_{bench}"] = X
        st.session_state[f"y_full_{bench}"] = y
        st.session_state[f"features_{bench}"] = feature_names
        
        progress_bar.progress(100)
        
        st.success("✅ Entrenamiento completado exitosamente!")
        status_text.empty()
        
        # Mostrar resumen
        st.subheader("Resumen de Entrenamiento")
        
        summary_data = []
        for name, metrics in results.items():
            summary_data.append({
                "Modelo": MODELS[name]['name'],
                "Tipo": MODELS[name]['type'],
                "RMSE": f"{metrics['rmse']:.4f}",
                "MAE": f"{metrics['mae']:.4f}",
                "R²": f"{metrics['r2']:.4f}",
                "Score": f"{metrics['composite_score']:.4f}"
            })
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        if pipeline.is_drillhole_dataset:
            st.caption("En sondajes, compare primero RMSE, MAE y R². El Score compuesto es "
                       "orientativo: no es un porcentaje de acierto ni una validación operativa.")


def render_phase5_evaluation(bench):
    """Fase 5: Evaluacion"""
    st.header("📈 Fase 5: Evaluacion Comparativa")
    is_drillhole_experiment = (st.session_state.get(f'experiment_profile_{bench}')
                               == 'drillholes_exploratory')
    if is_drillhole_experiment:
        st.info("Métricas de sondajes completos no vistos. Son resultados exploratorios; "
                "no representan la reconciliación de un banco ni de una planta. "
                "Para elegir el mejor de este experimento, use el menor RMSE; "
                "el Score compuesto es orientativo, no un porcentaje de acierto.")
    
    st.markdown("""
    **¿Para qué sirve esta fase?**
    Aquí se comparan las métricas de todos los modelos entrenados (RMSE, MAE, R², bias, etc.)
    para determinar cuál predice mejor la ley de cobre. Se generan gráficos de diagnóstico
    (predicción vs real, residuales, intervalos bootstrap) para validar que el modelo no tenga
    sesgos y limitaciones. Estos diagnósticos no certifican por sí solos decisiones operacionales.
    """)
    
    # Intentar cargar desde session_state primero
    benchmark_key = f"benchmark_{bench}"
    df_results = None
    
    if benchmark_key in st.session_state:
        # Convertir resultados de session_state a DataFrame
        results = st.session_state[benchmark_key]
        df_data = []
        for name, metrics in results.items():
            df_data.append({
                'model_name': MODELS[name]['name'],
                'model_type': MODELS[name]['type'],
                'rmse': metrics['rmse'],
                'mae': metrics['mae'],
                'r2': metrics['r2'],
                'mape': metrics['mape'],
                'bias': metrics['bias'],
                'composite_score': metrics['composite_score']
            })
        df_results = pd.DataFrame(df_data)
        st.success("✅ Resultados de sondajes cargados desde memoria" if is_drillhole_experiment
                   else f"✅ Resultados cargados desde memoria (Banco {bench}m)")
    else:
        # Fallback a PostgreSQL
        try:
            df_results = get_benchmark_results(bench)
            if not df_results.empty:
                st.info("Resultados cargados desde base de datos")
        except Exception as e:
            st.error(f"Error cargando resultados: {e}")
            return
    
    if df_results is None or df_results.empty:
        st.warning(f"No hay resultados de benchmark para el banco {bench}m. Entrene los modelos primero en Fase 4.")
        return
    
    st.subheader("Resultados — sondajes del dataset cargado" if is_drillhole_experiment
                 else f"Resultados - Banco {bench}m")
    test_frame = st.session_state.get(f'testdata_{bench}', {}).get('df_test')
    test_groups = (test_frame['hole_id'].to_numpy()
                   if is_drillhole_experiment and test_frame is not None and 'hole_id' in test_frame
                   else None)
    if is_drillhole_experiment:
        st.caption("Evaluación en una reserva de sondajes completos. Friedman y Wilcoxon no se "
                   "ejecutaron: no hay resultados de validación cruzada por sondajes.")
        if test_groups is None:
            st.warning("Faltan identificadores de los sondajes de prueba: no se calcularán intervalos por filas.")
    session_predictions = st.session_state.get(f'predictions_{bench}', {})
    corrected_statistics = None
    if session_predictions and (not is_drillhole_experiment or test_groups is not None):
        session_results = st.session_state.get(benchmark_key, {})
        if session_results:
            winner_key = (min(session_results, key=lambda key: session_results[key]['rmse'])
                          if is_drillhole_experiment else
                          max(session_results, key=lambda key: session_results[key]['composite_score']))
            corrected_statistics = run_statistical_analysis(
                session_predictions, winner=winner_key, groups=test_groups,
                cv_metrics=(None if is_drillhole_experiment else
                            st.session_state.get(f'cv_{bench}', {}).get('metrics')))
            archive = evaluation_archive(session_results, session_predictions, test_frame,
                st.session_state.get(f'hyperparameters_{bench}', {}),
                {'source': st.session_state.get('dataset_source'),
                 'dataset_fingerprint': st.session_state.get(f'experiment_dataset_hash_{bench}'),
                 'trained_at': st.session_state.get(f'evaluation_date_{bench}', 'sesión anterior sin fecha registrada'),
                 'training_version': st.session_state.get(f'evaluation_version_{bench}', 'anterior a corrección BatchNorm'),
                 'bootstrap_version': 'groups-v2',
                 'cv_executed': bool(st.session_state.get(f'cv_{bench}')) and not is_drillhole_experiment},
                corrected_statistics)
            st.download_button('Descargar evidencia de esta evaluación (ZIP)', archive,
                               file_name='evaluacion_sondajes.zip', mime='application/zip')
    st.caption("MAPE de esta ejecución: calculado únicamente para leyes medidas ≥ 1 % Cu; "
               "no representa el error porcentual de todas las muestras. Score: indicador referencial.")
    
    # Tabla comparativa
    display_cols = ['model_name', 'model_type', 'rmse', 'mae', 'r2', 'mape', 'composite_score']
    available_cols = [c for c in display_cols if c in df_results.columns]
    st.dataframe(
        df_results[available_cols].round(4),
        use_container_width=True,
        hide_index=True
    )
    
    # Interpretacion comparativa global
    comp_interp = InterpretationEngine.interpret_model_comparison(
        df_results, rank_metric='rmse' if is_drillhole_experiment else 'composite_score'
    )
    comp_static = f"{comp_interp.icon} {comp_interp.text}"
    if comp_interp.action:
        comp_static += f"\n\n💡 **Acción recomendada:** {comp_interp.action}"
    
    comp_data = {
        'models': df_results['model_name'].tolist(),
        'rmse': df_results['rmse'].tolist(),
        'r2': df_results['r2'].tolist(),
        'composite_score': df_results['composite_score'].tolist()
    }
    render_dual_interpretation('metrics_comparison', comp_data, bench, 'comp', comp_static)
    
    # Grafico de barras comparativo
    st.subheader("Comparacion Visual de Metricas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig, ax = plt.subplots(figsize=(8, 5))
        
        models = df_results['model_name'].values
        rmse_vals = df_results['rmse'].values
        colors = [MODEL_COLORS.get(m.split()[0].lower(), '#94a3b8') for m in models]
        
        bars = ax.barh(models, rmse_vals, color=colors, alpha=0.8, edgecolor='black')
        ax.set_xlabel("RMSE (% Cu)")
        ax.set_title("RMSE por Modelo (menor es mejor)")
        ax.grid(True, alpha=0.3, axis='x')
        
        # Destacar el mejor
        best_idx = np.argmin(rmse_vals)
        bars[best_idx].set_edgecolor('#10b981')
        bars[best_idx].set_linewidth(3)
        
        st.pyplot(fig)
        
        # Interpretacion del mejor RMSE
        best_rmse_row = df_results.loc[df_results['rmse'].idxmin()]
        interp_rmse = InterpretationEngine.interpret_rmse(best_rmse_row['rmse'])
        rmse_static = f"{interp_rmse.icon} {interp_rmse.text}"
        if interp_rmse.action:
            rmse_static += f"\n\n💡 **Acción recomendada:** {interp_rmse.action}"
        
        rmse_data = {
            'metric': 'RMSE',
            'best_model': best_rmse_row['model_name'],
            'best_value': float(best_rmse_row['rmse']),
            'all_models': {row['model_name']: float(row['rmse']) for _, row in df_results.iterrows()}
        }
        render_dual_interpretation('metrics_comparison', rmse_data, bench, 'rmse', rmse_static)
    
    with col2:
        fig, ax = plt.subplots(figsize=(8, 5))
        
        r2_vals = df_results['r2'].values
        
        bars = ax.barh(models, r2_vals, color=colors, alpha=0.8, edgecolor='black')
        ax.set_xlabel("R²")
        ax.set_title("R² por Modelo (mayor es mejor)")
        ax.grid(True, alpha=0.3, axis='x')
        ax.set_xlim(min(0, float(np.nanmin(r2_vals))) - 0.1, 1)
        ax.axvline(0, color='#64748b', linewidth=1)
        
        # Destacar el mejor
        best_idx = np.argmax(r2_vals)
        bars[best_idx].set_edgecolor('#10b981')
        bars[best_idx].set_linewidth(3)
        
        st.pyplot(fig)
        
        # Interpretacion del mejor R2
        best_r2_row = df_results.loc[df_results['r2'].idxmax()]
        interp_r2 = InterpretationEngine.interpret_r2(best_r2_row['r2'])
        r2_static = f"{interp_r2.icon} {interp_r2.text}"
        if interp_r2.action:
            r2_static += f"\n\n💡 **Acción recomendada:** {interp_r2.action}"
        
        r2_data = {
            'metric': 'R²',
            'best_model': best_r2_row['model_name'],
            'best_value': float(best_r2_row['r2']),
            'all_models': {row['model_name']: float(row['r2']) for _, row in df_results.iterrows()}
        }
        render_dual_interpretation('metrics_comparison', r2_data, bench, 'r2', r2_static)
    
    # Score compuesto
    st.subheader("Score Compuesto (referencial)" if is_drillhole_experiment
                 else "Score Compuesto (Ranking Final)")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scores = df_results['composite_score'].values
    sorted_idx = np.argsort(scores)[::-1]
    
    sorted_models = [models[i] for i in sorted_idx]
    sorted_scores = scores[sorted_idx]
    sorted_colors = [colors[i] for i in sorted_idx]
    
    bars = ax.bar(range(len(sorted_models)), sorted_scores, color=sorted_colors, alpha=0.8, edgecolor='black')
    ax.set_xticks(range(len(sorted_models)))
    ax.set_xticklabels(sorted_models, rotation=45, ha='right')
    ax.set_ylabel("Score Compuesto")
    ax.set_title("Ranking de Modelos por Score Compuesto")
    ax.grid(True, alpha=0.3, axis='y')
    
    # Destacar ganador
    bars[0].set_edgecolor('#f59e0b')
    bars[0].set_linewidth(4)
    
    # Agregar valores encima de barras
    for i, (bar, score) in enumerate(zip(bars, sorted_scores)):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                f'{score:.3f}', ha='center', va='bottom', fontweight='bold',
                color='white' if i == 0 else 'black')
    
    st.pyplot(fig)
    
    # Interpretacion del ranking
    winner_row = df_results.loc[df_results['composite_score'].idxmax()]
    interp_rank = InterpretationEngine.interpret_composite_ranking(
        winner_row['model_name'], winner_row['composite_score'], rank=1, total_models=len(df_results)
    )
    rank_static = f"{interp_rank.icon} {interp_rank.text}"
    if interp_rank.action:
        rank_static += f"\n\n💡 **Acción recomendada:** {interp_rank.action}"
    
    rank_data = {
        'metric': 'Composite Score',
        'winner': winner_row['model_name'],
        'winner_score': float(winner_row['composite_score']),
        'total_models': len(df_results),
        'all_scores': {row['model_name']: float(row['composite_score']) for _, row in df_results.iterrows()}
    }
    render_dual_interpretation('metrics_comparison', rank_data, bench, 'rank', rank_static)
    
    # ============================================================
    # ROBUSTEZ: VALIDACION CRUZADA, PRUEBAS ESTADISTICAS E HIPERPARAMETROS
    # ============================================================
    
    # ─── 1. Validación Cruzada Repetida ──────────────────────────────
    cv_key = f"cv_{bench}"
    if not is_drillhole_experiment and cv_key in st.session_state and st.session_state.get(cv_key):
        cv_metrics = st.session_state[cv_key]
        n_folds = cv_metrics.get('n_total_folds', 0)
        
        rows = []
        for key, folds in cv_metrics.get('metrics', {}).items():
            for m in folds:
                rows.append({
                    'model': MODELS.get(key, {}).get('name', key),
                    'model_key': key,
                    'RMSE': m['rmse'],
                    'MAE': m['mae'],
                    'R2': m['r2'] if m['r2'] is not None else np.nan
                })
        if rows:
            cv_df = pd.DataFrame(rows)
            cv_sum = cv_df.groupby('model').agg(
                rmse_mean=('RMSE', 'mean'), rmse_std=('RMSE', 'std'),
                mae_mean=('MAE', 'mean'), r2_mean=('R2', 'mean'),
                n_folds=('RMSE', 'count')
            ).reset_index()
            cv_sum['ci_half'] = 1.96 * cv_sum['rmse_std'] / np.sqrt(cv_sum['n_folds'])
            cv_sum['ci_lower'] = cv_sum['rmse_mean'] - cv_sum['ci_half']
            cv_sum['ci_upper'] = cv_sum['rmse_mean'] + cv_sum['ci_half']
            
            st.markdown("---")
            st.subheader("🔀 Validación Cruzada Repetida (5×3-fold = 15 folds pareados)")
            st.caption(
                "Cada modelo se evalúa sobre los **mismos** 15 folds (design pareado). "
                "La desviación entre folds mide la estabilidad del modelo ante distintas particiones de los datos."
            )
            
            tab_cv_table, tab_cv_plot = st.tabs(["📋 Tabla CV", "📊 Regresión de Folds"])
            with tab_cv_table:
                cv_display = cv_sum[['model', 'rmse_mean', 'rmse_std', 'ci_lower', 'ci_upper',
                                     'mae_mean', 'r2_mean', 'n_folds']].copy()
                cv_display.columns = ['Modelo', 'RMSĒ', 'Std', 'IC95% inf', 'IC95% sup',
                                      'MAĒ', 'R²̄', 'Folds']
                st.dataframe(cv_display.round(4), use_container_width=True, hide_index=True)
                st.caption(
                    "Interpretación de la tabla: el modelo con menor RMSĒ domina en promedio. "
                    "Std bajo ⇒ estable; IC95% estrecho ⇒ la estimación es precisa. "
                    "El ganador de CV es el mejor candidato independiente del split único de test."
                )
            with tab_cv_plot:
                fig, ax = plt.subplots(figsize=(10, 5.5))
                import seaborn as sns
                sns.boxplot(data=cv_df.dropna(subset=['RMSE']), x='model', y='RMSE', ax=ax,
                            palette='viridis', fliersize=4)
                ax.set_xlabel("Modelo")
                ax.set_ylabel("RMSE por Fold")
                ax.set_title("Distribución del RMSE en los 15 folds (menor = mejor, caja compacta = estable)")
                ax.grid(True, alpha=0.3, axis='y')
                plt.xticks(rotation=35, ha='right')
                plt.tight_layout()
                st.pyplot(fig)
            
            # Interpretación (dual)
            cv_interp = InterpretationEngine.interpret_cross_validation(cv_sum, n_folds)
            cv_static = f"{cv_interp.icon} {cv_interp.text}"
            if cv_interp.action:
                cv_static += f"\n\n💡 **Acción recomendada:** {cv_interp.action}"
            cv_data = {
                'chart': 'cross_validation',
                'n_folds': n_folds,
                'best_model': cv_sum.loc[cv_sum['rmse_mean'].idxmin(), 'model'],
                'summary': cv_sum.to_dict(orient='records')
            }
            render_dual_interpretation('cross_validation', cv_data, bench, 'cv', cv_static)
    
    # ─── 2. Pruebas Estadísticas Robustas ────────────────────────────
    stat_key = f"stat_tests_{bench}"
    if stat_key in st.session_state and st.session_state.get(stat_key):
        stat = st.session_state[stat_key]
        if is_drillhole_experiment:
            stat = corrected_statistics or {'friedman': {}, 'wilcoxon': [], 'bootstrap': []}
        
        st.markdown("---")
        st.subheader("🧪 Comparaciones estadísticas de la evaluación")
        if is_drillhole_experiment:
            st.caption("Bootstrap por sondajes completos, 2 000 remuestreos pareados, semilla 42. "
                       "Intervalos descriptivos condicionados a estas predicciones; no corrigen la "
                       "selección del ganador sobre la misma prueba ni toda la dependencia espacial.")
        
        friedman = stat.get('friedman', {})
        wilcoxon = stat.get('wilcoxon', [])
        bootstrap = stat.get('bootstrap', [])
        
        col_fri, col_note = st.columns([1, 2])
        with col_fri:
            if friedman.get('p_value') is not None:
                st.metric("Test de Friedman",
                          f"p = {friedman['p_value']:.4f}",
                          delta="Significativo" if friedman.get('significant') else "No significativo",
                          delta_color="normal" if friedman.get('significant') else "off")
            else:
                st.info("Friedman y Wilcoxon no ejecutados: no hay folds comparables."
                        if is_drillhole_experiment else "Sin datos suficientes para Friedman")
        with col_note:
            st.caption(
                "**Friedman** compara todos los modelos sobre los mismos folds (no paramétrico, para datos pareados). "
                "**Wilcoxon pareado + Bonferroni** compara pares de modelos corrigiendo por comparaciones múltiples. "
                "**Bootstrap pareado** remuestrea las observaciones de prueba para estimar el IC95% de ΔRMSE "
                "del ganador frente a cada rival."
            )
        
        tab_stat_table, tab_stat_plot = st.tabs(["📋 Resultados", "📊 ΔRMSE Bootstrap"])
        with tab_stat_table:
            if wilcoxon:
                w_df = pd.DataFrame([{
                    'Modelo A': w['model_a'], 'Modelo B': w['model_b'],
                    'Estadístico': round(w['statistic'], 3) if w['statistic'] is not None else None,
                    'p crudo': round(w['p_value'], 4) if w['p_value'] is not None else None,
                    'α Bonferroni': round(w['bonferroni_alpha'], 4),
                    'CM-A': round(w['mean_rmse_a'], 4), 'CM-B': round(w['mean_rmse_b'], 4),
                    'Significativo': '✅ Sí' if w['significant'] else '❌ No'
                } for w in wilcoxon])
                st.dataframe(w_df, use_container_width=True, hide_index=True)
            if bootstrap:
                b_df = pd.DataFrame([{
                    'Ganador': b['winner'], 'Rival': b['rival'],
                    'ΔRMSE (ganador - rival)': round(b['diff_mean'], 5),
                    'IC95% inf': round(b['ci_lower'], 5),
                    'IC95% sup': round(b['ci_upper'], 5),
                    'Conclusión': ('Intervalo favorece al ganador' if b['ci_upper'] < 0 else
                                   'Intervalo favorece al rival' if b['ci_lower'] > 0 else
                                   'Sin diferencia concluyente')
                } for b in bootstrap])
                st.dataframe(b_df, use_container_width=True, hide_index=True)
            st.caption(
                "Interpretación: p<0.05 tras Bonferroni ⇒ la diferencia entre ese par es estadísticamente "
                "significativa. En bootstrap, un IC95% de ΔRMSE totalmente negativo favorece al ganador; "
                "uno totalmente positivo favorece al rival."
            )
        with tab_stat_plot:
            if bootstrap:
                fig, ax = plt.subplots(figsize=(10, 5.5))
                names = [f"{b['winner']} vs {b['rival']}" for b in bootstrap]
                diffs = [b['diff_mean'] for b in bootstrap]
                lows = [b['ci_lower'] for b in bootstrap]
                highs = [b['ci_upper'] for b in bootstrap]
                y = np.arange(len(names))
                colors_bar = ['#10b981' if hi < 0 else '#ef4444' if lo > 0 else '#94a3b8'
                              for lo, hi in zip(lows, highs)]
                ax.barh(y, diffs, color=colors_bar, alpha=0.85, edgecolor='black')
                ax.errorbar(diffs, y, xerr=[np.abs(np.array(diffs)-np.array(lows)), np.abs(np.array(highs)-np.array(diffs))],
                            fmt='none', ecolor='black', capsize=4)
                ax.axvline(0, color='red', linestyle='--', lw=2)
                ax.set_yticks(y); ax.set_yticklabels(names)
                ax.set_xlabel("ΔRMSE (IC95%) — negativo favorece al ganador")
                ax.set_title("Bootstrap pareado: diferencia de RMSE entre ganador y rivales")
                ax.grid(True, alpha=0.3, axis='x')
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("No hay comparaciones bootstrap: se requiere más de un modelo entrenado.")
        
        stat_interp = InterpretationEngine.interpret_statistical_tests(stat)
        stat_static = f"{stat_interp.icon} {stat_interp.text}"
        if stat_interp.action:
            stat_static += f"\n\n💡 **Acción recomendada:** {stat_interp.action}"
        stat_data = {'chart': 'statistical_tests', 'friedman_p': friedman.get('p_value'),
                     'n_wilcoxon': len(wilcoxon), 'n_bootstrap': len(bootstrap)}
        render_dual_interpretation('statistical_tests', stat_data, bench, 'stat', stat_static)
    
    # ─── 3. Optimización de Hiperparámetros ──────────────────────────
    hp_key = f"hyperparameters_{bench}"
    if hp_key in st.session_state and st.session_state.get(hp_key):
        tuning = st.session_state[hp_key]
        tun = tuning.get('tuning', {})
        
        if tun:
            st.markdown("---")
            st.subheader("🔧 Optimización de Hiperparámetros (GridSearch sobre validation)")
            st.caption(
                "Se exploraron rejillas de **RandomForest** (n_estimators, max_depth, min_samples_split), "
                "**XGBoost** (n_estimators, max_depth, learning_rate) y **NN+Bayesian** (epochs, learning_rate). "
                "La última columna cuantifica la mejora frente a usar valores por defecto."
            )
            
            tab_hp_table, tab_hp_curve = st.tabs(["📋 Resultados", "📈 Curvas de Tuning"])
            with tab_hp_table:
                hp_rows = [{
                    'Modelo': MODELS.get(k, {}).get('name', k),
                    'Mejor parámetros': str(r.get('best_params', {})),
                    'val-RMSE mejor': round(r['best_rmse'], 4),
                    'val-RMSE default': round(r.get('default_rmse', float('nan')), 4),
                    'Mejora (%)': round(r.get('improvement_pct', 0.0), 1),
                    'Candidatos': r.get('n_candidates', 0)
                } for k, r in tun.items() if isinstance(r, dict) and 'best_rmse' in r]
                if hp_rows:
                    st.dataframe(pd.DataFrame(hp_rows), use_container_width=True, hide_index=True)
                st.caption(
                    "Interpretación: una mejora >0% indica que el modelo final fue configurado con evidencia "
                    "empírica (datos de validación), no con valores arbitrarios. Los parámetros finales quedan "
                    "registrados para el anexo técnico del reporte."
                )
            with tab_hp_curve:
                n_models = len(tun)
                fig, axes = plt.subplots(1, max(n_models, 1), figsize=(max(10, 5*n_models), 4.5), squeeze=False)
                for idx, (k, r) in enumerate(tun.items()):
                    ax = axes[0][idx]
                    evals = sorted(r.get('evaluations', []), key=lambda e: e.get('val_rmse', 0))
                    if not evals or 'best_rmse' not in r:
                        ax.axis('off')
                        continue
                    evals = r.get('evaluations', [])
                    rmses = [e['val_rmse'] for e in evals]
                    labels = [f"C{i}" for i in range(1, len(evals)+1)]
                    ax.plot(range(len(evals)), rmses, 'o-', color=MODEL_COLORS.get(k, '#6366f1'))
                    ax.fill_between(range(len(evals)), rmses, min(rmses)*0.9, alpha=0.15,
                                    color=MODEL_COLORS.get(k, '#6366f1'))
                    ax.axhline(r.get('default_rmse', max(rmses)), color='red', linestyle='--', lw=1,
                               label=f"default={r.get('default_rmse', 0):.3f}")
                    ax.set_title(MODELS.get(k, {}).get('name', k))
                    ax.set_xticks(range(len(evals)))

                    ax.set_xticklabels(labels, rotation=45, ha='right')
                    ax.set_xlabel("Candidato (ordenado por val-RMSE)")
                    ax.set_ylabel("val-RMSE")
                    ax.legend(fontsize=8)
                    ax.grid(True, alpha=0.3)
                plt.suptitle("Curvas de validación por modelo (rojo punteado = default)", y=1.03)
                plt.tight_layout()
                st.pyplot(fig)
            
            hp_interp = InterpretationEngine.interpret_hyperparameters(tuning)
            hp_static = f"{hp_interp.icon} {hp_interp.text}"
            if hp_interp.action:
                hp_static += f"\n\n💡 **Acción recomendada:** {hp_interp.action}"
            hp_data = {'chart': 'hyperparameters',
                       'models': {k: r.get('best_params', {}) for k, r in tun.items() if isinstance(r, dict)}}
            render_dual_interpretation('hyperparameters', hp_data, bench, 'hp', hp_static)
    
    # ============================================================
    # GRAFICOS AVANZADOS DE EVALUACION
    # ============================================================
    
    pred_key = f"predictions_{bench}"
    if pred_key in st.session_state:
        predictions = st.session_state[pred_key]
        
        st.markdown("---")
        st.subheader("📊 Diagnóstico de Modelos - Análisis Avanzado")
        
        # 1. Predicción vs Real
        st.markdown("**1. Predicción vs Real (Ley de Cobre % Cu)**")
        st.caption("Los puntos deben agruparse cerca de la línea 1:1 (negra punteada). Cuanto más dispersos, peor el modelo.")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        for idx, (name, preds) in enumerate(predictions.items()):
            if idx >= 5:
                break
            ax = axes[idx]
            y_true = preds['y_true']
            y_pred = preds['y_pred']
            
            ax.scatter(y_true, y_pred, alpha=0.5, s=20, color=MODEL_COLORS.get(name, '#94a3b8'))
            
            # Línea 1:1
            min_val = min(y_true.min(), y_pred.min())
            max_val = max(y_true.max(), y_pred.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', lw=2, label='1:1 Ideal')
            
            ax.set_xlabel("Real (% Cu)")
            ax.set_ylabel("Predicho (% Cu)")
            ax.set_title(f"{MODELS[name]['name']}\nR² = {df_results[df_results['model_name'] == MODELS[name]['name']]['r2'].values[0]:.3f}")
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Interpretacion de Prediccion vs Real
        winner_pred = df_results.loc[df_results['rmse'].idxmin() if is_drillhole_experiment
                                     else df_results['composite_score'].idxmax()]
        pred_static = (f"**{winner_pred['model_name']}** encabeza el criterio de comparación "
                       f"(R²={winner_pred['r2']:.3f}). Revise la dispersión respecto de la línea 1:1 "
                       "y los errores en leyes altas; esta gráfica no identifica por sí sola su causa geológica.")
        pred_data = {
            'chart': 'prediction_vs_real',
            'winner': winner_pred['model_name'],
            'winner_r2': float(winner_pred['r2']),
            'models': {name: {'r2': float(df_results[df_results['model_name'] == MODELS[name]['name']]['r2'].values[0])} for name in predictions.keys()}
        }
        render_dual_interpretation('prediction_vs_real', pred_data, bench, 'pred_real', pred_static)
        
        # 2. Análisis de Residuales
        st.markdown("**2. Análisis de Residuales (Real - Predicho)**")
        st.caption("Los residuales deben distribuirse aleatoriamente alrededor de 0 sin patrones. Patrones indican sesgo.")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        for idx, (name, preds) in enumerate(predictions.items()):
            if idx >= 5:
                break
            ax = axes[idx]
            residuals = preds['residuals']
            y_pred = preds['y_pred']
            
            ax.scatter(y_pred, residuals, alpha=0.5, s=20, color=MODEL_COLORS.get(name, '#94a3b8'))
            ax.axhline(y=0, color='red', linestyle='--', lw=2)
            
            ax.set_xlabel("Predicho (% Cu)")
            ax.set_ylabel("Residual (% Cu)")
            ax.set_title(f"{MODELS[name]['name']}")
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Interpretacion de Residuales
        res_lines = []
        has_issue = False
        for name, preds in predictions.items():
            interp_res = InterpretationEngine.interpret_residuals(preds['residuals'])
            res_lines.append(f"**{MODELS[name]['name']}**: {interp_res.icon} {interp_res.text}")
            if interp_res.severity in ['warning', 'danger']:
                has_issue = True
        
        if not has_issue:
            res_static = "✅ Todos los modelos muestran residuales bien balanceados alrededor de cero. No se detectan patrones sistematicos de sesgo."
        else:
            res_static = "\n\n".join(res_lines)
        
        res_data = {
            'chart': 'residuals',
            'models': {name: {'mean_residual': float(preds['residuals'].mean()), 'std_residual': float(preds['residuals'].std())} for name, preds in predictions.items()}
        }
        render_dual_interpretation('residuals', res_data, bench, 'residuals', res_static)
        
        # 3. Histograma de Residuales (Q-Q simplificado)
        st.markdown("**3. Distribución de Residuales**")
        st.caption("Revise sesgo, dispersión y valores extremos. La normalidad de los residuales "
                   "no es un requisito general para estos modelos predictivos.")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        for idx, (name, preds) in enumerate(predictions.items()):
            if idx >= 5:
                break
            ax = axes[idx]
            residuals = preds['residuals']
            
            ax.hist(residuals, bins=30, color=MODEL_COLORS.get(name, '#94a3b8'), 
                   alpha=0.7, edgecolor='black', density=True)
            
            # Línea de media
            mean_res = residuals.mean()
            ax.axvline(mean_res, color='red', linestyle='--', lw=2, label=f'Media: {mean_res:.4f}')
            
            ax.set_xlabel("Residual (% Cu)")
            ax.set_ylabel("Densidad")
            ax.set_title(f"{MODELS[name]['name']}")
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # 4. Bootstrap Confidence Intervals para RMSE
        st.markdown("**4. Intervalos de Confianza Bootstrap (RMSE)**")
        st.caption("1 000 remuestreos con semilla 42. En sondajes se remuestrean perforaciones "
                   "completas; las barras son intervalos percentiles descriptivos del 95 % para el RMSE.")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bootstrap_results = []
        
        for name, preds in predictions.items():
            y_true = preds['y_true']
            y_pred = preds['y_pred']
            if is_drillhole_experiment and test_groups is None:
                break
            boot_summary = rmse_bootstrap(y_true, y_pred, groups=test_groups)
            ci_lower = boot_summary['ci_lower']
            ci_upper = boot_summary['ci_upper']
            rmse_mean = boot_summary['rmse_mean']
            
            bootstrap_results.append({
                'model': MODELS[name]['name'],
                'rmse_mean': rmse_mean,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper
            })
        
        # Graficar
        y_pos = np.arange(len(bootstrap_results))
        colors = [MODEL_COLORS.get(name, '#94a3b8') for name in predictions.keys()]
        
        for i, (br, color) in enumerate(zip(bootstrap_results, colors)):
            ax.errorbar(br['rmse_mean'], i, 
                       xerr=[[br['rmse_mean'] - br['ci_lower']], [br['ci_upper'] - br['rmse_mean']]], 
                       fmt='o', color=color, ecolor=color, capsize=5, capthick=2, markersize=10)
            ax.text(br['rmse_mean'], i + 0.15, f"{br['rmse_mean']:.4f}", ha='center', fontsize=9)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels([br['model'] for br in bootstrap_results])
        ax.set_xlabel("RMSE (% Cu)")
        ax.set_title("Intervalos de Confianza Bootstrap 95% para RMSE")
        ax.grid(True, alpha=0.3, axis='x')
        
        st.pyplot(fig)
        
        # Interpretacion de Bootstrap
        boot_lines = []
        has_boot_issue = False
        for br in bootstrap_results:
            interp_boot = InterpretationEngine.interpret_bootstrap_ci(
                br['rmse_mean'], br['ci_lower'], br['ci_upper'], br['model']
            )
            boot_lines.append(f"**{br['model']}**: {interp_boot.icon} {interp_boot.text}")
            if interp_boot.severity in ['warning', 'danger']:
                has_boot_issue = True
        
        if not has_boot_issue:
            boot_static = "Los intervalos describen variación por remuestreo de la reserva de prueba; no certifican reproducibilidad ni incertidumbre de cada cubo."
        else:
            boot_static = "\n\n".join(boot_lines)
        
        boot_data = {
            'chart': 'bootstrap',
            'models': {br['model']: {'rmse_mean': br['rmse_mean'], 'ci_lower': br['ci_lower'], 'ci_upper': br['ci_upper']} for br in bootstrap_results}
        }
        render_dual_interpretation('bootstrap', boot_data, bench, 'bootstrap', boot_static)
        
        # 5. Tabla resumen de bootstrap
        st.subheader("📋 Resumen Bootstrap")
        bootstrap_df = pd.DataFrame(bootstrap_results, columns=['model', 'rmse_mean', 'ci_lower', 'ci_upper'])
        bootstrap_df['IC 95%'] = bootstrap_df.apply(lambda x: f"[{x['ci_lower']:.4f}, {x['ci_upper']:.4f}]", axis=1)
        st.dataframe(bootstrap_df[['model', 'rmse_mean', 'IC 95%']].round(4), use_container_width=True, hide_index=True)
        
        # 6. Prueba de estabilidad (perturbación de datos)
        models_key = f"models_{bench}"
        testdata_key = f"testdata_{bench}"
        
        if models_key in st.session_state and testdata_key in st.session_state:
            st.markdown("**5. Análisis de Estabilidad (Perturbación de Datos)**")
            st.caption("Ruido gaussiano en las coordenadas, con desviación de 0 a 0.2 m para sondajes. "
                       "Cinco repeticiones por nivel, semilla 42 y perturbaciones compartidas entre modelos. "
                       "Mide sensibilidad local a pequeños cambios de posición, no robustez espacial general.")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            noise_levels = [0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2]
            models_dict = st.session_state[models_key]
            X_base = st.session_state[testdata_key]['X_test']
            y_base = st.session_state[testdata_key]['y_test']
            
            stability_data = {}  # Guardar para interpretacion
            
            for name, model in models_dict.items():
                try:
                    curve = stability_curve(model, X_base, y_base,
                                            predictions[name]['y_pred'], noise_levels)
                except ValueError as exc:
                    st.warning(f"{MODELS[name]['name']}: {exc}")
                    continue
                rmse_by_noise = curve['rmse']
                
                stability_data[name] = rmse_by_noise
                
                ax.plot(noise_levels, rmse_by_noise, 'o-', label=MODELS[name]['name'], 
                       color=MODEL_COLORS.get(name, '#94a3b8'), linewidth=2, markersize=6)
            
            ax.set_xlabel("Desviación del ruido (m)" if is_drillhole_experiment else "Desviación del ruido (unidades de entrada)")
            ax.set_ylabel("RMSE (% Cu)")
            ax.set_title("Estabilidad del Modelo ante Perturbaciones")
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            st.pyplot(fig)
            
            # Interpretacion de estabilidad
            stab_lines = []
            has_stab_issue = False
            for name, rmse_by_noise in stability_data.items():
                interp_stab = InterpretationEngine.interpret_stability(
                    noise_levels, rmse_by_noise, MODELS[name]['name']
                )
                stab_lines.append(f"**{MODELS[name]['name']}**: {interp_stab.icon} {interp_stab.text}")
                if interp_stab.severity in ['danger', 'warning']:
                    has_stab_issue = True
            
            if not has_stab_issue:
                winner_name = df_results.loc[df_results['rmse'].idxmin() if is_drillhole_experiment
                                             else df_results['composite_score'].idxmax(), 'model_name']
                stab_static = f"🏆 **{winner_name}** (ganador): Todos los modelos muestran buena estabilidad ante perturbaciones."
            else:
                stab_static = "\n\n".join(stab_lines)
            if is_drillhole_experiment:
                stab_static = ("Sensibilidad local ante desplazamientos pequeños de coordenadas. "
                               "Se muestran únicamente modelos cuya predicción inicial coincide con la "
                               "evaluación guardada. Este ensayo no acredita generalización a otras zonas.")
            
            stab_data = {
                'chart': 'stability',
                'noise_levels': noise_levels,
                'models': {MODELS[name]['name']: rmse_by_noise for name, rmse_by_noise in stability_data.items()}
            }
            render_dual_interpretation('stability', stab_data, bench, 'stability', stab_static)


def render_exploratory_phase6(bench):
    """Publica el experimento de sondajes en una ruta separada del banco operativo."""
    from model_registry import (export_drillhole_experiment,
                                get_drillhole_experiment_metadata)

    st.info("Despliegue exploratorio GeoMet: predice Cu medido a partir de X/Y/Z. "
            "No modifica el modelo activo, las predicciones de planta ni el banco seleccionado.")
    results = st.session_state.get(f"benchmark_{bench}")
    models = st.session_state.get(f"models_{bench}")
    coordinates = st.session_state.get(f"X_full_{bench}")
    current_revision = st.session_state.get(f"experiment_revision_{bench}") == DRILLHOLE_MODEL_REVISION
    current_dataset = drillhole_dataset_fingerprint(st.session_state.get('dataset'))
    same_dataset = (current_dataset is not None and current_dataset ==
                    st.session_state.get(f"experiment_dataset_hash_{bench}"))
    if results and models and coordinates is not None and current_revision and same_dataset:
        winner_key = min(results, key=lambda key: results[key]['rmse'])
        winner = results[winner_key]
        st.subheader("Modelo seleccionado para exploración")
        st.write(f"**{MODELS[winner_key]['name']}** — menor RMSE en sondajes completos no vistos")
        c1, c2, c3 = st.columns(3)
        c1.metric("RMSE (% Cu)", f"{winner['rmse']:.4f}")
        c2.metric("MAE (% Cu)", f"{winner['mae']:.4f}")
        c3.metric("R²", f"{winner['r2']:.4f}")
        st.caption("El Score compuesto es orientativo. Estas métricas describen un experimento "
                   "de exploración; no validan control de planta ni estimación de recursos.")
        if st.button("Publicar modelo exploratorio para el frontend", type="primary"):
            try:
                metadata = export_drillhole_experiment(
                    models[winner_key], MODELS[winner_key]['name'], winner, coordinates
                )
                st.success(f"{metadata['model_name']} publicado en el servicio exploratorio. "
                           "Abre 'Sondajes GeoMet' en el frontend para consultar X/Y/Z.")
            except Exception as exc:
                st.error(f"No se pudo publicar el experimento: {exc}")
    else:
        st.warning("Vuelve a entrenar con el CSV de sondajes actualmente cargado en Fase 4 "
                   "usando esta versión del motor para seleccionar y publicar el ganador.")

    published = get_drillhole_experiment_metadata()
    if published:
        st.markdown("---")
        st.subheader("Experimento publicado actualmente")
        st.write(f"**{published['model_name']}** — {published['exported_at']}")
        st.write("Ruta de consulta en el GD: `Sondajes GeoMet` → predicción por X/Y/Z.")


def render_phase6_deployment(bench):
    """Fase 6: Seleccion y Despliegue"""
    st.header("🏆 Fase 6: Seleccion del Modelo Ganador")
    loaded = st.session_state.get('dataset')
    current_drillholes = drillhole_dataset_fingerprint(loaded) is not None
    previous_drillholes = (st.session_state.get(f'experiment_profile_{bench}')
                           == 'drillholes_exploratory')
    if current_drillholes:
        render_exploratory_phase6(bench)
        return
    if previous_drillholes:
        st.warning("El dataset de sondajes del entrenamiento ya no está cargado. "
                   "Carga el CSV y vuelve a entrenar antes de publicar otro modelo.")
        return
    
    st.markdown("""
    **¿Para qué sirve esta fase?**
    Aquí se selecciona el modelo con mejor desempeño y se activa como modelo oficial del banco.
    Al activarlo, sus predicciones se envían al backend y aparecen en el Dashboard de Reconciliación
    Mine-to-Mill del frontend React. Desde ese momento, el equipo operativo puede comparar
    las predicciones de la IA contra la alimentación real de planta y detectar drift o desviaciones.
    También se generan reportes PDF/Excel para documentación JORC.
    """)
    
    # Intentar cargar desde session_state primero
    benchmark_key = f"benchmark_{bench}"
    df_results = None
    
    if benchmark_key in st.session_state:
        results = st.session_state[benchmark_key]
        df_data = []
        for name, metrics in results.items():
            df_data.append({
                'model_name': MODELS[name]['name'],
                'model_type': MODELS[name]['type'],
                'rmse': metrics['rmse'],
                'mae': metrics['mae'],
                'r2': metrics['r2'],
                'mape': metrics['mape'],
                'bias': metrics['bias'],
                'composite_score': metrics['composite_score']
            })
        df_results = pd.DataFrame(df_data)
        st.success(f"✅ Resultados cargados desde memoria (Banco {bench}m)")
    else:
        # Fallback a PostgreSQL
        try:
            df_results = get_benchmark_results(bench)
            if not df_results.empty:
                st.info("Resultados cargados desde base de datos")
        except Exception as e:
            st.error(f"Error cargando resultados: {e}")
            return
    
    if df_results is None or df_results.empty:
        st.warning(f"No hay resultados para el banco {bench}m. Entrene primero en Fase 4.")
        return
    
    # Determinar ganador
    winner_idx = df_results['composite_score'].idxmax()
    winner_row = df_results.loc[winner_idx]
    
    st.subheader("Modelo Ganador")

    # 4 metricas del modelo ganador en una fila (cards con soporte claro/oscuro)
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown(f"""
        <div class="kpi-card kpi-rmse">
            <div class="kpi-value">{winner_row['rmse']:.4f}%</div>
            <div class="kpi-label">RMSE</div>
            <div class="kpi-sub">Error cuadratico medio</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="kpi-card kpi-r2">
            <div class="kpi-value">{winner_row['r2']:.4f}</div>
            <div class="kpi-label">R²</div>
            <div class="kpi-sub">Coef. de determinacion</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="kpi-card kpi-mae">
            <div class="kpi-value">{winner_row['mae']:.4f}%</div>
            <div class="kpi-label">MAE</div>
            <div class="kpi-sub">Error absoluto medio</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div class="kpi-card kpi-mape">
            <div class="kpi-value">{winner_row['mape']:.2f}%</div>
            <div class="kpi-label">MAPE</div>
            <div class="kpi-sub">Error porcentual medio</div>
        </div>
        """, unsafe_allow_html=True)

    # Nombre del modelo ganador + score (card a ancho completo con modo oscuro)
    st.markdown(f"""
    <div class="winner-card">
        <div class="winner-name">🏆 {winner_row['model_name']}</div>
        <div class="winner-type">Tipo: {winner_row['model_type']}</div>
        <div class="winner-score-box">
            <div class="winner-score-value">{winner_row['composite_score']:.4f}</div>
            <div class="winner-score-label">Score Compuesto</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Interpretacion completa del modelo ganador
    st.markdown("---")
    st.subheader("📋 Diagnóstico Completo del Modelo Ganador")
    
    winner_metrics = {
        'rmse': winner_row['rmse'],
        'r2': winner_row['r2'],
        'mae': winner_row['mae'],
        'mape': winner_row['mape'],
        'bias': winner_row['bias']
    }
    
    full_interps = InterpretationEngine.interpret_model_full(winner_metrics, winner_row['model_name'])
    winner_static_lines = []
    for interp in full_interps:
        line = f"{interp.icon} {interp.text}"
        if interp.action:
            line += f"\n💡 Acción recomendada: {interp.action}"
        winner_static_lines.append(line)
    winner_static = "\n\n".join(winner_static_lines)
    
    winner_data = {
        'model_name': winner_row['model_name'],
        'rmse': float(winner_row['rmse']),
        'r2': float(winner_row['r2']),
        'mae': float(winner_row['mae']),
        'mape': float(winner_row['mape']),
        'bias': float(winner_row['bias']),
        'composite_score': float(winner_row['composite_score'])
    }
    render_dual_interpretation('winner_diagnostic', winner_data, bench, 'winner', winner_static)
    
    # Boton para activar modelo
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pressed_activate = st.button("✅ Activar Modelo Ganador", type="primary", use_container_width=True)
    
    with col2:
        if st.button("📊 Generar Reportes", use_container_width=True):
            with st.spinner("Generando reportes profesionales... Esto puede tomar 10-20 segundos."):
                try:
                    # 1. Recolectar datos
                    collector = ReportDataCollector(bench)
                    report_data = collector.collect_all(st.session_state)
                    
                    if not collector.has_data():
                        st.error("No hay datos suficientes para generar el reporte. Entrena primero en Fase 4.")
                    else:
                        # 2. Renderizar graficos
                        renderer = ChartRenderer()
                        chart_paths = renderer.render_all(report_data)
                        
                        # 3. Generar Excel
                        excel_bytes = generate_excel_report(report_data, bench)
                        
                        # 4. Generar PDF (con analisis IA opcional)
                        ai_text = None
                        try:
                            from utils.ai_analysis import generate_ai_interpretation
                            ai_text = generate_ai_interpretation(report_data['benchmark'], bench)
                        except Exception:
                            pass  # IA es opcional
                        
                        pdf_bytes = generate_pdf_report(report_data, bench, chart_paths, ai_text)
                        
                        # 5. Limpiar graficos temporales
                        renderer.cleanup()
                        
                        # 6. Mostrar botones de descarga
                        st.success("✅ Reportes generados exitosamente!")
                        
                        timestamp = report_data['metadata']['timestamp'].replace(':', '-').replace(' ', '_')
                        
                        col_pdf, col_excel = st.columns(2)
                        with col_pdf:
                            st.download_button(
                                label="📄 Descargar Reporte PDF",
                                data=pdf_bytes,
                                file_name=f"M6_Reporte_Banco{bench}_{timestamp}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        with col_excel:
                            st.download_button(
                                label="📊 Descargar Reporte Excel",
                                data=excel_bytes,
                                file_name=f"M6_Reporte_Banco{bench}_{timestamp}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        
                        st.info("El PDF incluye portada, graficos de alta resolucion, interpretaciones automaticas "
                                f"{'y analisis con IA.' if ai_text else 'y diagnosticos completos.'}")
                        
                except Exception as e:
                    import traceback
                    st.error(f"❌ Error generando reportes: {e}")
                    with st.expander("Ver detalles tecnicos del error (para debugging)"):
                        st.code(traceback.format_exc(), language='python')
                    st.info("Sugerencias: (1) Reinicia Streamlit, (2) Ejecuta: python -c \"import fpdf; print(fpdf.__version__)\" , (3) Si el error es 'self is not defined', borra las carpetas __pycache__ y reinicia.")
    
    # ─── Diagnóstico de Activación (a ancho completo, no dividido en columnas) ───
    if pressed_activate:
        try:
            # 1. Activar modelo con metricas completas
            activate_model(
                bench=bench,
                model_name=winner_row['model_name'],
                composite_score=winner_row['composite_score'],
                rmse=winner_row['rmse'],
                r2=winner_row['r2'],
                mae=winner_row['mae'],
                mape=winner_row['mape'],
                bias=winner_row['bias']
            )
            
            # 2. Guardar en session_state para persistencia
            active_key = f"active_{bench}"
            st.session_state[active_key] = {
                'bench': bench,
                'model_name': winner_row['model_name'],
                'composite_score': winner_row['composite_score'],
                'rmse': winner_row['rmse'],
                'r2': winner_row['r2'],
                'mae': winner_row['mae'],
                'mape': winner_row['mape'],
                'bias': winner_row['bias']
            }
            
            st.success(f"✅ Modelo '{winner_row['model_name']}' activado para banco {bench}m")
            
            # 3. Generar y enviar predicciones del modelo ganador al backend
            models_key = f"models_{bench}"
            X_full_key = f"X_full_{bench}"
            y_full_key = f"y_full_{bench}"
            
            st.markdown("---")
            st.subheader("🔍 Diagnóstico de Activación")
            
            has_models = models_key in st.session_state
            has_X_full = X_full_key in st.session_state
            has_y_full = y_full_key in st.session_state
            
            diag_cols = st.columns(3)
            with diag_cols[0]:
                st.metric("Models en memoria", "Sí" if has_models else "No")
            with diag_cols[1]:
                st.metric("X_full en memoria", "Sí" if has_X_full else "No")
            with diag_cols[2]:
                st.metric("y_full en memoria", "Sí" if has_y_full else "No")
            
            if has_models and has_X_full:
                # Mapear nombre del modelo a key del diccionario
                winner_model_key = None
                for k, v in MODELS.items():
                    if v['name'] == winner_row['model_name']:
                        winner_model_key = k
                        break
                
                if winner_model_key and winner_model_key in st.session_state[models_key]:
                    winner_model = st.session_state[models_key][winner_model_key]
                    X_full = st.session_state[X_full_key]
                    
                    # Hacer predicciones sobre TODOS los datos (no solo test)
                    if hasattr(winner_model, 'predict_with_uncertainty'):
                        predictions, _, _, _ = winner_model.predict_with_uncertainty(X_full)
                    else:
                        predictions = winner_model.predict(X_full)
                    
                    preds_arr = np.array(predictions)
                    
                    # Detalles tecnicos colapsados para mantener la seccion limpia
                    with st.expander("🔬 Detalles técnicos del diagnóstico"):
                        st.write(f"🎯 Modelo ganador key: `{winner_model_key}`")
                        st.write(f"📦 Keys disponibles en models: {list(st.session_state[models_key].keys())}")
                        st.write(f"📐 X_full shape: {X_full.shape}")
                        st.write(f"📐 X_full dtype: {X_full.dtype}")
                        st.write(f"📐 X_full min/mean/max: {X_full.min():.4f} / {X_full.mean():.4f} / {X_full.max():.4f}")
                        st.write(f"📊 Predicciones shape: {preds_arr.shape}")
                        st.write(f"📊 Predicciones min/mean/max: {preds_arr.min():.4f} / {preds_arr.mean():.4f} / {preds_arr.max():.4f}")
                        st.write(f"📊 Primeras 5 predicciones: {preds_arr[:5].tolist()}")
                        st.write(f"📊 Últimas 5 predicciones: {preds_arr[-5:].tolist()}")
                    
                    # Validación: ¿las predicciones tienen sentido?
                    if has_y_full:
                        y_full = st.session_state[y_full_key]
                        
                        pred_mean = float(preds_arr.mean())
                        y_mean = float(y_full.mean())
                        
                        if abs(pred_mean - y_mean) > 0.5:
                            st.error(f"⚠️ ALERTA: Media de predicciones ({pred_mean:.4f}) muy diferente a media real ({y_mean:.4f}). "
                                     f"Esto indica que el modelo en memoria NO es el que obtuvo RMSE {winner_row['rmse']:.4f}. "
                                     f"**Debes re-entrenar en Fase 4 y activar INMEDIATAMENTE en la misma pestaña.**")
                        else:
                            st.success(f"✅ Predicciones coherentes con datos reales (media pred={pred_mean:.4f} vs real={y_mean:.4f})")
                    
                    # Exportar el modelo ganador al registro de inferencia (servicio FastAPI en vivo)
                    try:
                        from model_registry import export_winner
                        export_winner(winner_model, winner_row['model_name'], bench, {
                            'rmse': float(winner_row['rmse']),
                            'r2': float(winner_row['r2']),
                            'mae': float(winner_row['mae']),
                            'mape': float(winner_row['mape']),
                            'bias': float(winner_row['bias']),
                            'composite_score': float(winner_row['composite_score'])
                        })
                        st.success(f"🗂️ Modelo '{winner_row['model_name']}' exportado al registro de inferencia en vivo (banco {bench}m).")
                    except Exception as exp_err:
                        st.warning(f"⚠️ No se pudo exportar el modelo al registro de inferencia: {exp_err}")
                    
                    # Enviar predicciones al backend
                    pred_result = send_predictions_to_api(
                        bench=bench,
                        model_name=winner_row['model_name'],
                        predictions=preds_arr.tolist()
                    )
                    
                    if pred_result.get('success'):
                        st.success(f"📊 Predicciones enviadas al sistema ({pred_result.get('records_updated', 0)} registros)")
                        
                        # Mostrar predicciones vs reales para verificación visual inmediata
                        if has_y_full:
                            y_full = st.session_state[y_full_key]
                            st.subheader("📋 Verificación: Predicciones vs Reales (primeras 10)")
                            verify_df = pd.DataFrame({
                                'Predicción': preds_arr[:10].round(4),
                                'Real': y_full[:10].round(4),
                                'Error': (y_full[:10] - preds_arr[:10]).round(4)
                            })
                            st.dataframe(verify_df, use_container_width=True)
                            
                            # Interpretacion dual: IA (izquierda) y Deterministica (derecha)
                            pred_mean = float(preds_arr.mean())
                            y_mean = float(y_full.mean())
                            act_static_lines = [
                                f"🏆 **{winner_row['model_name']}** activado oficialmente en banco {bench}m con Score Compuesto **{winner_row['composite_score']:.4f}**.",
                                f"📊 **Predicciones enviadas al backend:** {pred_result.get('records_updated', 0)} registros.",
                                f"✅ **Coherencia estadistica:** media predicha {pred_mean:.4f}% Cu vs media real {y_mean:.4f}% Cu.",
                                f"📐 **Rango de predicciones:** {preds_arr.min():.4f} - {preds_arr.max():.4f}% Cu.",
                                f"🔍 **Verificacion (primeras 10):** error medio absoluto {float(np.mean(np.abs(y_full[:10] - preds_arr[:10]))):.4f} %Cu."
                            ]
                            activation_static = "\n\n".join(act_static_lines)
                            
                            activation_data = {
                                'model_name': winner_row['model_name'],
                                'composite_score': float(winner_row['composite_score']),
                                'rmse': float(winner_row['rmse']),
                                'r2': float(winner_row['r2']),
                                'mae': float(winner_row['mae']),
                                'mape': float(winner_row['mape']),
                                'bias': float(winner_row['bias']),
                                'registered_records': pred_result.get('records_updated', 0),
                                'real_mean': float(y_full.mean()),
                                'pred_mean': pred_mean,
                                'real_std': float(y_full.std()),
                                'pred_std': float(preds_arr.std()),
                                'real_range': [float(y_full.min()), float(y_full.max())],
                                'pred_range': [float(preds_arr.min()), float(preds_arr.max())]
                            }
                            render_dual_interpretation('winner_diagnostic', activation_data, bench, 'activation', activation_static)
                    else:
                        st.warning(f"⚠️ Modelo activado pero predicciones no enviadas: {pred_result.get('message', '')}")
                else:
                    st.error(f"❌ Modelo ganador ('{winner_row['model_name']}') no encontrado en memoria. "
                             f"Keys disponibles: {list(st.session_state[models_key].keys())}")
                    st.info("ℹ️ Entrena en Fase 4 y activa INMEDIATAMENTE sin cerrar la pestaña.")
            else:
                missing = []
                if not has_models:
                    missing.append(f"'{models_key}'")
                if not has_X_full:
                    missing.append(f"'{X_full_key}'")
                st.error(f"❌ Faltan datos en memoria: {', '.join(missing)}")
                st.info("ℹ️ Modelo activado solo con metadata. Los datos de entrenamiento no están en memoria. "
                         "**Debes entrenar en Fase 4 y activar en la MISMA sesión de Streamlit sin cerrar la pestaña.**")
            
            st.info("El frontend React detectara automaticamente el cambio en los proximos 10 segundos.")
        except Exception as e:
            st.error(f"Error activando modelo: {e}")
    
    # Modelo activo actual
    st.markdown("---")
    st.subheader("Modelo Activo Actual")
    
    active_key = f"active_{bench}"
    if active_key in st.session_state:
        active = st.session_state[active_key]
        st.info(f"Banco {bench}m: **{active['model_name']}** (Score: {active['composite_score']:.4f})")
    else:
        try:
            active = get_active_model(bench)
            if active:
                st.info(f"Banco {bench}m: **{active['model_name']}** (Score: {active['composite_score']:.4f})")
            else:
                st.warning(f"No hay modelo activo para el banco {bench}m")
        except Exception as e:
            st.warning(f"No se pudo obtener modelo activo: {e}")


def render_batch_training():
    """Modo Lote: Fases 4-5-6 en secuencia para multiples bancos de una sola vez."""
    st.header("⚡ Lote Multi-Banco — Entrenar y Activar")

    st.markdown("""
    **¿Qué hace este modo?**
    Ejecuta de forma **automática y secuencial** las Fases 4 → 5 → 6 para cada banco seleccionado:
    1. 🤖 **Entrena** los modelos con los datos del banco.
    2. 📈 **Evalúa** y determina el modelo ganador por *composite score*.
    3. 🏆 **Activa** el ganador en la base de datos (modelo oficial del banco).
    4. 🗂️ **Exporta** el `.joblib` para la inferencia en vivo (servicio 8502).
    5. 📊 **Envía** las predicciones al backend para la Reconciliación Mine-to-Mill.

    Al finalizar tendrás todos los bancos con su modelo activo y listos para predicción en vivo,
    sin necesidad de pasar banco por banco por las fases manuales.
    """)

    # ─── Controles ───
    # Si hay dataset cargado, Mine-to-Mill se desactiva automáticamente
    if st.session_state.dataset is not None:
        use_real_data = False
        st.info(f"📦 Dataset cargado detectado: el lote entrenará con tus datos ({len(st.session_state.dataset):,} muestras). 'Usar datos reales de planta' desactivado.")
    else:
        use_real_data = st.checkbox(
            "📊 Usar datos reales de planta (Mine-to-Mill)",
            value=True,
            help="Entrena con los datos reales de alimentación a planta en lugar de sintéticos",
        )

    default_benches = [b for b in BENCHES if b in (3170, 3140, 3155)]
    b_row1, b_row2 = st.columns([3, 1], vertical_alignment="bottom")
    with b_row2:
        pressed_all = st.button("✅ Todos los bancos", use_container_width=True, type="secondary")
    with b_row1:
        if pressed_all:
            st.session_state["batch_benches"] = BENCHES
        selected_benches = st.multiselect(
            "Bancos a procesar:",
            BENCHES,
            key="batch_benches",
            default=default_benches or [BENCHES[0]],
            help="Puedes seleccionar varios bancos a la vez",
        )

    selected_models = st.multiselect(
        "Modelos a entrenar por banco:",
        list(MODELS.keys()),
        default=list(MODELS.keys()),
        format_func=lambda k: MODELS[k]['name'],
    )

    if not selected_benches:
        st.warning("⚠️ Selecciona al menos un banco para procesar.")
        st.stop()
    if not selected_models:
        st.warning("⚠️ Selecciona al menos un modelo para entrenar.")
        st.stop()

    st.caption(f"Se procesarán **{len(selected_benches)} banco(s)** × **{len(selected_models)} modelo(s)**.")

    if st.button("🚀 Iniciar Lote Multi-Banco", type="primary", use_container_width=True):
        source = st.session_state.get('dataset_source', '') or ''
        quality = st.session_state.get('dataset_quality')
        data = st.session_state.get('dataset')
        if data is not None and 'hole_id' in data.columns and 'cu_base' not in data.columns:
            st.error("Los sondajes GeoMet no tienen bancos operativos. Usa Fase 4 para el experimento espacial.")
            return
        if source.startswith('Archivo:') and (quality is None or not quality.get('usable_for_training', False)):
            st.error("El CSV cargado no pasó el control de calidad para entrenamiento. Revisa los fallos en Carga de Datos.")
            return
        summary = []
        overall_progress = st.progress(0)
        overall_status = st.empty()

        for idx, bench in enumerate(selected_benches):
            overall_status.info(f"▶️ Procesando banco **{bench}m** ({idx + 1}/{len(selected_benches)})...")
            st.markdown(f"### 🏔️ Banco {bench}m")

            try:
                pipeline = TrainingPipeline(bench=bench)

                # 1) Cargar datos (misma logica que Fase 4)
                if st.session_state.dataset is not None and not use_real_data:
                    df = st.session_state.dataset.copy()
                    bench_col = 'bench' if 'bench' in df.columns else ('z' if 'z' in df.columns else None)
                    if bench_col is not None:
                        df_bench = df[df[bench_col] == bench]
                        if len(df_bench) > 50:
                            df = df_bench
                    st.write(f"📦 Usando dataset cargado: {len(df)} muestras (para banco {bench}m)")
                else:
                    df = pipeline.load_data(bench, use_real_data=use_real_data)
                    st.write(f"📦 Datos {'reales de planta' if use_real_data else 'sintéticos'}: {len(df)} muestras")

                # 2) Preprocesar y dividir
                X, y, feature_names, df_clean = pipeline.preprocess(df)
                X_train, X_val, X_test, y_train, y_val, y_test = pipeline.split_data(X, y, df=df_clean)

                # 3) Entrenar
                models = pipeline.train_all_models(X_train, y_train, X_val, y_val, models_to_train=selected_models)

                # 4) Evaluar
                results = pipeline.evaluate_all_models(X_test, y_test, pipeline.get_test_frame(df_clean))

                pipeline.save_results()

                # 5) Persistir en session_state (para Fases 5 y 6 manuales post-lote)
                st.session_state[f"benchmark_{bench}"] = results
                st.session_state['last_trained_bench'] = bench
                if hasattr(pipeline, 'predictions'):
                    st.session_state[f"predictions_{bench}"] = pipeline.predictions
                if hasattr(pipeline, 'test_data'):
                    st.session_state[f"testdata_{bench}"] = pipeline.test_data
                if hasattr(pipeline, 'models'):
                    st.session_state[f"models_{bench}"] = pipeline.models
                st.session_state[f"X_full_{bench}"] = X
                st.session_state[f"y_full_{bench}"] = y
                st.session_state[f"features_{bench}"] = feature_names

                # 6) Determinar ganador
                winner_key = max(results, key=lambda k: results[k]['composite_score'])
                winner = results[winner_key]
                winner_name = MODELS[winner_key]['name']

                # 7) Activar en base de datos
                activate_model(
                    bench=bench,
                    model_name=winner_name,
                    composite_score=winner['composite_score'],
                    rmse=winner['rmse'],
                    r2=winner['r2'],
                    mae=winner['mae'],
                    mape=winner['mape'],
                    bias=winner['bias'],
                )
                st.session_state[f"active_{bench}"] = {
                    'bench': bench,
                    'model_name': winner_name,
                    **{k: winner[k] for k in ('composite_score', 'rmse', 'r2', 'mae', 'mape', 'bias')},
                }

                # 8) Exportar modelo para inferencia en vivo
                exported = False
                try:
                    from model_registry import export_winner
                    export_winner(models[winner_key], winner_name, bench, {
                        'rmse': float(winner['rmse']),
                        'r2': float(winner['r2']),
                        'mae': float(winner['mae']),
                        'mape': float(winner['mape']),
                        'bias': float(winner['bias']),
                        'composite_score': float(winner['composite_score']),
                    })
                    exported = True
                except Exception as exp_err:
                    st.warning(f"⚠️ Export a inferencia en vivo falló: {exp_err}")

                # 9) Predicciones completas y envio al backend
                winner_model = models[winner_key]
                if hasattr(winner_model, 'predict_with_uncertainty'):
                    predictions, _, _, _ = winner_model.predict_with_uncertainty(X)
                else:
                    predictions = winner_model.predict(X)

                pred_result = send_predictions_to_api(
                    bench=bench,
                    model_name=winner_name,
                    predictions=np.array(predictions).tolist(),
                )
                records = pred_result.get('records_updated', 0) if pred_result.get('success') else 0

                summary.append({
                    'Banco': bench,
                    'Ganador': winner_name,
                    'RMSE': round(float(winner['rmse']), 4),
                    'R²': round(float(winner['r2']), 4),
                    'Registros': records,
                    'Exportado': 'Sí' if exported else 'No',
                })

                st.success(f"✅ Banco {bench}m: **{winner_name}** activado y exportado. "
                           f"{'📊 ' + str(records) + ' registros enviados al backend' if pred_result.get('success') else '⚠️ Predicciones no enviadas'}")

            except Exception as e:
                st.error(f"❌ Error en banco {bench}m: {e}")
                summary.append({
                    'Banco': bench,
                    'Ganador': f"ERROR: {e}",
                    'RMSE': None,
                    'R²': None,
                    'Registros': 0,
                    'Exportado': 'No',
                })

            overall_progress.progress((idx + 1) / len(selected_benches))

        overall_status.success(f"✅ Lote multi-banco finalizado: {len(summary)} banco(s) procesados.")
        st.markdown("### 📋 Resumen del Lote")
        st.dataframe(pd.DataFrame(summary), use_container_width=True)


def main():
    """Funcion principal"""
    render_header()
    
    phase, selected_bench = render_sidebar()
    
    # Renderizar fase seleccionada
    if "Inicio" in phase:
        render_home()
    elif "Carga de Datos" in phase:
        render_data_upload()
    elif "Fase 1" in phase:
        render_phase1_understanding()
    elif "Fase 2" in phase:
        render_phase2_exploration(selected_bench)
    elif "Fase 3" in phase:
        render_phase3_preparation(selected_bench)
    elif "Fase 4" in phase:
        render_phase4_modeling(selected_bench)
    elif "Fase 5" in phase:
        render_phase5_evaluation(selected_bench)
    elif "Fase 6" in phase:
        render_phase6_deployment(selected_bench)
    elif "Lote" in phase:
        render_batch_training()


if __name__ == "__main__":
    main()
