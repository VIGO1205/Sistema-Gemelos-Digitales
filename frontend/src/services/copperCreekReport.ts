import { jsPDF } from 'jspdf';
import * as XLSX from 'xlsx';
import type { CopperCreekScene } from '../components/viewer3d/CopperCreekViewer';
import type { CopperCreekModelMetadata } from '../hooks/useCopperCreekStudy';

export interface StudyReport {
  scene: CopperCreekScene;
  model: CopperCreekModelMetadata;
  title: string;
  author: string;
  generatedAt: string;
  benches: Array<{ bench: number; blocks: number; meanCu: number; meanIdw3: number; meanSpread: number; meanDistance: number }>;
}

const average = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
const fixed = (value: number, digits = 4) => value.toFixed(digits);
const fileStem = () => `Copper_Creek_Mammoth_${new Date().toISOString().slice(0, 10)}`;

export function buildStudyReport(scene: CopperCreekScene, model: CopperCreekModelMetadata, title: string, author: string): StudyReport {
  if (!scene.blocks.length || scene.metadata.model_name !== model.model_name || scene.metadata.model_exported_at !== model.exported_at) {
    throw new Error('La escena y el modelo publicado no coinciden o no contienen cubos.');
  }
  const levels = [...new Set(scene.blocks.map(block => block.bench))].sort((a, b) => b - a);
  return {
    scene, model, title: title.trim() || 'Informe académico de Copper Creek · Mammoth', author,
    generatedAt: new Date().toLocaleString('es-PE'),
    benches: levels.map(bench => {
      const blocks = scene.blocks.filter(block => block.bench === bench);
      return {
        bench, blocks: blocks.length,
        meanCu: average(blocks.map(block => block.cu_bayesian)),
        meanIdw3: average(blocks.map(block => block.cu_idw3 ?? 0)),
        meanSpread: average(blocks.map(block => block.epistemic_unc)),
        meanDistance: average(blocks.map(block => block.nearest_drillhole_m)),
      };
    }),
  };
}

export function buildStudyPdf(report: StudyReport): jsPDF {
  const pdf = new jsPDF({ unit: 'mm', format: 'a4' });
  const { scene, model } = report;
  let y = 20;
  const pageBottom = 275;
  const newPage = () => { pdf.addPage(); y = 20; };
  const paragraph = (label: string, value: string, gap = 5) => {
    pdf.setFont('helvetica', 'bold'); pdf.setFontSize(10);
    const heading = pdf.splitTextToSize(label, 170) as string[];
    if (y + heading.length * 5 + 10 > pageBottom) newPage();
    pdf.text(heading, 20, y); y += heading.length * 5 + 1;
    pdf.setFont('helvetica', 'normal'); pdf.setFontSize(9);
    const lines = pdf.splitTextToSize(value, 170) as string[];
    if (y + lines.length * 4.5 > pageBottom) newPage();
    pdf.text(lines, 20, y); y += lines.length * 4.5 + gap;
  };
  const heading = (value: string) => {
    if (y + 12 > pageBottom) newPage();
    pdf.setFont('helvetica', 'bold'); pdf.setFontSize(13); pdf.setTextColor(25, 55, 75);
    pdf.text(value, 20, y); pdf.setTextColor(0, 0, 0); y += 9;
  };

  pdf.setFillColor(15, 23, 42); pdf.rect(0, 0, 210, 14, 'F');
  pdf.setTextColor(255, 255, 255); pdf.setFontSize(9); pdf.text('M-6 | COPPER CREEK - MAMMOTH', 20, 9);
  pdf.setTextColor(0, 0, 0); pdf.setFont('helvetica', 'bold'); pdf.setFontSize(18);
  const titleLines = pdf.splitTextToSize(report.title, 170) as string[];
  pdf.text(titleLines, 20, 30); y = 30 + titleLines.length * 8;
  paragraph('Identificación', `Generado: ${report.generatedAt} | Autor: ${report.author} | Modelo publicado: ${model.model_name} | Versión: ${model.exported_at}`);
  heading('1. Alcance y procedencia');
  paragraph('Fuente', `${scene.metadata.source}. La escena corresponde a una reconstrucción académica aproximada del sector Mammoth.`);
  paragraph('Sistema de coordenadas', scene.metadata.crs);
  paragraph('Cobertura', `${scene.metadata.study_holes} sondajes del estudio, ${scene.drillholes.length} sondajes visibles, ${scene.metadata.used_composites} compositos de entrenamiento, ${scene.blocks.length} cubos estimados y ${report.benches.length} bancos reconstruidos.`);
  paragraph('Geometría', 'Cubos de 20 × 20 × 12 m. Los contornos y bancos son aproximados; no se dispone de sólidos oficiales de diseño minero.');
  heading('2. Modelo y validación');
  paragraph('Objetivo', 'Estimar %Cu en centros de cubos a partir de X, Y, Z y ensayos de sondajes. Las leyes de cubos son predicciones, no ensayos directos.');
  paragraph('Validación', `${model.validation}. Regla de soporte: hasta ${model.support_rule.max_holes} sondajes independientes, mínimo ${model.support_rule.min_holes}, distancia máxima ${model.support_rule.max_distance_m} m.`);
  for (const [name, metrics] of Object.entries(model.comparison)) {
    paragraph(name, `RMSE ${fixed(metrics.mean_rmse)} %Cu | MAE ${fixed(metrics.mean_mae)} %Cu | R² ${fixed(metrics.mean_r2)}.`, 3);
  }
  paragraph('Cobertura excluida', `${scene.metadata.skipped_unsupported_blocks} posiciones de cubo omitidas por soporte insuficiente. No se les asigna una ley en esta escena.`);
  paragraph('Control de datos', `${scene.metadata.invalid_cu_rows} filas de Cu descartadas durante la preparación del estudio.`);

  newPage(); heading('3. Resumen de cubos por banco');
  paragraph('Lectura', 'Los promedios son descriptivos de los cubos reconstruidos y admitidos por soporte. No son leyes de producción ni un inventario de recursos.');
  pdf.setFont('helvetica', 'bold'); pdf.setFontSize(8);
  pdf.text('Banco', 20, y); pdf.text('Cubos', 44, y); pdf.text('Cu modelo', 67, y); pdf.text('Cu IDW3', 101, y); pdf.text('Dispersión', 132, y); pdf.text('Dist. media', 166, y);
  y += 4; pdf.line(20, y, 190, y); y += 5; pdf.setFont('helvetica', 'normal');
  for (const row of report.benches) {
    if (y > pageBottom) newPage();
    pdf.text(`${row.bench} m`, 20, y); pdf.text(String(row.blocks), 44, y);
    pdf.text(`${fixed(row.meanCu)} %`, 67, y); pdf.text(`${fixed(row.meanIdw3)} %`, 101, y);
    pdf.text(`${fixed(row.meanSpread)} %`, 132, y); pdf.text(`${fixed(row.meanDistance, 1)} m`, 166, y); y += 7;
  }
  y += 8; heading('4. Límites de interpretación');
  paragraph('Incertidumbre', 'La dispersión entre sondajes vecinos es una medida descriptiva de variación local. No equivale a un intervalo probabilístico calibrado ni a P10/P50/P90.');
  paragraph('Datos ausentes', 'No se incorporan espectros SWIR, reconciliación real con planta, topografía oficial de banco ni clasificación de recursos o reservas.');
  paragraph('Uso', 'Material académico exploratorio. No valida decisiones de despacho, tonelaje, valor económico ni cumplimiento NI 43-101/JORC.');
  const pages = pdf.getNumberOfPages();
  for (let page = 1; page <= pages; page++) {
    pdf.setPage(page); pdf.setFontSize(8); pdf.setTextColor(100, 116, 139);
    pdf.text(`Copper Creek · reconstrucción académica | ${page}/${pages}`, 20, 287);
  }
  return pdf;
}

export function exportStudyExcel(report: StudyReport): void {
  const { scene, model } = report;
  const workbook = XLSX.utils.book_new();
  const add = (name: string, rows: Record<string, string | number>[]) => XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(rows), name);
  add('Alcance', [
    { Campo: 'Proyecto', Valor: scene.metadata.project },
    { Campo: 'Estado', Valor: scene.metadata.status },
    { Campo: 'Fuente', Valor: scene.metadata.source },
    { Campo: 'CRS', Valor: scene.metadata.crs },
    { Campo: 'Modelo publicado', Valor: model.model_name },
    { Campo: 'Versión del modelo', Valor: model.exported_at },
    { Campo: 'Validación', Valor: model.validation },
    { Campo: 'Sondajes del estudio', Valor: scene.metadata.study_holes },
    { Campo: 'Sondajes visibles', Valor: scene.drillholes.length },
    { Campo: 'Compositos usados', Valor: scene.metadata.used_composites },
    { Campo: 'Cubos estimados', Valor: scene.blocks.length },
    { Campo: 'Cubos omitidos por soporte', Valor: scene.metadata.skipped_unsupported_blocks },
    { Campo: 'Filas Cu inválidas descartadas', Valor: scene.metadata.invalid_cu_rows },
    { Campo: 'Límite', Valor: 'Sin clasificación de recursos, despacho ni reconciliación real con planta' },
  ]);
  add('Validacion', Object.entries(model.comparison).map(([name, metric]) => ({ Modelo: name, 'RMSE (%Cu)': metric.mean_rmse, 'MAE (%Cu)': metric.mean_mae, R2: metric.mean_r2 })));
  add('Bancos', report.benches.map(row => ({ 'Banco (m)': row.bench, Cubos: row.blocks, 'Cu modelo promedio (%Cu)': row.meanCu, 'Cu IDW3 promedio (%Cu)': row.meanIdw3, 'Dispersión local promedio (%Cu)': row.meanSpread, 'Distancia sondaje promedio (m)': row.meanDistance })));
  add('Cubos', scene.blocks.map(block => ({ ID: block.id, 'X UTM (m)': block.x, 'Y UTM (m)': block.y, 'Z (m)': block.z, 'Banco (m)': block.bench, 'Cu modelo publicado (%Cu)': block.cu_bayesian, 'Cu IDW3 referencia (%Cu)': block.cu_idw3 ?? 0, 'Dispersión local (%Cu)': block.epistemic_unc, 'Sondajes soporte': block.support_holes ?? 0, 'Sondaje más cercano (m)': block.nearest_drillhole_m, 'Dim X (m)': block.dx, 'Dim Y (m)': block.dy, 'Dim Z (m)': block.dz })));
  add('Sondajes_visibles', scene.drillholes.map(hole => ({ ID: hole.hole_id, 'X UTM (m)': hole.x, 'Y UTM (m)': hole.y, 'Z collar (m)': hole.z, 'Profundidad (m)': hole.total_depth_m, Azimut: hole.azimuth, Dip: hole.dip })));
  XLSX.writeFile(workbook, `${fileStem()}.xlsx`);
}

export async function buildStudyWord(report: StudyReport): Promise<Blob> {
  const { Document, Packer, Paragraph, HeadingLevel, Table, TableRow, TableCell, TextRun, WidthType } = await import('docx');
  const line = (text: string) => new Paragraph({ text, spacing: { after: 120 } });
  const section = (text: string) => new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 100 } });
  const cell = (text: string) => new TableCell({ children: [new Paragraph(text)] });
  const table = new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: [
    new TableRow({ children: ['Banco', 'Cubos', 'Cu modelo %', 'Cu IDW3 %', 'Dist. media m'].map(cell) }),
    ...report.benches.map(row => new TableRow({ children: [String(row.bench), String(row.blocks), fixed(row.meanCu), fixed(row.meanIdw3), fixed(row.meanDistance, 1)].map(cell) })),
  ] });
  const comparisons = Object.entries(report.model.comparison).map(([name, metric]) =>
    line(`${name}: RMSE ${fixed(metric.mean_rmse)} %Cu; MAE ${fixed(metric.mean_mae)} %Cu; R² ${fixed(metric.mean_r2)}.`));
  const doc = new Document({ sections: [{ properties: {}, children: [
    new Paragraph({ children: [new TextRun({ text: report.title, bold: true, size: 32 })], spacing: { after: 180 } }),
    line(`Proyecto: Copper Creek · sector Mammoth | Fecha: ${report.generatedAt} | Autor: ${report.author}`),
    line('Reconstrucción académica aproximada. Sin clasificación de recursos ni certificación.'),
    section('1. Datos y alcance'),
    line(`Fuente: ${report.scene.metadata.source}. CRS: ${report.scene.metadata.crs}.`),
    line(`${report.scene.metadata.study_holes} sondajes del estudio; ${report.scene.drillholes.length} visibles; ${report.scene.metadata.used_composites} compositos; ${report.scene.blocks.length} cubos estimados en ${report.benches.length} bancos.`),
    line('Cubos de 20 × 20 × 12 m. Contornos y elevaciones de banco aproximados para la demostración.'),
    section('2. Modelo publicado y validación'),
    line(`Modelo: ${report.model.model_name}. Versión: ${report.model.exported_at}.`),
    line(`Objetivo: %Cu estimado en centros de cubos con X/Y/Z. Validación: ${report.model.validation}.`),
    ...comparisons,
    line(`Regla de soporte: mínimo ${report.model.support_rule.min_holes} y máximo ${report.model.support_rule.max_holes} sondajes independientes dentro de ${report.model.support_rule.max_distance_m} m. ${report.scene.metadata.skipped_unsupported_blocks} posiciones omitidas por soporte insuficiente.`),
    line(`Control de datos: ${report.scene.metadata.invalid_cu_rows} filas de Cu descartadas durante la preparación.`),
    section('3. Resumen por banco'),
    line('Promedios descriptivos de cubos reconstruidos con soporte. No son leyes de producción ni inventario de recursos.'),
    table,
    section('4. Límites'),
    line('La dispersión local entre sondajes no es un intervalo probabilístico calibrado. No se reportan P10/P50/P90.'),
    line('No hay espectros SWIR, diseño minero oficial, datos reales de planta ni clasificación de recursos o reservas.'),
    line('Este documento es exploratorio y académico; no autoriza despacho, estimación de tonelaje ni decisiones económicas.'),
  ] }] });
  return Packer.toBlob(doc);
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const studyFilename = (extension: 'pdf' | 'docx') => `${fileStem()}.${extension}`;
