import { useRef, useState, type ReactNode } from 'react';
import { Download } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { downloadSvgPng, downloadTableXlsx } from '../../services/visualExport';

interface Props {
  title: string;
  filename: string;
  interpretation: string;
  children: ReactNode;
  className?: string;
}

function Interpretation({ text }: { text: string }) {
  return <p className="mt-3 border-t border-slate-200 pt-2 text-[11px] leading-relaxed text-slate-600 dark:border-slate-800 dark:text-slate-400"><strong className="text-slate-700 dark:text-slate-300">Interpretación determinística: </strong>{text}</p>;
}

function ExportButton({ label, busy, onClick }: { label: string; busy: boolean; onClick: () => void }) {
  return <button type="button" title={label} aria-label={label} onClick={onClick} disabled={busy}
    className="absolute right-2 top-2 z-20 inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white/95 px-2 py-1.5 text-[11px] font-semibold text-slate-800 shadow-sm opacity-0 transition-opacity hover:bg-amber-50 focus:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900/95 dark:text-slate-100 dark:hover:bg-slate-800">
    <Download className="h-3.5 w-3.5" />{busy ? 'Preparando…' : label}
  </button>;
}

export function ExportableFigure({ title, filename, interpretation, children, className = '' }: Props) {
  const visualRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { isDark } = useTheme();
  const exportFigure = async () => {
    const svg = visualRef.current?.querySelector('svg');
    if (!svg) { setError('La figura aún no está disponible.'); return; }
    setBusy(true);
    setError('');
    try { await downloadSvgPng(svg, `${filename}.png`, isDark, title); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo exportar la figura.'); }
    finally { setBusy(false); }
  };
  return <figure className={`group relative ${className}`} aria-label={title}>
    <div ref={visualRef} className="relative">
      {children}
      <ExportButton label="Descargar PNG" busy={busy} onClick={() => void exportFigure()} />
    </div>
    <figcaption><Interpretation text={interpretation} /></figcaption>
    {error && <p role="alert" className="mt-1 text-xs text-rose-600">{error}</p>}
  </figure>;
}

export function ExportableTable({ title, filename, interpretation, children, className = '' }: Props) {
  const tableRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');
  const exportTable = () => {
    const table = tableRef.current?.querySelector('table');
    if (!table) { setError('La tabla aún no está disponible.'); return; }
    setError('');
    try { downloadTableXlsx(table, `${filename}.xlsx`, title, interpretation); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo exportar la tabla.'); }
  };
  return <section className={`group relative ${className}`} aria-label={title}>
    <div ref={tableRef} className="relative">
      {children}
      <ExportButton label="Exportar Excel" busy={false} onClick={exportTable} />
    </div>
    <Interpretation text={interpretation} />
    {error && <p role="alert" className="mt-1 text-xs text-rose-600">{error}</p>}
  </section>;
}
