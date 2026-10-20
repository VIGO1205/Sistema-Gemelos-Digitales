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

export async function downloadSvgPng(svg: SVGSVGElement, filename: string, dark: boolean, title: string): Promise<void> {
  const bounds = svg.getBoundingClientRect();
  const viewBox = svg.viewBox.baseVal;
  const width = Math.max(1, Math.round(bounds.width || viewBox.width));
  const height = Math.max(1, Math.round(bounds.height || viewBox.height));
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttribute('width', String(width));
  clone.setAttribute('height', String(height));
  clone.setAttribute('color', dark ? '#cbd5e1' : '#334155');
  const markup = new XMLSerializer().serializeToString(clone);
  const image = new Image();
  const url = URL.createObjectURL(new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }));
  try {
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error('No se pudo convertir el gráfico a PNG.'));
      image.src = url;
    });
    const legend = Array.from(svg.closest('.recharts-wrapper')?.querySelectorAll('.recharts-legend-item') ?? [])
      .map(item => ({
        label: item.querySelector('.recharts-legend-item-text')?.textContent?.trim() ?? '',
        color: item.querySelector('.recharts-legend-icon')?.getAttribute('stroke') ||
          item.querySelector('.recharts-legend-icon')?.getAttribute('fill') || '#64748b',
      })).filter(item => item.label);
    const top = 42;
    const bottom = legend.length ? 34 : 0;
    const canvas = document.createElement('canvas');
    const scale = 3;
    canvas.width = width * scale;
    canvas.height = (height + top + bottom) * scale;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('No se pudo crear la imagen.');
    context.fillStyle = dark ? '#0f172a' : '#ffffff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.scale(scale, scale);
    context.fillStyle = dark ? '#f1f5f9' : '#0f172a';
    context.font = 'bold 15px Arial, sans-serif';
    context.fillText(title, 14, 27, Math.max(1, width - 28));
    context.drawImage(image, 0, top, width, height);
    if (legend.length) {
      context.font = '12px Arial, sans-serif';
      let x = 14;
      for (const item of legend) {
        context.fillStyle = item.color;
        context.fillRect(x, top + height + 11, 11, 4);
        context.fillStyle = dark ? '#cbd5e1' : '#475569';
        context.fillText(item.label, x + 16, top + height + 17);
        x += Math.min(context.measureText(item.label).width + 40, width / legend.length);
      }
    }
    await downloadCanvasPng(canvas, filename, 288);
  } finally {
    URL.revokeObjectURL(url);
  }
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
