import { toJpeg } from 'html-to-image';
import * as XLSX from 'xlsx';

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function pngChunk(type: string, data: Uint8Array): Uint8Array {
  const chunk = new Uint8Array(12 + data.length);
  const view = new DataView(chunk.buffer);
  view.setUint32(0, data.length);
  for (let i = 0; i < 4; i++) chunk[4 + i] = type.charCodeAt(i);
  chunk.set(data, 8);
  let crc = 0xffffffff;
  for (let i = 4; i < 8 + data.length; i++) {
    crc ^= chunk[i];
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  view.setUint32(8 + data.length, (crc ^ 0xffffffff) >>> 0);
  return chunk;
}

/** PNG pHYs metadata records the intended print resolution; pixels still carry the image detail. */
async function withDpi(blob: Blob, dpi: number): Promise<Blob> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  if (bytes.length < 33 || bytes[12] !== 73 || bytes[13] !== 72 || bytes[14] !== 68 || bytes[15] !== 82) {
    throw new Error('El navegador no produjo un PNG válido.');
  }
  const pixelsPerMeter = Math.round(dpi / 0.0254);
  const resolution = new Uint8Array(9);
  const view = new DataView(resolution.buffer);
  view.setUint32(0, pixelsPerMeter);
  view.setUint32(4, pixelsPerMeter);
  resolution[8] = 1;
  const chunk = pngChunk('pHYs', resolution);
  const output = new Uint8Array(bytes.length + chunk.length);
  output.set(bytes.subarray(0, 33), 0);
  output.set(chunk, 33);
  output.set(bytes.subarray(33), 33 + chunk.length);
  return new Blob([output], { type: 'image/png' });
}

export async function downloadCanvasPng(canvas: HTMLCanvasElement, filename: string, dpi: number): Promise<void> {
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => {
    if (value) resolve(value);
    else reject(new Error('No se pudo capturar la figura.'));
  }, 'image/png'));
  downloadBlob(await withDpi(blob, dpi), filename);
}

/** Capture the rendered card, including headings, legend and interpretation. */
export async function downloadFigureJpg(element: HTMLElement, filename: string, dark: boolean): Promise<void> {
  const bounds = element.getBoundingClientRect();
  if (bounds.width < 2 || bounds.height < 2) throw new Error('La figura aún no tiene dimensiones para exportar.');
  const dataUrl = await toJpeg(element, {
    backgroundColor: dark ? '#0f172a' : '#ffffff',
    pixelRatio: 3,
    quality: 0.96,
    filter: node => !(node instanceof HTMLElement && node.dataset.exportControl === 'true'),
  });
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function downloadTableXlsx(table: HTMLTableElement, filename: string, title: string, interpretation: string): void {
  const sheet = XLSX.utils.table_to_sheet(table, { raw: false });
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, sheet, title.slice(0, 31).replace(/[\\/?*\[\]:]/g, ''));
  const notes = XLSX.utils.aoa_to_sheet([
    ['Figura o tabla', title],
    ['Tipo', 'Interpretación determinística'],
    ['Interpretación', interpretation],
  ]);
  notes['!cols'] = [{ wch: 22 }, { wch: 110 }];
  XLSX.utils.book_append_sheet(workbook, notes, 'Interpretación');
  XLSX.writeFile(workbook, filename);
}
