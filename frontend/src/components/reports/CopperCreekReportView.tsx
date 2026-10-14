import { useState } from 'react';
import { Award, Download, Eye, FileSpreadsheet, FileText, Layers, ShieldCheck } from 'lucide-react';
import type { UserRole } from '../../types';
import { useCopperCreekStudy } from '../../hooks/useCopperCreekStudy';
import { buildStudyReport, buildStudyPdf, buildStudyWord, downloadBlob, exportStudyExcel, studyFilename } from '../../services/copperCreekReport';
import { useToast } from '../../context/ToastContext';
import { MiningLoader } from '../shared/MiningLoader';
import { PdfPreviewModal } from './PdfPreviewModal';

interface Props { currentRole: UserRole; userName: string }

export function CopperCreekReportView({ currentRole, userName }: Props) {
  const { scene, model, error } = useCopperCreekStudy();
  const [title, setTitle] = useState('Informe académico de leyes · Copper Creek Mammoth');
  const [working, setWorking] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { addToast } = useToast();
  const author = `${userName} (${currentRole})`;

  if (error) return <div className="rounded-xl border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-300">{error}</div>;
  if (!scene || !model) return <MiningLoader title="Preparando reportes de Copper Creek" detail="Cargando sondajes, cubos y validación del modelo publicado." className="h-full" />;

  const report = () => buildStudyReport(scene, model, title, author);
  const closePreview = () => {
    setPreviewOpen(false);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
  };
  const previewPdf = () => {
    setWorking('PDF'); setPreviewOpen(true);
    try {
      const url = URL.createObjectURL(buildStudyPdf(report()).output('blob'));
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(url);
    } catch {
      addToast('No se pudo generar la vista previa del PDF', 'error'); setPreviewOpen(false);
    } finally { setWorking(null); }
  };
  const downloadPdf = () => {
    setWorking('PDF');
    try { downloadBlob(buildStudyPdf(report()).output('blob'), studyFilename('pdf')); addToast('Informe PDF descargado', 'success'); }
    catch { addToast('No se pudo descargar el PDF', 'error'); }
    finally { setWorking(null); }
  };
  const downloadExcel = () => {
    setWorking('EXCEL');
    try { exportStudyExcel(report()); addToast('Planilla Excel descargada', 'success'); }
    catch { addToast('No se pudo descargar la planilla Excel', 'error'); }
    finally { setWorking(null); }
  };
  const downloadWord = async () => {
    setWorking('WORD');
    try { downloadBlob(await buildStudyWord(report()), studyFilename('docx')); addToast('Memoria Word descargada', 'success'); }
    catch { addToast('No se pudo generar el documento Word', 'error'); }
    finally { setWorking(null); }
  };

  return <div className="space-y-4 sm:space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div><h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2"><FileText className="w-5 h-5 text-amber-500" />Generador de Reportes Académicos</h2><p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Sondajes públicos, cubos reconstruidos y validación del modelo publicado de Copper Creek · Mammoth</p></div>
      <div className="flex items-center gap-2"><Award className="w-5 h-5 text-amber-500" /><span className="text-xs font-mono text-amber-600 dark:text-amber-400 font-semibold">Uso académico · Sin certificación</span></div>
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 space-y-4 shadow-sm">
        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase font-display tracking-wider border-b border-slate-200 dark:border-slate-800 pb-2">Parámetros del Informe Técnico</h3>
        <div className="space-y-3 text-xs">
          <div><label htmlFor="report-title" className="block text-slate-700 dark:text-slate-300 font-medium mb-1">Título del documento:</label><input id="report-title" type="text" value={title} onChange={event => setTitle(event.target.value)} className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100 focus:outline-none focus:border-amber-500 text-xs" /></div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">El título se incorpora al PDF y Word. Los tres archivos describen la misma escena y modelo publicado.</p>
          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <div className="flex justify-between gap-2"><span>Proyecto:</span><span className="font-mono font-bold text-slate-800 dark:text-slate-200">Copper Creek · Mammoth</span></div>
            <div className="flex justify-between gap-2"><span>Cobertura:</span><span className="font-mono font-bold text-amber-600 dark:text-amber-400">{scene.pit_levels.length} bancos · {scene.blocks.length.toLocaleString('es-PE')} cubos</span></div>
            <div className="flex justify-between gap-2"><span>Modelo:</span><span className="font-mono font-bold text-cyan-700 dark:text-cyan-400">{model.model_name}</span></div>
            <div className="flex justify-between gap-2"><span>Generado por:</span><span className="font-mono font-bold text-cyan-700 dark:text-cyan-400 text-right">{author}</span></div>
          </div>
        </div>
      </div>
      <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-sm hover:border-amber-500/50 transition-all">
          <div><div className="w-10 h-10 rounded-xl bg-rose-500/10 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-3"><FileText className="w-5 h-5" /></div><h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display mb-1">Reporte Académico en PDF</h4><p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">Procedencia, validación por sondaje, comparación de modelos, resumen por banco y límites del estudio.</p></div>
          <button onClick={previewPdf} disabled={working !== null} className="w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2 shadow disabled:opacity-60"><Eye className="w-4 h-4" />{working === 'PDF' ? 'Generando PDF...' : 'Previsualizar Informe PDF'}</button>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-sm hover:border-emerald-500/50 transition-all">
          <div><div className="w-10 h-10 rounded-xl bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3"><FileSpreadsheet className="w-5 h-5" /></div><h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display mb-1">Planilla de Estudio (Excel)</h4><p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">Alcance, métricas, bancos, coordenadas y %Cu de cada cubo; ubicación de sondajes visibles.</p></div>
          <button onClick={downloadExcel} disabled={working !== null} className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2 shadow disabled:opacity-60"><Download className="w-4 h-4" />{working === 'EXCEL' ? 'Exportando...' : 'Descargar Planilla Excel'}</button>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-sm hover:border-cyan-500/50 transition-all">
          <div><div className="w-10 h-10 rounded-xl bg-cyan-500/10 dark:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 flex items-center justify-center mb-3"><FileText className="w-5 h-5" /></div><h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display mb-1">Memoria Técnica (Word)</h4><p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">Documento .docx real con metodología, resultados por banco y límites para revisar y editar.</p></div>
          <button onClick={() => void downloadWord()} disabled={working !== null} className="w-full py-2.5 px-4 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2 shadow disabled:opacity-60"><Download className="w-4 h-4" />{working === 'WORD' ? 'Generando Word...' : 'Descargar Memoria .DOCX'}</button>
        </div>
        <div className="bg-gradient-to-br from-amber-500/10 to-amber-500/5 border border-amber-300 dark:border-amber-500/30 rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-start gap-3"><div className="p-2 rounded-xl bg-amber-500 text-slate-950"><ShieldCheck className="w-5 h-5" /></div><div><h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display">Alcance del reporte</h4><p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">Usa ensayos públicos y una reconstrucción académica. No es el modelo de recursos oficial ni acredita despacho, tonelaje o planta.</p></div></div>
          <div className="mt-4 pt-3 border-t border-amber-200 dark:border-amber-500/20 flex items-center justify-between text-[11px] font-mono text-amber-700 dark:text-amber-400"><span>Sin firma profesional</span><span className="font-bold">Exploración académica</span></div>
        </div>
      </div>
    </div>
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
      <h4 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2"><Layers className="w-4 h-4 text-amber-500" />Contenido y límites de los reportes</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
        {[
          ['Ensayos de Cu', `${scene.metadata.study_holes} sondajes del estudio y ${scene.metadata.used_composites} compositos usados en el modelado.`],
          ['Modelo y validación', `${model.model_name}, validación con sondajes completos no vistos y métricas RMSE, MAE y R².`],
          ['Geometría 3D', `${scene.blocks.length.toLocaleString('es-PE')} cubos de 20 × 20 × 12 m y ${scene.pit_levels.length} bancos aproximados; ${scene.metadata.crs}.`],
          ['Soporte espacial', `${scene.metadata.skipped_unsupported_blocks} posiciones excluidas por soporte insuficiente; distancia y sondajes de apoyo por cubo.`],
          ['SWIR y planta', 'No hay espectros SWIR ni mediciones reales de planta en este estudio.'],
          ['Recursos e incertidumbre', 'Sin clasificación de recursos ni P10/P50/P90 calibrados. La dispersión vecinal es descriptiva.'],
        ].map(([label, detail]) => <div key={label} className="bg-slate-50 dark:bg-slate-950/60 p-3 rounded-xl border border-slate-200 dark:border-slate-800/80"><span className="font-bold text-amber-600 dark:text-amber-400">{label}</span><p className="text-slate-600 dark:text-slate-300 mt-1">{detail}</p></div>)}
      </div>
    </div>
    <PdfPreviewModal open={previewOpen} loading={working === 'PDF' && !previewUrl} previewUrl={previewUrl} onClose={closePreview} onDownload={downloadPdf} downloading={working === 'PDF'} projectName="Copper Creek · Mammoth" scopeLabel={`${scene.pit_levels.length} bancos · ${scene.blocks.length.toLocaleString('es-PE')} cubos`} generatedBy={author} />
  </div>;
}
