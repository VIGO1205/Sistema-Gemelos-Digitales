import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Bell, CheckCircle2, ExternalLink, FlaskConical, Layers, ShieldAlert } from 'lucide-react';
import { useCopperCreekStudy } from '../../hooks/useCopperCreekStudy';
import { buildReviewSignals, type ReviewKind } from '../../services/copperCreekReview';
import { MiningLoader } from '../shared/MiningLoader';

interface Props {
  onOpenViewer: () => void;
}

const card = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm';
const kinds: Array<{ value: ReviewKind | 'ALL'; label: string }> = [
  { value: 'ALL', label: 'Todas' },
  { value: 'SUPPORT', label: 'Soporte' },
  { value: 'DISAGREEMENT', label: 'Desacuerdo' },
  { value: 'VARIATION', label: 'Variación' },
];

export function AlertsManager({ onOpenViewer }: Props) {
  const { scene, model, error } = useCopperCreekStudy();
  const [bench, setBench] = useState<number | 'ALL'>('ALL');
  const [kind, setKind] = useState<ReviewKind | 'ALL'>('ALL');
  const [cutoff, setCutoff] = useState(0.13);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState<string[]>([]);
  useEffect(() => {
    if (!model) return;
    try {
      const saved = JSON.parse(sessionStorage.getItem(`copper-creek-review:${model.exported_at}`) ?? '[]');
      setReviewed(Array.isArray(saved) ? saved.filter((value): value is string => typeof value === 'string') : []);
    } catch { setReviewed([]); }
  }, [model]);
  const rmse = model?.comparison[model.model_name]?.mean_rmse ?? 0;
  const signals = useMemo(() => scene && rmse > 0 ? buildReviewSignals(scene.blocks, rmse) : [], [scene, rmse]);
  const benches = useMemo(() => [...new Set<number>(scene?.blocks.map(block => block.bench) ?? [])].sort((a, b) => b - a), [scene]);
  const visible = signals.filter(signal =>
    (bench === 'ALL' || signal.bench === bench) && (kind === 'ALL' || signal.kind === kind));
  const selected = visible.find(signal => signal.id === selectedId) ?? visible[0];
  const destination = useMemo(() => {
    const blocks = scene?.blocks.filter(block => bench === 'ALL' || block.bench === bench) ?? [];
    const above = blocks.filter(block => block.cu_bayesian >= cutoff).length;
    const modelDisagreement = blocks.filter(block =>
      (block.cu_bayesian >= cutoff) !== ((block.cu_idw3 ?? block.cu_base) >= cutoff)).length;
    return { above, below: blocks.length - above, modelDisagreement };
  }, [scene, bench, cutoff]);

  if (error) return <div role="alert" className="rounded-xl border border-rose-400 p-4 text-sm text-rose-700 dark:text-rose-300">{error}</div>;
  if (!scene || !model) return <MiningLoader title="Preparando señales de revisión" detail="Revisando soporte y diferencias de ley en los cubos reconstruidos." />;

  const markReviewed = (id: string) => setReviewed(previous => {
    const next = previous.includes(id) ? previous.filter(value => value !== id) : [...previous, id];
    try { sessionStorage.setItem(`copper-creek-review:${model.exported_at}`, JSON.stringify(next)); } catch { /* Memoria local de la vista. */ }
    return next;
  });
  const pending = visible.filter(signal => !reviewed.includes(signal.id)).length;
  const covered = scene.blocks.length;
  const unsupported = scene.metadata.skipped_unsupported_blocks;

  return <div className="space-y-4 sm:space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div>
        <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2"><Bell className="h-5 w-5 text-amber-500" /> Señales para Revisión Geológica</h2>
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">Señales exploratorias calculadas de los mismos cubos y del modelo {model.model_name} que usa el Gemelo Digital 3D.</p>
      </div>
      <button type="button" onClick={onOpenViewer} className="flex items-center gap-1 rounded-xl bg-amber-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-amber-600"><ExternalLink className="h-3.5 w-3.5" /> Abrir visor 3D</button>
    </div>

    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><ShieldAlert className="h-4 w-4 text-amber-500" /> Señales pendientes en filtro</div><div className="mt-2 font-mono text-2xl font-bold">{pending}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Revisión local en esta sesión; no son alarmas operativas.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><Layers className="h-4 w-4 text-cyan-500" /> Cubos con soporte</div><div className="mt-2 font-mono text-2xl font-bold">{covered.toLocaleString('es-PE')}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{unsupported.toLocaleString('es-PE')} candidatos sin soporte omitidos de la escena.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><FlaskConical className="h-4 w-4 text-emerald-500" /> Error de validación</div><div className="mt-2 font-mono text-2xl font-bold">{rmse.toFixed(3)} %Cu</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">RMSE en cinco grupos de sondajes completos no vistos.</p></div>
    </div>

    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white p-3 text-xs dark:border-slate-800 dark:bg-slate-900">
      <label className="font-semibold text-slate-600 dark:text-slate-300" htmlFor="cc-alert-bench">Banco</label>
      <select id="cc-alert-bench" value={bench} onChange={event => setBench(event.target.value === 'ALL' ? 'ALL' : Number(event.target.value))} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 dark:border-slate-700 dark:bg-slate-900"><option value="ALL">Todos</option>{benches.map(level => <option key={level} value={level}>{level} m</option>)}</select>
      <span className="ml-2 font-semibold text-slate-600 dark:text-slate-300">Tipo</span>
      {kinds.map(option => <button key={option.value} type="button" onClick={() => setKind(option.value)} className={`rounded-md px-2 py-1 font-mono text-[10px] transition-all ${kind === option.value ? 'bg-amber-500 font-bold text-slate-950 shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'}`}>{option.label}</button>)}
    </div>

    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className={`${card} space-y-2 lg:max-h-[560px] lg:overflow-y-auto`}>
        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase font-display tracking-wider">Alertas activas para revisión ({visible.length})</h3>
        {visible.length === 0 && <p className="text-xs text-slate-500">Sin señales para este filtro.</p>}
        {visible.map(signal => <button key={signal.id} type="button" onClick={() => setSelectedId(signal.id)} className={`w-full rounded-xl border p-3 text-left text-xs transition-all hover:shadow-sm ${selected?.id === signal.id ? 'border-amber-400 bg-amber-50 dark:bg-amber-950/20' : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50'}`}>
          <div className="flex items-center justify-between gap-2"><span className="font-bold">{signal.title}</span>{reviewed.includes(signal.id) ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <AlertTriangle className="h-4 w-4 text-amber-500" />}</div>
          <p className="mt-1 font-mono text-slate-600 dark:text-slate-300">Banco {signal.bench} m · {signal.count} cubos</p>
        </button>)}
      </div>
      <div className={`${card} lg:col-span-2`}>
        {selected ? <div className="space-y-4 text-sm">
          <div><h3 className="font-display font-bold text-slate-900 dark:text-slate-100">{selected.title}</h3><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Banco {selected.bench} m · {selected.count} cubos · ejemplo {selected.representative.id}</p></div>
          <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <div><span className="text-slate-500">Ley {model.model_name}</span><p className="font-mono font-bold">{selected.representative.cu_bayesian.toFixed(4)} %Cu</p></div>
            <div><span className="text-slate-500">IDW3 referencia</span><p className="font-mono font-bold">{(selected.representative.cu_idw3 ?? selected.representative.cu_base).toFixed(4)} %Cu</p></div>
            <div><span className="text-slate-500">Sondajes de soporte</span><p className="font-mono font-bold">{selected.representative.support_holes ?? '—'}</p></div>
            <div><span className="text-slate-500">Sondaje más cercano</span><p className="font-mono font-bold">{selected.representative.nearest_drillhole_m?.toFixed(1) ?? '—'} m</p></div>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300">Criterio: {selected.kind === 'SUPPORT' ? `${selected.observed} sondajes, mínimo permitido ${selected.threshold}` : `${selected.observed.toFixed(3)} %Cu frente al umbral ${selected.threshold.toFixed(3)} %Cu`}</p>
          <p className="rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 dark:bg-slate-800 dark:text-slate-300">{selected.explanation}</p>
          <p className="text-xs"><strong>Acción recomendada:</strong> {selected.action}</p>
          <button type="button" onClick={() => markReviewed(selected.id)} className="rounded-xl border border-emerald-400 px-3 py-2 text-xs font-semibold text-emerald-700 dark:text-emerald-300">{reviewed.includes(selected.id) ? 'Volver a pendiente' : 'Marcar como revisada'}</button>
        </div> : <p className="text-xs text-slate-500">Selecciona una señal.</p>}
      </div>
    </div>

    <div className={card}>
      <h3 className="font-display text-sm font-bold">Escenario de clasificación por ley estimada</h3>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Cuenta cubos con soporte por encima o debajo de un umbral elegido para exploración. No asigna destinos reales.</p>
      <label className="mt-3 flex items-center gap-2 text-xs" htmlFor="cc-grade-threshold"><span className="font-semibold">Umbral %Cu</span><input id="cc-grade-threshold" type="number" min="0" max="5" step="0.01" value={cutoff} onChange={event => { const value = Number(event.target.value); if (Number.isFinite(value) && value >= 0 && value <= 5) setCutoff(value); }} className="w-24 rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono dark:border-slate-700 dark:bg-slate-800" /></label>
      <div className="mt-3 grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
        <div className="rounded-xl bg-emerald-50 p-3 dark:bg-emerald-950/20"><span className="text-slate-600 dark:text-slate-300">Sobre umbral · {model.model_name}</span><p className="mt-1 font-mono text-xl font-bold text-emerald-700 dark:text-emerald-400">{destination.above.toLocaleString('es-PE')}</p></div>
        <div className="rounded-xl bg-slate-100 p-3 dark:bg-slate-800"><span className="text-slate-600 dark:text-slate-300">Bajo umbral · {model.model_name}</span><p className="mt-1 font-mono text-xl font-bold">{destination.below.toLocaleString('es-PE')}</p></div>
        <div className="rounded-xl bg-amber-50 p-3 dark:bg-amber-950/20"><span className="text-slate-600 dark:text-slate-300">Cruzan el umbral distinto con IDW3</span><p className="mt-1 font-mono text-xl font-bold text-amber-700 dark:text-amber-400">{destination.modelDisagreement.toLocaleString('es-PE')}</p></div>
      </div>
      <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Sin densidad validada, recuperación, dilución, costos ni trazabilidad de extracción, estos conteos no definen mineral, desmonte o envío a planta.</p>
    </div>

    <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-xs leading-relaxed text-cyan-900 dark:border-cyan-900 dark:bg-cyan-950/20 dark:text-cyan-200"><strong>Alcance de estas señales.</strong> Sirven para priorizar la revisión académica de cubos. Los CSV públicos no contienen voladuras, rutas, toneladas medidas ni señales de planta; marcar una señal como revisada solo se guarda en este navegador durante la sesión y no envía instrucciones de despacho.</div>
  </div>;
}
