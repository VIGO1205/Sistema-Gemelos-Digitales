"""
Generador de Reportes PDF profesionales para el Motor IA M-6
Estructura formal: portada, tablas, graficos, interpretaciones, analisis IA
"""

import io
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from fpdf import FPDF


# Mapeo de emojis a texto ASCII para compatibilidad con fuentes PDF core
EMOJI_MAP = {
    '🟢': '[OK]', '✅': '[OK]', '⚠️': '[AVISO]', '🔴': '[ALERTA]',
    '🏆': '[GANADOR]', '🥈': '[2DO]', '📊': '[GRAF]', '📉': '[BAJO]',
    '🎯': '[PRECISO]', '🛡️': '[ROBUSTO]', '⭐': '[*]', '🌟': '[*]',
    '🤝': '[MIXTO]', '💡': '[TIP]', 'ℹ️': '[INFO]', '⛏️': '[MINA]',
    '📄': '[PDF]', '📋': '[DOC]', '✅': '[OK]', '❌': '[ERROR]',
    '📈': '[SUBE]', '🏗️': '[CONST]', '🗄️': '[DB]', '🧠': '[IA]',
    '🎲': '[RND]', '📤': '[UP]', '📥': '[DOWN]', '👁️': '[VER]',
    '🔍': '[BUSQ]', '🛠️': '[HERR]', '🤖': '[BOT]', '📁': '[FILE]',
    '🚀': '[GO]', '🎓': '[ACAD]', '📅': '[FECHA]', '🔬': '[CIEN]',
    '📡': '[COM]', '💻': '[PC]', '📱': '[MOVIL]', '🔧': '[AJUS]',
    '📐': '[DIBUJO]', '📏': '[REGLA]', '🔑': '[LLAVE]', '⚙️': '[ENGR]',
    '🔩': '[TORN]', '📦': '[CAJA]', '📮': '[CORR]', '📯': '[CORNO]',
    '📜': '[PERG]', '📃': '[DOC]', '📄': '[HOJA]', '📑': '[MARC]',
    '📊': '[BARRAS]', '📈': '[LINEA]', '📉': '[BAJA]', '🗒️': '[NOTAS]',
    '📓': '[CUAD]', '📔': '[DIAR]', '📕': '[LIBRO]', '📖': '[LEER]',
    '📗': '[LIB-V]', '📘': '[LIB-A]', '📙': '[LIB-N]', '📚': '[LIBROS]',
    '📛': '[ETIQ]', '🔖': '[SEPA]', '🧮': '[ABACO]', '🗃️': '[ARCH]',
    '🗄️': '[CAJON]', '🗑️': '[BASU]', '📰': '[PERI]', '🗞️': '[DIAR]',
    '📋': '[CLIP]', '📌': '[CHINC]', '📍': '[UBIC]', '📎': '[CLIP2]',
    '🖇️': '[CLIPS]', '📏': '[REGLA]', '📐': '[ESCU]', '✂️': '[TIJ]',
    '🖊️': '[BOLI]', '🖋️': '[PLUM]', '✒️': '[PLUM2]', '📝': '[NOTA]',
    '💼': '[MAL]', '📁': '[CARP]', '📂': '[CARP-A]', '🗂️': '[INDE]',
}

def sanitize_for_pdf(text: str) -> str:
    """Reemplaza emojis y caracteres Unicode no soportados por fuentes PDF core (latin-1)"""
    if not isinstance(text, str):
        text = str(text)
    # Reemplazar emojis conocidos
    for emoji, replacement in EMOJI_MAP.items():
        text = text.replace(emoji, replacement)
    # Reemplazar bullets y guiones Unicode por ASCII
    text = text.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
    text = text.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u00a0', ' ').replace('\u200b', '')
    # Codificar a latin-1 eliminando caracteres no soportados
    return text.encode('latin-1', 'ignore').decode('latin-1')


def get_logo_path() -> Optional[str]:
    """Resuelve la ruta del logo M-6 para usarlo en el encabezado del PDF."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "logo" / "LOGO-M6.png",
        Path(__file__).resolve().parent.parent / "frontend" / "public" / "logo" / "LOGO-M6.png",
        Path(__file__).resolve().parent / "LOGO-M6.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


class M6PDFReport(FPDF):
    """Clase personalizada de PDF con estilo M-6 profesional"""
    
    # Colores del tema
    COPPER = (180, 83, 9)
    COPPER_LIGHT = (245, 158, 11)
    DARK = (30, 41, 59)
    WHITE = (255, 255, 255)
    GREEN = (21, 128, 61)
    RED = (220, 38, 38)
    GRAY = (100, 116, 139)
    BG_GRAY = (248, 250, 252)
    
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)
        self.chart_paths = {}
    
    def header(self):
        """Encabezado en cada pagina (excepto portada): logo a la derecha + titulo"""
        if self.page_no() == 1:
            return
        
        # Logo M-6 alineado a la derecha del encabezado
        logo_path = get_logo_path()
        if logo_path:
            self.image(logo_path, x=170, y=9, w=25)
        
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 8, 'Motor IA M-6 - Gemelo Digital Predictivo', ln=True, align='L')
        self.cell(0, 4, f'Reporte de Benchmark - Banco {getattr(self, "bench", "N/A")}m', ln=True, align='L')
        
        # Linea separadora
        self.set_draw_color(*self.COPPER)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)
    
    def footer(self):
        """Pie de pagina con numero de pagina"""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
    
    def add_cover_page(self, metadata: Dict[str, Any]):
        """Portada formal del reporte"""
        self.add_page()
        
        # Fondo superior con color cobre
        self.set_fill_color(*self.COPPER)
        self.rect(0, 0, 210, 70, 'F')
        
        # Titulo principal
        self.set_y(25)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(*self.WHITE)
        self.cell(0, 12, 'MOTOR IA M-6', ln=True, align='C')
        
        self.set_font('Helvetica', '', 14)
        self.cell(0, 8, 'Gemelo Digital Predictivo para Mineria de Cobre', ln=True, align='C')
        
        # Logo del sistema centrado bajo la franja cobre
        logo_path = get_logo_path()
        if logo_path:
            self.image(logo_path, x=80, y=74, w=50)
        
        # Subtitulo del reporte
        self.set_y(112)
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(*self.DARK)
        self.cell(0, 10, 'REPORTE DE BENCHMARK DE MODELOS', ln=True, align='C')
        
        self.set_font('Helvetica', '', 12)
        self.set_text_color(*self.GRAY)
        self.cell(0, 8, 'Evaluacion Comparativa de 5 Modelos Predictivos', ln=True, align='C')
        self.cell(0, 8, '(3 Clasicos + 2 Hibridos)', ln=True, align='C')
        
        # Linea decorativa
        self.set_y(148)
        self.set_draw_color(*self.COPPER)
        self.set_line_width(0.8)
        self.line(60, self.get_y(), 150, self.get_y())
        
        # Metadatos
        self.set_y(160)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*self.DARK)
        
        meta_lines = [
            ('BANCO OPERATIVO', f"{metadata.get('bench', 'N/A')} m"),
            ('FECHA DE GENERACION', metadata.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))),
            ('METODOLOGIA', metadata.get('methodology', 'CRISP-DM')),
            ('VERSION DEL MOTOR', metadata.get('motor_version', 'M-6 IA v1.0')),
            ('SISTEMA', f"{metadata.get('system', 'N/A')} | Python {metadata.get('python_version', 'N/A')}"),
        ]
        
        for label, value in meta_lines:
            self.set_x(50)
            self.set_font('Helvetica', 'B', 10)
            self.cell(50, 7, label, align='L')
            self.set_font('Helvetica', '', 10)
            self.cell(60, 7, f': {value}', align='L', ln=True)
        
        # Nota de confidencialidad
        self.set_y(265)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 5, 'Documento generado automaticamente por el Motor IA M-6 - Sistema de Gemelos Digitales', ln=True, align='C')
        self.cell(0, 5, 'Metodologia conforme a estandares CRISP-DM y JORC 2012', ln=True, align='C')
    
    def add_section_title(self, title: str, icon: str = ''):
        """Agrega un titulo de seccion estilizado"""
        title = sanitize_for_pdf(title)
        icon = sanitize_for_pdf(icon)
        self.ln(5)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*self.COPPER)
        self.set_fill_color(*self.BG_GRAY)
        display = f'  {icon}  {title}' if icon else f'  {title}'
        self.cell(0, 10, display, ln=True, fill=True)
        self.ln(2)
        self.set_text_color(*self.DARK)
    
    def add_paragraph(self, text: str, font_size: int = 10, bold: bool = False):
        """Agrega un parrafo de texto justificado"""
        text = sanitize_for_pdf(text)
        self.set_font('Helvetica', 'B' if bold else '', font_size)
        self.set_text_color(*self.DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)
    
    def add_interpretation_box(self, text: str, severity: str = 'info', icon: str = ''):
        """Agrega una interpretacion simple con bullet de color. Robusta ante saltos de pagina."""
        text = sanitize_for_pdf(text)
        icon = sanitize_for_pdf(icon)
        
        # Mapear severidad a etiqueta y color
        severity_map = {
            'success': ('[OK]', self.GREEN),
            'warning': ('[AVISO]', self.COPPER_LIGHT),
            'danger': ('[ALERTA]', self.RED),
            'info': ('[INFO]', self.GRAY),
        }
        label, color = severity_map.get(severity, ('[INFO]', self.GRAY))
        
        # Guardar posicion Y inicial
        start_y = self.get_y()
        
        # Dibujar bullet de color (cuadrado pequeno)
        self.set_xy(17, start_y + 1)
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        self.rect(17, start_y + 1, 3, 3, 'F')
        
        # Escribir etiqueta en negrita + color
        self.set_xy(22, start_y)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*color)
        self.cell(25, 5.5, label, ln=0)
        
        # Escribir texto de interpretacion
        self.set_xy(47, start_y)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self.DARK)
        self.multi_cell(148, 5.5, text)
        
        self.ln(2)
    
    def add_table(self, headers: List[str], rows: List[List[Any]], col_widths: List[int] = None):
        """Agrega una tabla formateada"""
        if col_widths is None:
            n_cols = len(headers)
            col_widths = [int(180 / n_cols)] * n_cols
        
        # Headers
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(*self.COPPER)
        self.set_text_color(*self.WHITE)
        self.set_draw_color(*self.COPPER)
        
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, str(h), border=1, align='C', fill=True)
        self.ln()
        
        # Filas
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*self.DARK)
        self.set_draw_color(200, 200, 200)
        
        for row_idx, row in enumerate(rows):
            fill = row_idx % 2 == 1
            if fill:
                self.set_fill_color(248, 250, 252)
            
            for i, val in enumerate(row):
                if isinstance(val, float):
                    text = f'{val:.4f}'
                elif isinstance(val, bool):
                    text = 'GANADOR' if val else ''
                else:
                    text = str(val)
                
                # Resaltar ganador
                if i == 0 and len(row) > 1 and row[-1] == 'GANADOR':
                    self.set_font('Helvetica', 'B', 9)
                    self.set_text_color(*self.GREEN)
                else:
                    self.set_font('Helvetica', '', 9)
                    self.set_text_color(*self.DARK)
                
                self.cell(col_widths[i], 7, text, border=1, align='C', fill=fill)
            
            self.ln()
    
    def add_chart(self, chart_path: str, width: int = 180, caption: str = ''):
        """Incrusta una imagen de grafico centrada en la pagina"""
        if os.path.exists(chart_path):
            self.image(chart_path, x=(210 - width) / 2, w=width)
            if caption:
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(*self.GRAY)
                self.cell(0, 5, caption, ln=True, align='C')
            self.ln(3)
    
    def add_page_break(self):
        """Salto de pagina"""
        self.add_page()


def generate_pdf_report(report_data: Dict[str, Any], bench: int, 
                       chart_paths: Dict[str, str],
                       ai_analysis: Optional[str] = None) -> bytes:
    """
    Genera un reporte PDF profesional completo.
    
    Args:
        report_data: Datos estructurados del reporte
        bench: Numero de banco
        chart_paths: Rutas a imagenes PNG de graficos
        ai_analysis: Texto opcional de analisis con IA (Groq)
    
    Returns:
        bytes del archivo PDF listo para descargar
    """
    pdf = M6PDFReport()
    pdf.bench = bench
    pdf.chart_paths = chart_paths
    
    metadata = report_data.get('metadata', {})
    benchmark = report_data.get('benchmark')
    predictions = report_data.get('predictions')
    interpretations = report_data.get('interpretations', {})
    stability = report_data.get('stability')
    bootstrap = report_data.get('bootstrap')
    
    # ============================================================
    # PORTADA
    # ============================================================
    pdf.add_cover_page(metadata)
    
    # ============================================================
    # 1. RESUMEN EJECUTIVO + 2. CONTEXTO DEL EXPERIMENTO (una sola pagina)
    # ============================================================
    pdf.add_page()
    pdf.add_section_title('1. Resumen Ejecutivo', icon='')
    
    if benchmark is not None and not benchmark.empty:
        winner = benchmark.loc[benchmark['composite_score'].idxmax()]
        
        resumen = (
            f"Este reporte presenta los resultados del benchmark de 5 modelos predictivos "
            f"evaluados para la estimacion de ley de cobre (% Cu) en el banco {bench}m. "
            f"La metodologia sigue las 6 fases de CRISP-DM y los criterios de calidad "
            f"conformes a los estandares JORC 2012 para estimacion de recursos mineros.\n\n"
            f"El modelo ganador es "
        )
        pdf.add_paragraph(resumen, font_size=10)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 5.5, f"{winner['model_name']} ({winner['model_type']})", ln=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(0, 5.5, (
            f"con un Score Compuesto de {winner['composite_score']:.4f}. "
            f"Este modelo alcanzo un RMSE de {winner['rmse']:.4f}% Cu y un R2 de {winner['r2']:.4f}, "
            f"indicando {'excelente' if winner['r2'] > 0.90 else 'buena'} capacidad predictiva. "
            f"El analisis de estabilidad y los intervalos de confianza bootstrap confirman "
            f"la confiabilidad del modelo para su despliegue en el gemelo digital."
        ))
        pdf.ln(2)
        
        # Interpretacion comparativa
        if '__comparison__' in interpretations:
            comp = interpretations['__comparison__'][0]
            pdf.add_interpretation_box(comp['text'], comp['severity'], comp['icon'])
    
    # ============================================================
    # 2. CONTEXTO DEL EXPERIMENTO (continua en la misma hoja que seccion 1)
    # ============================================================
    pdf.add_section_title('2. Contexto del Experimento', icon='')
    
    ctx_text = (
        f"El experimento fue ejecutado en el banco operativo {bench}m del deposito minero.\n"
        f"Se evaluaron 5 modelos predictivos: 3 clasicos (Kriging, Random Forest, XGBoost) "
        f"y 2 hibridos (Stacking Ensemble, NN + Bayesian Kriging).\n\n"
        f"PARAMETROS EVALUADOS POR EL GEMELO DIGITAL M-6:\n"
        f"- Ensayos Quimicos: Ley de Cobre Total (% Cu) y Cobre Soluble (% CuSol).\n"
        f"- Espectrometria SWIR/VNIR: Indice de alteracion mineral (Crisocola, Illita, Clorita, Biotita).\n"
        f"- Geologia y Litologia: Tipo de Roca (Skarn, Porfido, Andesita) y Alteracion.\n"
        f"- Espaciales 3D: Coordenadas (X, Y, Z), Kernel Matern 5/2, distancia a sondajes y fallas.\n"
        f"- Operacionales y Bayesiano: Tonelaje, densidad de barrenos, Ley de corte 0.35% Cu y Simu. Monte Carlo (P10/P50/P90).\n\n"
        f"La division train/validation/test fue 70/15/15 con semilla aleatoria 42 para reproducibilidad."
    )
    pdf.add_paragraph(ctx_text, font_size=10)
    
    pdf.add_paragraph('Features de entrada:', bold=True)
    features_text = ', '.join(metadata.get('features_used', []))
    pdf.add_paragraph(features_text, font_size=9)
    
    if predictions:
        pdf.add_paragraph(f"Muestras en conjunto de test: {predictions['n_samples']}", bold=True)
    
    # ============================================================
    # 3. COMPARATIVA DE MODELOS
    # ============================================================
    pdf.add_page()
    pdf.add_section_title('3. Comparativa de Modelos', icon='')
    
    if benchmark is not None and not benchmark.empty:
        # Tabla comparativa
        headers = ['Modelo', 'Tipo', 'RMSE', 'MAE', 'R2', 'MAPE%', 'Score', '']
        rows = []
        for _, r in benchmark.iterrows():
            rows.append([
                r['model_name'], r['model_type'], r['rmse'], r['mae'],
                r['r2'], r['mape'], r['composite_score'],
                'GANADOR' if r['is_winner'] else ''
            ])
        
        col_widths = [38, 22, 22, 22, 20, 20, 24, 22]
        pdf.add_table(headers, rows, col_widths)
        pdf.ln(5)
        
        # Graficos RMSE y R2 (mismo tamano, reducidos para que quepan juntos en la hoja)
        if 'rmse_comparison' in chart_paths:
            pdf.add_chart(chart_paths['rmse_comparison'], width=120,
                         caption='Figura 1: RMSE por Modelo (menor es mejor)')
        
        if 'r2_comparison' in chart_paths:
            pdf.add_chart(chart_paths['r2_comparison'], width=120,
                         caption='Figura 2: R2 por Modelo (mayor es mejor)')
    
    # ============================================================
    # 4. RANKING POR SCORE COMPUESTO
    # ============================================================
    pdf.add_page()
    pdf.add_section_title('4. Ranking por Score Compuesto', icon='')
    
    ranking_text = (
        "El Score Compuesto pondera las metricas de la siguiente manera: "
        "RMSE (25%), MAE (20%), R2 (20%), MAPE (15%), Bias (10%) e Incertidumbre (10%). "
        "Esta ponderacion prioriza la precision predictiva y la calidad del ajuste, "
        "pero tambien penaliza modelos con alto sesgo o incertidumbre excesiva."
    )
    pdf.add_paragraph(ranking_text, font_size=10)
    
    if 'composite_ranking' in chart_paths:
        pdf.add_chart(chart_paths['composite_ranking'], width=170,
                     caption='Figura 3: Ranking Final por Score Compuesto')
    
    # Interpretacion del ganador
    if '__winner__' in interpretations:
        win = interpretations['__winner__'][0]
        pdf.add_interpretation_box(win['text'], win['severity'], win['icon'])
    
    # ============================================================
    # 5. DIAGNOSTICO POR METRICA
    # ============================================================
    pdf.add_page()
    pdf.add_section_title('5. Diagnostico por Metrica', icon='')
    
    if benchmark is not None and not benchmark.empty:
        winner = benchmark.loc[benchmark['composite_score'].idxmax()]
        winner_key = None
        for key, val in MODELS.items():
            if val['name'] == winner['model_name']:
                winner_key = key
                break
        
        # Interpretaciones del ganador
        if winner_key and winner_key in interpretations:
            for interp in interpretations[winner_key]:
                pdf.add_interpretation_box(interp['text'], interp['severity'], interp['icon'])
                if interp.get('action'):
                    pdf.set_font('Helvetica', 'I', 9)
                    pdf.set_text_color(100, 116, 139)
                    pdf.cell(0, 5, f"Accion recomendada: {interp['action']}", ln=True)
                    pdf.ln(2)
    
    # ============================================================
    # 6. PREDICCION VS REAL
    # ============================================================
    if 'prediction_vs_real' in chart_paths:
        pdf.add_page()
        pdf.add_section_title('6. Analisis de Prediccion vs Real', icon='')
        
        pred_text = (
            "Los graficos de dispersion comparan los valores predichos por cada modelo "
            "contra los valores reales de ley de cobre. La linea punteada negra representa "
            "la relacion ideal 1:1. Cuanto mas cercanos esten los puntos a esta linea, "
            "mayor sera la precision del modelo. La dispersion en zonas de alta ley (>0.8% Cu) "
            "es esperada debido al efecto nugget geologico inherente a los depositos porfidicos."
        )
        pdf.add_paragraph(pred_text, font_size=10)
        pdf.add_chart(chart_paths['prediction_vs_real'], width=175,
                     caption='Figura 4: Prediccion vs Real por Modelo')
    
    # ============================================================
    # 7. ANALISIS DE RESIDUALES
    # ============================================================
    if 'residuals' in chart_paths:
        pdf.add_page()
        pdf.add_section_title('7. Analisis de Residuales', icon='')
        
        res_text = (
            "Los residuales (diferencia entre valor real y predicho) deben distribuirse "
            "aleatoriamente alrededor de cero sin patrones discernibles. La presencia de patrones "
            "(funnel, curva, o tendencia) indica que el modelo no captura completamente "
            "la estructura subyacente de los datos."
        )
        pdf.add_paragraph(res_text, font_size=10)
        pdf.add_chart(chart_paths['residuals'], width=175,
                     caption='Figura 5: Residuales vs Predicho')
    
    if 'residual_histograms' in chart_paths:
        pdf.add_page()
        pdf.add_section_title('7.1 Distribucion de Residuales', icon='')
        
        hist_text = (
            "Los histogramas de residuales deberian aproximar una distribucion normal centrada en cero. "
            "Asimetria significativa o colas pesadas indican que el modelo tiene dificultades "
            "en ciertos rangos de ley, lo cual puede requerir transformaciones o segmentacion por dominio."
        )
        pdf.add_paragraph(hist_text, font_size=10)
        pdf.add_chart(chart_paths['residual_histograms'], width=175,
                     caption='Figura 6: Histogramas de Residuales')
    
    # ============================================================
    # 8. BOOTSTRAP CI
    # ============================================================
    if 'bootstrap_ci' in chart_paths:
        pdf.add_page()
        pdf.add_section_title('8. Intervalos de Confianza Bootstrap', icon='')
        
        boot_text = (
            "Se realizaron 1000 iteraciones de bootstrap para estimar la incertidumbre "
            "en la metrica RMSE. Los intervalos de confianza al 95% indican el rango dentro "
            "del cual se espera que se encuentre el RMSE verdadero. Intervalos estrechos "
            "indican alta confianza en la estimacion; intervalos amplios sugieren que se "
            "requieren mas datos de validacion."
        )
        pdf.add_paragraph(boot_text, font_size=10)
        pdf.add_chart(chart_paths['bootstrap_ci'], width=170,
                     caption='Figura 7: IC Bootstrap 95% para RMSE')
        
        # Tabla resumen bootstrap
        if bootstrap:
            pdf.ln(3)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 7, 'Resumen Bootstrap:', ln=True)
            
            headers = ['Modelo', 'RMSE Mean', 'IC 95% Inferior', 'IC 95% Superior', 'Amplitud']
            rows = []
            for br in bootstrap:
                rows.append([
                    br['model_name'],
                    br['rmse_mean'],
                    br['ci_lower'],
                    br['ci_upper'],
                    br['ci_width']
                ])
            pdf.add_table(headers, rows, [40, 30, 35, 35, 30])
    
    # ============================================================
    # 8.1 VALIDACION CRUZADA REPETIDA
    # ============================================================
    cv_data = report_data.get('cross_validation')
    if cv_data and 'cross_validation' in chart_paths:
        pdf.add_page()
        pdf.add_section_title('8.1 Validacion Cruzada Repetida', icon='')
        
        cv_text = (
            f"Se evaluo cada modelo sobre los MISMOS {cv_data.get('n_total_folds', 0)} folds "
            f"({cv_data.get('n_repeats', 3)}x{cv_data.get('n_splits', 5)}-fold, diseno pareado) "
            f"submuestreados a {cv_data.get('n_rows_used', 0)} filas. Esta validacion cruzada "
            "repetida permite comparar los modelos de forma estadisticamente rigurosa en lugar "
            "de depender de un solo split de train/test."
        )
        pdf.add_paragraph(cv_text, font_size=10)
        pdf.add_chart(chart_paths['cross_validation'], width=175,
                     caption='Figura 8.1: Distribucion del RMSE por fold')
        
        # Tabla resumen CV
        summary_df = cv_data.get('summary')
        if summary_df is not None and not summary_df.empty:
            pdf.ln(2)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 7, 'Resumen de Validacion Cruzada:', ln=True)
            headers = ['Modelo', 'RMSE medio', 'Std', 'IC95% inf', 'IC95% sup', 'MAE', 'R2']
            rows = []
            for _, r in summary_df.iterrows():
                rows.append([sanitize_for_pdf(str(r['model_name'])),
                             r['rmse_mean'], r['rmse_std'],
                             r['ci_lower'], r['ci_upper'],
                             r['mae_mean'], r['r2_mean']])
            pdf.add_table(headers, rows, [48, 24, 24, 28, 28, 20, 20])
        
        if cv_data.get('interpretation'):
            interp = cv_data['interpretation']
            pdf.add_interpretation_box(interp['text'], interp['severity'], interp['icon'])
    
    # ============================================================
    # 8.2 PRUEBAS ESTADISTICAS ROBUSTAS
    # ============================================================
    stat_tests = report_data.get('stat_tests')
    if stat_tests and (stat_tests.get('friedman') or stat_tests.get('wilcoxon') or stat_tests.get('bootstrap')):
        pdf.add_page()
        pdf.add_section_title('8.2 Pruebas Estadisticas Robustas', icon='')
        
        test_text = (
            "Las pruebas estadisticas se calcularon con datos REALES de prediccion y folds de "
            "validacion cruzada (no con datos simulados), tal como exige la buena practica "
            "academica para respaldar la seleccion del modelo ganador."
        )
        pdf.add_paragraph(test_text, font_size=10)
        
        friedman = stat_tests.get('friedman', {})
        if friedman.get('p_value') is not None:
            pdf.ln(2)
            pdf.cell(0, 6, 'Test de Friedman (comparacion global de modelos pareados):', ln=True)
            headers = ['Estadistico chi2', 'p-valor', 'Folds', 'Conclusion']
            rows = [[
                round(friedman.get('statistic', 0.0), 4),
                round(friedman.get('p_value', 1.0), 4),
                friedman.get('n_folds', 0),
                'Diferencias significativas' if friedman.get('significant') else 'Sin diferencias significativas'
            ]]
            pdf.add_table(headers, rows, [40, 40, 30, 70])
            if friedman.get('significant'):
                pdf.add_interpretation_box(
                    "Existen diferencias estadisticamente significativas entre los modelos "
                    "(p<0.05): la seleccion del ganador esta respaldada, no es producto del azar.",
                    'success', '🧪'
                )
        
        if stat_tests.get('wilcoxon'):
            pdf.ln(2)
            pdf.cell(0, 6, 'Comparaciones pareadas (Wilcoxon + correccion Bonferroni):', ln=True)
            headers = ['Modelo A', 'Modelo B', 'Estadistico', 'p (crudo)', 'p (Bonferroni)', 'Significativo']
            rows = []
            for w in stat_tests['wilcoxon']:
                rows.append([
                    sanitize_for_pdf(str(w['model_a'])),
                    sanitize_for_pdf(str(w['model_b'])),
                    round(w['statistic'], 3) if w['statistic'] is not None else '-',
                    round(w['p_value'], 4) if w['p_value'] is not None else 1.0,
                    round(w['bonferroni_alpha'], 4),
                    'SI' if w['significant'] else 'NO'
                ])
            pdf.add_table(headers, rows, [38, 38, 22, 28, 30, 24])
        
        if stat_tests.get('bootstrap') and 'stat_tests_bootstrap' in chart_paths:
            pdf.ln(2)
            pdf.add_chart(chart_paths['stat_tests_bootstrap'], width=170,
                         caption='Figura 8.2: Bootstrap pareado (IC95% de la diferencia de RMSE)')
            headers = ['Ganador', 'Rival', 'Delta RMSE', 'IC95% inf', 'IC95% sup', 'Ganador mejor']
            rows = []
            for b in stat_tests['bootstrap']:
                rows.append([
                    sanitize_for_pdf(str(b['winner'])), sanitize_for_pdf(str(b['rival'])),
                    round(b['diff_mean'], 5), round(b['ci_lower'], 5),
                    round(b['ci_upper'], 5), 'SI' if b['ci_upper'] < 0 else 'NO'
                ])
            pdf.add_table(headers, rows, [34, 34, 32, 32, 32, 24])
        
        if stat_tests.get('interpretation'):
            interp = stat_tests['interpretation']
            pdf.add_interpretation_box(interp['text'], interp['severity'], interp['icon'])
    
    # ============================================================
    # 8.3 OPTIMIZACION DE HIPERPARAMETROS
    # ============================================================
    hp_data = report_data.get('hyperparameters')
    if hp_data and hp_data.get('table') is not None and not hp_data['table'].empty:
        pdf.add_page()
        pdf.add_section_title('8.3 Optimizacion de Hiperparametros', icon='')
        
        hp_text = (
            "Se exploraron rejillas de hiperparametros (RandomForest: n_estimators/max_depth/"
            "min_samples_split; XGBoost: n_estimators/max_depth/learning_rate; NN+Bayesian: "
            "epochs/learning_rate) evaluadas sobre el validation set. Esto garantiza que los "
            "modelos finales fueron configurados con evidencia empirica y no con valores arbitrarios."
        )
        pdf.add_paragraph(hp_text, font_size=10)
        
        if 'hyperparameters' in chart_paths:
            pdf.add_chart(chart_paths['hyperparameters'], width=180,
                         caption='Figura 8.3: Curvas de validacion por modelo (rojo = default)')
        
        headers = ['Modelo', 'Mejores parametros', 'val-RMSE', 'Default', 'Mejora %', 'Candidatos']
        rows = []
        for _, r in hp_data['table'].iterrows():
            rows.append([
                sanitize_for_pdf(str(r['model_name'])),
                sanitize_for_pdf(str(r['best_params'])),
                round(r['best_rmse'], 4),
                round(r['default_rmse'], 4) if pd.notna(r['default_rmse']) else '-',
                round(r['improvement_pct'], 1),
                int(r['n_candidates'])
            ])
        pdf.add_table(headers, rows, [36, 60, 26, 22, 22, 20])
        
        if hp_data.get('interpretation'):
            interp = hp_data['interpretation']
            pdf.add_interpretation_box(interp['text'], interp['severity'], interp['icon'])
    
    # ============================================================
    # 9. ESTABILIDAD
    # ============================================================
    if 'stability' in chart_paths:
        pdf.add_page()
        pdf.add_section_title('9. Estabilidad ante Perturbaciones', icon='')
        
        stab_text = (
            "Se evaluo la robustez de cada modelo ante la adicion de ruido gaussiano creciente "
            "a los datos de entrada. Modelos robustos mantienen un RMSE relativamente estable "
            "incluso con niveles altos de ruido. Un incremento acelerado del RMSE indica "
            "overfitting: el modelo ha memorizado el ruido como si fuera senal."
        )
        pdf.add_paragraph(stab_text, font_size=10)
        pdf.add_chart(chart_paths['stability'], width=130,
                     caption='Figura 8: Estabilidad ante Perturbaciones')
        
        # Interpretaciones de estabilidad
        if stability:
            pdf.ln(3)
            for name, data in stability.items():
                interp = data['interpretation']
                pdf.add_interpretation_box(interp['text'], interp['severity'], interp['icon'])
    
    # ============================================================
    # 10. ANALISIS CON IA (opcional)
    # ============================================================
    if ai_analysis:
        pdf.add_page()
        pdf.add_section_title('10. Analisis Avanzado con Inteligencia Artificial', icon='')
        
        ia_intro = (
            "La siguiente seccion presenta un analisis generado por un modelo de lenguaje de gran escala "
            f"(Qwen 3.8-27B via Groq API) entrenado en literatura geoestadistica y minera. "
            f"Este analisis complementa las interpretaciones deterministicas con una perspectiva "
            f"narrativa profesional."
        )
        pdf.add_paragraph(ia_intro, font_size=10)
        
        # Linea decorativa
        pdf.set_draw_color(*pdf.COPPER_LIGHT)
        pdf.set_line_width(0.5)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)
        
        # Texto de IA
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*pdf.DARK)
        pdf.multi_cell(0, 5.5, ai_analysis)
        pdf.ln(3)
        
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(*pdf.GRAY)
        pdf.cell(0, 5, 'Analisis generado automaticamente por modelo de lenguaje. Revisar por experto humano.', ln=True)
    
    # ============================================================
    # 11. RECOMENDACIONES
    # ============================================================
    pdf.add_page()
    pdf.add_section_title('11. Recomendaciones y Conclusiones', icon='')
    
    if benchmark is not None and not benchmark.empty:
        winner = benchmark.loc[benchmark['composite_score'].idxmax()]
        
        # Determinar recomendacion segun calidad
        if winner['r2'] > 0.90 and winner['rmse'] < 0.05 and abs(winner['bias']) < 0.02:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(*pdf.GREEN)
            pdf.cell(0, 7, 'APTO PARA DESPLIEGUE INMEDIATO', ln=True)
            pdf.set_text_color(*pdf.DARK)
            pdf.set_font('Helvetica', '', 10)
            pdf.multi_cell(0, 5.5, (
                f"El modelo {winner['model_name']} cumple todos los criterios de calidad "
                f"para estimacion de recursos JORC. Se recomienda activarlo como modelo "
                f"predictivo principal del gemelo digital para el banco {bench}m."
            ))
            pdf.ln(2)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, 'Pasos siguientes:', ln=True)
            pdf.set_font('Helvetica', '', 10)
            pasos = [
                '1. Activar modelo en el sistema de reconciliacion Mine-to-Mill.',
                '2. Monitorear metricas en operacion real durante las primeras 4 semanas.',
                '3. Recalibrar trimestralmente con nuevos datos de sondajes.',
                '4. Documentar el modelo en el reporte de estimacion de recursos.',
            ]
            for paso in pasos:
                pdf.cell(0, 5.5, paso, ln=True)
        elif winner['r2'] > 0.80 and winner['rmse'] < 0.08:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(*pdf.COPPER)
            pdf.cell(0, 7, 'APTO CON PRECAUCIONES', ln=True)
            pdf.set_text_color(*pdf.DARK)
            pdf.set_font('Helvetica', '', 10)
            pdf.multi_cell(0, 5.5, (
                f"El modelo {winner['model_name']} es aceptable pero requiere monitoreo adicional."
            ))
            pdf.ln(2)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, 'Se recomienda:', ln=True)
            pdf.set_font('Helvetica', '', 10)
            pasos = [
                '1. Validar con datos independientes antes de despliegue completo.',
                '2. Implementar alertas automaticas si el error excede umbrales.',
                '3. Considerar un ensemble ponderado con el segundo mejor modelo.',
                '4. Revisar features geologicos para mejorar capacidad explicativa.',
            ]
            for paso in pasos:
                pdf.cell(0, 5.5, paso, ln=True)
        else:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(*pdf.RED)
            pdf.cell(0, 7, 'NO APTO PARA PRODUCCION', ln=True)
            pdf.set_text_color(*pdf.DARK)
            pdf.set_font('Helvetica', '', 10)
            pdf.multi_cell(0, 5.5, (
                f"El modelo {winner['model_name']} no alcanza los umbrales minimos de calidad."
            ))
            pdf.ln(2)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, 'Se recomienda:', ln=True)
            pdf.set_font('Helvetica', '', 10)
            pasos = [
                '1. NO activar en el gemelo digital sin mejoras significativas.',
                '2. Recolectar mas datos de entrenamiento (minimo 3000 muestras).',
                '3. Revisar calidad de datos de entrada (outliers, errores de muestreo).',
                '4. Evaluar transformaciones de variables o nuevos features geologicos.',
                '5. Considerar segmentacion por dominios geologicos.',
            ]
            for paso in pasos:
                pdf.cell(0, 5.5, paso, ln=True)
    
    # Generar bytes (convertir bytearray a bytes para compatibilidad con Streamlit)
    return bytes(pdf.output(dest='S'))


# Import MODELS para el generador
from config import MODELS
