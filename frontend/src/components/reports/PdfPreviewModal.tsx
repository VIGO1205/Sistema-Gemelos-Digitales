import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Download,
  X,
  CheckCircle2,
  Loader2,
  Eye,
  ShieldCheck
} from 'lucide-react';

interface PdfPreviewModalProps {
  open: boolean;
  loading: boolean;
  previewUrl: string | null;
  onClose: () => void;
  onDownload: () => void;
  downloading: boolean;
  projectName: string;
  scopeLabel: string;
  generatedBy: string;
}

export const PdfPreviewModal: React.FC<PdfPreviewModalProps> = ({
  open,
  loading,
  previewUrl,
  onClose,
  onDownload,
  downloading,
  projectName,
  scopeLabel,
  generatedBy
}) => {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <motion.div
      className="fixed inset-0 z-[90] flex items-center justify-center p-3 sm:p-6 bg-slate-950/70 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 360, damping: 30 }}
            className="relative w-full max-w-5xl h-[88vh] max-h-[92vh] flex flex-col overflow-hidden rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/50">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 shrink-0 rounded-xl bg-rose-500/10 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2">
                    Vista Previa del Informe PDF
                    <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 text-[9px] font-mono font-bold uppercase tracking-wider">
                      <Eye className="w-3 h-3" />
                      Preview
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                    {projectName} · {scopeLabel} · {generatedBy}
                  </p>
                </div>
              </div>

              <button
                onClick={onClose}
                className="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                aria-label="Cerrar previsualización"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="relative flex-1 min-h-0 bg-slate-100 dark:bg-slate-950/60">
              {loading || !previewUrl ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                  <div className="relative">
                    <div className="absolute inset-0 rounded-full bg-amber-500/20 blur-xl animate-pulse" />
                    <div className="relative w-12 h-12 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow flex items-center justify-center">
                      <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="text-xs font-bold text-slate-700 dark:text-slate-200 font-mono">
                      Generando previsualización...
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                      Renderizando reporte académico
                    </p>
                  </div>
                  <div className="w-40 h-1 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full w-1/2 rounded-full bg-gradient-to-r from-amber-500 to-amber-400 animate-[m6shimmer_1.2s_ease-in-out_infinite]" />
                  </div>
                </div>
              ) : (
                <iframe
                  src={previewUrl}
                  title="Vista previa del informe PDF"
                  className="absolute inset-0 w-full h-full border-0 bg-white"
                />
              )}
            </div>

            {/* Footer */}
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/50">
              <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-700 dark:text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Copper Creek · Reconstrucción académica · Sin clasificación de recursos</span>
                <span className="sm:hidden">Uso académico</span>
              </div>

              <div className="flex items-center gap-2.5">
                {previewUrl && !loading && (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-bold font-mono text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors inline-flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    Abrir en pestaña nueva
                  </a>
                )}
                <button
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-bold font-mono text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Cerrar
                </button>
                <button
                  onClick={onDownload}
                  disabled={downloading}
                  className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2 shadow disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {downloading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Descargando...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Descargar PDF Ahora
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
