import { useEffect, useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { Activity, ChevronDown, ChevronUp, Cpu, Database, FlaskConical, Layers, MapPin, TrendingUp, Zap } from 'lucide-react';
import api from '../../services/api';
import { useTheme } from '../../context/ThemeContext';
import type { CopperCreekScene } from '../viewer3d/CopperCreekViewer';
import { MiningLoader } from '../shared/MiningLoader';

interface Props {
  onOpenViewer: () => void;
}

const card = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm';

export function ExecutiveDashboard({ onOpenViewer }: Props) {
  const { isDark } = useTheme();
  const [scene, setScene] = useState<CopperCreekScene | null>(null);
  const [bench, setBench] = useState<number | 'ALL'>('ALL');
  const [showTwinInfo, setShowTwinInfo] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.get<CopperCreekScene>('/api/copper-creek/mammoth-reconstruction'),
      api.get<{ model: { model_name: string; exported_at: string } }>('/api/copper-creek/model-info'),
    ]).then(([sceneResponse, modelResponse]) => {
      if (!mounted) return;
      const loaded = sceneResponse.data;
      if (loaded.metadata.model_name !== modelResponse.data.model.model_name ||
          loaded.metadata.model_exported_at !== modelResponse.data.model.exported_at) {
        setError('La escena no coincide con el modelo publicado. Reconstruye Copper Creek.');
        return;
      }
      setScene(loaded);
    }).catch(() => {
      if (mounted) setError('No se pudo cargar Copper Creek o el modelo publicado por FastAPI.');
    });
    return () => { mounted = false; };
  }, []);

  const benches = useMemo(
    () => [...new Set<number>(scene?.blocks.map(block => block.bench) ?? [])].sort((a, b) => b - a),
    [scene],
  );
  const blocks = useMemo(
    () => scene?.blocks.filter(block => bench === 'ALL' || block.bench === bench) ?? [],
    [scene, bench],
  );
  const benchSeries = useMemo(() => benches.map(level => {
    const subset = blocks.filter(block => block.bench === level);
    const count = subset.length;
    return {
      bench: String(level),
      winner: count ? subset.reduce((sum, block) => sum + block.cu_bayesian, 0) / count : 0,
      idw3: count ? subset.reduce((sum, block) => sum + (block.cu_idw3 ?? 0), 0) / count : 0,
      count,
    };
  }).filter(row => row.count > 0), [blocks, benches]);

  const distribution = useMemo(() => {
    const ranges = [
      { label: '<0,13', min: 0, max: 0.13 },
      { label: '0,13–0,45', min: 0.13, max: 0.45 },
      { label: '0,45–0,80', min: 0.45, max: 0.8 },
      { label: '≥0,80', min: 0.8, max: Infinity },
    ];
    return ranges.map(range => ({
      tramo: range.label,
      cubos: blocks.filter(block => block.cu_bayesian >= range.min && block.cu_bayesian < range.max).length,
    }));
  }, [blocks]);

  if (error) {
    return <div role="alert" className="rounded-2xl border border-rose-300 bg-rose-50 p-5 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/20 dark:text-rose-300">{error}</div>;
  }
  if (!scene) {
    return <MiningLoader title="Preparando el Dashboard" detail="Organizando indicadores de ley y cobertura de los bancos de Mammoth." />;
  }

  const metadata = scene.metadata;
  const winner = metadata.model_validation[metadata.model_name];
  const idw3 = metadata.model_validation.IDW3;
  const coverage = scene.blocks.length / (scene.blocks.length + metadata.skipped_unsupported_blocks) * 100;
  const meanGrade = blocks.length
    ? blocks.reduce((sum, block) => sum + block.cu_bayesian, 0) / blocks.length : 0;
  const improvement = idw3 && winner ? (idw3.mean_rmse - winner.mean_rmse) / idw3.mean_rmse * 100 : 0;
  const chartText = isDark ? '#94a3b8' : '#64748b';
  const chartGrid = isDark ? '#334155' : '#e2e8f0';
  const tooltipStyle = {
    backgroundColor: isDark ? '#0f172a' : '#fff',
    borderColor: isDark ? '#334155' : '#cbd5e1',
    color: isDark ? '#f8fafc' : '#0f172a',
    borderRadius: 10,
  };
  const comparison = Object.keys(metadata.model_validation)
    .map(model => ({ model, rmse: metadata.model_validation[model].mean_rmse, mae: metadata.model_validation[model].mean_mae }))
    .sort((a, b) => a.rmse - b.rmse);

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 sm:p-5 dark:border-amber-500/30 dark:bg-slate-900">
        <div>
          <h2 className="font-display text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2"><Zap className="h-5 w-5 text-amber-500" /> Copper Creek · sector Mammoth</h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">Resumen exploratorio de los mismos cubos del Gemelo Digital 3D. El %Cu estimado se basa en sondajes públicos.</p>
        </div>
        <button type="button" onClick={onOpenViewer} className="rounded-xl bg-amber-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-amber-600">
          Abrir Gemelo Digital 3D
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="mr-1 font-semibold text-slate-600 dark:text-slate-300">Banco:</span>
        <button type="button" onClick={() => setBench('ALL')} className={`rounded-lg px-2.5 py-1.5 ${bench === 'ALL' ? 'bg-amber-500 font-bold text-slate-950' : 'bg-white text-slate-700 dark:bg-slate-800 dark:text-slate-200'}`}>Todos</button>
        {benches.map(level => (
          <button key={level} type="button" onClick={() => setBench(level)} className={`rounded-lg px-2.5 py-1.5 ${bench === level ? 'bg-amber-500 font-bold text-slate-950' : 'bg-white text-slate-700 dark:bg-slate-800 dark:text-slate-200'}`}>
            {level} m
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className={card + ' relative overflow-hidden hover:shadow-md transition-shadow'}>
          <Layers className="absolute right-3 top-3 h-16 w-16 text-amber-500 opacity-10" />
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider font-display text-slate-500 dark:text-slate-400">Cubos con soporte</div>
          <div className="mt-2 font-mono text-2xl font-bold text-slate-900 dark:text-slate-100">{blocks.length.toLocaleString('es-PE')}</div>
          <p className="mt-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">{bench === 'ALL' ? `${coverage.toFixed(1)}% de los cubos candidatos; ${metadata.skipped_unsupported_blocks.toLocaleString('es-PE')} omitidos` : 'Cubos estimados del banco seleccionado'}</p>
        </div>
        <div className={card + ' relative overflow-hidden hover:shadow-md transition-shadow'}>
          <TrendingUp className="absolute right-3 top-3 h-16 w-16 text-emerald-500 opacity-10" />
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider font-display text-slate-500 dark:text-slate-400">Ley Cu media estimada</div>
          <div className="mt-2 font-mono text-2xl font-bold text-emerald-700 dark:text-emerald-400">{meanGrade.toFixed(3)} %Cu</div>
          <p className="mt-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">{metadata.model_name} · promedio simple de cubos con soporte</p>
        </div>
        <div className={card + ' relative overflow-hidden hover:shadow-md transition-shadow'}>
          <FlaskConical className="absolute right-3 top-3 h-16 w-16 text-cyan-500 opacity-10" />
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider font-display text-slate-500 dark:text-slate-400">Sondajes de estudio</div>
          <div className="mt-2 font-mono text-2xl font-bold text-slate-900 dark:text-slate-100">{metadata.study_holes}</div>
          <p className="mt-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">{metadata.used_composites.toLocaleString('es-PE')} composites de ~6 m · {metadata.displayed_holes} trazas visibles</p>
        </div>
        <div className={card + ' relative overflow-hidden hover:shadow-md transition-shadow'}>
          <MapPin className="absolute right-3 top-3 h-16 w-16 text-indigo-500 opacity-10" />
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider font-display text-slate-500 dark:text-slate-400">RMSE de validación</div>
          <div className="mt-2 font-mono text-2xl font-bold text-indigo-700 dark:text-indigo-400">{winner.mean_rmse.toFixed(3)} %Cu</div>
          <p className="mt-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">5 grupos de sondajes no vistos · {improvement.toFixed(1)}% menos que IDW3</p>
        </div>
      </div>

      <div className={card + ' text-slate-900 dark:text-slate-100 shadow-md'}>
        <button type="button" onClick={() => setShowTwinInfo(value => !value)} className="flex w-full items-center justify-between gap-3 text-left">
          <span className="flex items-center gap-3"><span className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-2.5 text-amber-600 dark:text-amber-400"><Cpu className="h-5 w-5" /></span><span><strong className="block font-display text-sm">¿Qué es este Gemelo Digital M-6 y cómo predice?</strong><span className="text-xs text-slate-500 dark:text-slate-400">Reconstrucción académica de Mammoth con sondajes públicos y un estimador de ley.</span></span></span>
          {showTwinInfo ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        {showTwinInfo && <div className="mt-4 grid grid-cols-1 gap-3 border-t border-slate-200 pt-4 text-xs dark:border-slate-800 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950"><strong className="text-amber-600 dark:text-amber-400">1. Sondajes y ensayos</strong><p className="mt-1">Las muestras Cu aportan la ley observada para entrenar y validar el modelo.</p></div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950"><strong className="text-emerald-600 dark:text-emerald-400">2. Cubos reconstruidos</strong><p className="mt-1">Se estima %Cu en el centro de cada cubo con soporte cercano suficiente.</p></div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950"><strong className="text-cyan-600 dark:text-cyan-400">3. Alcance</strong><p className="mt-1">Random Forest entrega una ley puntual; no hay datos de planta ni despacho validado.</p></div>
        </div>}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className={card}>
          <h3 className="font-display text-sm font-bold text-slate-900 dark:text-slate-100">Ley Cu media por banco</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Modelo seleccionado frente a la estimación IDW3 de referencia; sin interpretación de reservas.</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={benchSeries}>
                <CartesianGrid stroke={chartGrid} strokeDasharray="3 3" />
                <XAxis dataKey="bench" stroke={chartText} tick={{ fontSize: 10 }} />
                <YAxis stroke={chartText} tick={{ fontSize: 10 }} unit="%" />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend />
                <Line dataKey="winner" name={metadata.model_name} stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line dataKey="idw3" name="IDW3" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className={card}>
          <h3 className="font-display text-sm font-bold text-slate-900 dark:text-slate-100">Cubos por tramo de ley estimada</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Conteos del banco seleccionado; los rangos son solo exploratorios.</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distribution}>
                <CartesianGrid stroke={chartGrid} strokeDasharray="3 3" />
                <XAxis dataKey="tramo" stroke={chartText} tick={{ fontSize: 10 }} />
                <YAxis stroke={chartText} tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="cubos" name="Cubos con soporte" fill="#0284c7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className={card}>
        <h3 className="font-display text-sm font-bold text-slate-900 dark:text-slate-100">Cobertura espacial por banco</h3>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Conteo de cubos con soporte que el modelo pudo estimar en cada nivel de la reconstrucción.</p>
        <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={benchSeries}>
          <CartesianGrid stroke={chartGrid} strokeDasharray="3 3" /><XAxis dataKey="bench" stroke={chartText} tick={{ fontSize: 10 }} /><YAxis stroke={chartText} tick={{ fontSize: 10 }} />
          <Tooltip contentStyle={tooltipStyle} /><Bar dataKey="count" name="Cubos con soporte" fill="#f59e0b" radius={[4, 4, 0, 0]} />
        </BarChart></ResponsiveContainer></div>
      </div>

      <div className={card}>
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-amber-500" />
          <h3 className="font-display text-sm font-bold text-slate-900 dark:text-slate-100">Selección del estimador para Copper Creek</h3>
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">RMSE y MAE sobre los mismos composites con soporte, reservando sondajes completos en cinco particiones. Menor error es mejor.</p>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {comparison.map(row => (
            <div key={row.model} className={`rounded-xl border p-3 text-xs ${row.model === metadata.model_name ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/20' : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/60'}`}>
              <p className="font-bold text-slate-900 dark:text-slate-100">{row.model}{row.model === metadata.model_name ? ' · seleccionado' : ''}</p>
              <p className="mt-2 font-mono text-slate-600 dark:text-slate-300">RMSE {row.rmse.toFixed(3)} %Cu</p>
              <p className="font-mono text-slate-600 dark:text-slate-300">MAE {row.mae.toFixed(3)} %Cu</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 dark:border-cyan-900 dark:bg-cyan-950/20">
        <div className="flex items-center gap-2 font-display text-sm font-bold text-cyan-900 dark:text-cyan-200"><Activity className="h-4 w-4" /> Alcance del resumen espacial</div>
        <p className="mt-1 text-xs leading-relaxed text-cyan-800 dark:text-cyan-300">Los indicadores de esta vista provienen de sondajes y cubos estimados de Copper Creek. El control estadístico de planta (EWMA/CUSUM), la dilución y la reconciliación requieren mediciones de extracción y planta vinculadas al mismo material; esas series no forman parte de los CSV públicos.</p>
        <p className="mt-2 text-[11px] text-cyan-700 dark:text-cyan-400">La geometría del tajo y los cubos son una reconstrucción académica.</p>
      </div>
    </div>
  );
}
