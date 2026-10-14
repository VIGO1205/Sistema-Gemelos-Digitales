import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChevronDown, ChevronUp, DollarSign, FlaskConical, Layers, RotateCcw, Settings2, ShieldAlert, TrendingUp } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useCopperCreekStudy } from '../../hooks/useCopperCreekStudy';
import { MiningLoader } from '../shared/MiningLoader';

const POUNDS_PER_METRIC_TONNE = 2204.62262185;
const defaults = { price: 4.2, recovery: 85, cost: 20 };
const card = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm';

function contributionPerTonne(gradePct: number, price: number, recoveryPct: number, cost: number) {
  return gradePct / 100 * POUNDS_PER_METRIC_TONNE * price * recoveryPct / 100 - cost;
}

export function EconomicDashboard() {
  const { scene, model, error } = useCopperCreekStudy();
  const { isDark } = useTheme();
  const [bench, setBench] = useState<number | 'ALL'>('ALL');
  const [price, setPrice] = useState(defaults.price);
  const [recovery, setRecovery] = useState(defaults.recovery);
  const [cost, setCost] = useState(defaults.cost);
  const [showParams, setShowParams] = useState(true);
  const benches = useMemo(() => [...new Set<number>(scene?.blocks.map(block => block.bench) ?? [])].sort((a, b) => b - a), [scene]);
  const blocks = useMemo(() => scene?.blocks.filter(block => bench === 'ALL' || block.bench === bench) ?? [], [scene, bench]);
  const breakEvenGrade = price > 0 && recovery > 0
    ? cost / (POUNDS_PER_METRIC_TONNE * price * recovery / 100) * 100 : null;
  const summary = useMemo(() => {
    if (!blocks.length) return { meanGrade: 0, meanContribution: 0, above: 0, differentFromIdw3: 0 };
    const meanGrade = blocks.reduce((sum, block) => sum + block.cu_bayesian, 0) / blocks.length;
    const meanContribution = blocks.reduce((sum, block) => sum + contributionPerTonne(block.cu_bayesian, price, recovery, cost), 0) / blocks.length;
    const above = blocks.filter(block => contributionPerTonne(block.cu_bayesian, price, recovery, cost) >= 0).length;
    const differentFromIdw3 = blocks.filter(block =>
      (contributionPerTonne(block.cu_bayesian, price, recovery, cost) >= 0) !==
      (contributionPerTonne(block.cu_idw3 ?? block.cu_base, price, recovery, cost) >= 0)).length;
    return { meanGrade, meanContribution, above, differentFromIdw3 };
  }, [blocks, price, recovery, cost]);
  const byBench = useMemo(() => benches.map(level => {
    const subset = blocks.filter(block => block.bench === level);
    return {
      bench: String(level),
      count: subset.length,
      contribution: subset.length ? subset.reduce((sum, block) => sum + contributionPerTonne(block.cu_bayesian, price, recovery, cost), 0) / subset.length : 0,
      meanGrade: subset.length ? subset.reduce((sum, block) => sum + block.cu_bayesian, 0) / subset.length : 0,
      above: subset.filter(block => contributionPerTonne(block.cu_bayesian, price, recovery, cost) >= 0).length,
    };
  }).filter(row => row.count > 0), [blocks, benches, price, recovery, cost]);
  const sensitivity = useMemo(() => [0.7, 0.85, 1, 1.15, 1.3].map(factor => {
    const assumedPrice = price * factor;
    return {
      price: assumedPrice.toFixed(2),
      above: blocks.filter(block => contributionPerTonne(block.cu_bayesian, assumedPrice, recovery, cost) >= 0).length,
    };
  }), [blocks, price, recovery, cost]);

  if (error) return <div role="alert" className="rounded-xl border border-rose-400 p-4 text-sm text-rose-700 dark:text-rose-300">{error}</div>;
  if (!scene || !model) return <MiningLoader title="Preparando el análisis económico" detail="Leyendo las leyes estimadas y los bancos para el escenario académico." />;

  const setNumber = (setter: (value: number) => void, maximum: number) => (raw: string) => {
    const value = Number(raw);
    if (Number.isFinite(value) && value >= 0 && value <= maximum) setter(value);
  };
  const tooltipStyle = { backgroundColor: isDark ? '#0f172a' : '#fff', borderColor: isDark ? '#334155' : '#cbd5e1', color: isDark ? '#f8fafc' : '#0f172a', borderRadius: 10 };

  return <div className="space-y-4 sm:space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div><h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2"><DollarSign className="h-5 w-5 text-amber-600 dark:text-amber-400" /> Sensibilidad Económica Académica</h2>
      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Sensibilidad exploratoria con ley %Cu de {model.model_name}; aporte hipotético por tonelada de referencia, sin tonelajes validados.</p></div>
      <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 font-mono text-[10px] font-bold text-amber-700 dark:text-amber-400">ESCENARIO ACADÉMICO · {price.toFixed(2)} USD/lb Cu</span>
    </div>

    <div className={card}>
      <h3 className="font-display text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">Ley media y umbral teórico por banco</h3>
      <p className="mb-4 mt-1 text-[10px] text-slate-500 dark:text-slate-400">Comparación visual del promedio simple de ley estimada con el umbral derivado de los supuestos editables; no es una ley de corte operativa.</p>
      <div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={byBench}>
        <CartesianGrid stroke={isDark ? '#334155' : '#e2e8f0'} strokeDasharray="3 3" /><XAxis dataKey="bench" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} unit="%" /><Tooltip contentStyle={tooltipStyle} /><Legend />
        <Line type="monotone" dataKey="meanGrade" name="Ley media estimada %Cu" stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 3 }} />
        {breakEvenGrade !== null && <ReferenceLine y={breakEvenGrade} stroke="#f59e0b" strokeDasharray="5 4" label="Umbral teórico" />}
      </LineChart></ResponsiveContainer></div>
    </div>

    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-2 bg-amber-500/5 px-4 py-3">
        <button type="button" onClick={() => setShowParams(value => !value)} className="flex items-center gap-2 text-left"><Settings2 className="h-4 w-4 text-amber-600 dark:text-amber-400" /><span className="font-display text-xs font-bold uppercase tracking-wider">Parámetros Económicos</span>{showParams ? <ChevronUp className="h-4 w-4 text-amber-500" /> : <ChevronDown className="h-4 w-4 text-amber-500" />}</button>
        <button type="button" onClick={() => { setPrice(defaults.price); setRecovery(defaults.recovery); setCost(defaults.cost); }} className="flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"><RotateCcw className="h-3.5 w-3.5" /> Restablecer</button>
      </div>
      {showParams && <div className="space-y-3 px-4 py-4">
      <div className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2 xl:grid-cols-4">
        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700/60 dark:bg-slate-800/30"><p className="font-display text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">Precio de metal</p><label className="space-y-1"><span className="block font-semibold">Cobre supuesto (USD/lb)</span><input type="number" min="0" max="100" step="0.1" value={price} onChange={event => setNumber(setPrice, 100)(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono dark:border-slate-700 dark:bg-slate-800" /></label><p className="text-[10px] text-slate-500">Ejemplo editable, sin cotización verificada.</p></div>
        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700/60 dark:bg-slate-800/30"><p className="font-display text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">Recuperación metalúrgica</p><label className="space-y-1"><span className="block font-semibold">Recuperación supuesta (%)</span><input type="number" min="0" max="100" step="1" value={recovery} onChange={event => setNumber(setRecovery, 100)(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono dark:border-slate-700 dark:bg-slate-800" /></label><p className="text-[10px] text-slate-500">No proviene de ensayos metalúrgicos del proyecto.</p></div>
        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700/60 dark:bg-slate-800/30"><p className="font-display text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">Costo del ejercicio</p><label className="space-y-1"><span className="block font-semibold">Costo conjunto supuesto (USD/t)</span><input type="number" min="0" max="1000" step="1" value={cost} onChange={event => setNumber(setCost, 1000)(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-mono dark:border-slate-700 dark:bg-slate-800" /></label><p className="text-[10px] text-slate-500">No desglosa minado, proceso ni transporte.</p></div>
        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700/60 dark:bg-slate-800/30"><p className="font-display text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">Nivel de análisis</p><label className="space-y-1"><span className="block font-semibold">Banco de la reconstrucción</span><select value={bench} onChange={event => setBench(event.target.value === 'ALL' ? 'ALL' : Number(event.target.value))} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-800"><option value="ALL">Todos</option>{benches.map(level => <option key={level} value={level}>{level} m</option>)}</select></label><p className="text-[10px] text-slate-500">Se calcula por cubo con soporte.</p></div>
      </div>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">Aporte ilustrativo = (ley Cu / 100) × 2 204,62 lb/t × precio supuesto × recuperación supuesta − costo supuesto. Los valores iniciales son ejemplos, no cotizaciones ni parámetros medidos de Copper Creek.</p>
      </div>}
    </div>

    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><Layers className="h-4 w-4 text-cyan-500" /> Cubos con soporte en filtro</div><div className="mt-2 font-mono text-2xl font-bold">{blocks.length.toLocaleString('es-PE')}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Promedio simple; sin tonelaje validado.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><FlaskConical className="h-4 w-4 text-emerald-500" /> Ley media estimada</div><div className="mt-2 font-mono text-2xl font-bold">{summary.meanGrade.toFixed(3)} %Cu</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Modelo {model.model_name}.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><TrendingUp className="h-4 w-4 text-amber-500" /> Umbral teórico del ejercicio</div><div className="mt-2 font-mono text-2xl font-bold">{breakEvenGrade === null ? '—' : `${breakEvenGrade.toFixed(3)} %Cu`}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Ley que hace cero el aporte por tonelada con estos supuestos.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><DollarSign className="h-4 w-4 text-indigo-500" /> Aporte medio ilustrativo</div><div className="mt-2 font-mono text-2xl font-bold">{summary.meanContribution.toFixed(2)} USD/t</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">No es beneficio, NSR ni NPV del proyecto.</p></div>
    </div>

    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className={card}><h3 className="font-display text-sm font-bold">Aporte ilustrativo medio por banco</h3><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">USD por tonelada de referencia; cada cubo pesa igual en el promedio.</p><div className="mt-4 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={byBench}><CartesianGrid stroke={isDark ? '#334155' : '#e2e8f0'} strokeDasharray="3 3" /><XAxis dataKey="bench" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} unit="$" /><Tooltip contentStyle={tooltipStyle} /><Bar dataKey="contribution" name="USD/t de referencia" fill="#0ea5e9" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div></div>
      <div className={card}><h3 className="font-display text-sm font-bold">Sensibilidad al precio supuesto</h3><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Cubos cuyo aporte ilustrativo es ≥ 0 al variar solo el precio Cu.</p><div className="mt-4 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={sensitivity}><CartesianGrid stroke={isDark ? '#334155' : '#e2e8f0'} strokeDasharray="3 3" /><XAxis dataKey="price" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip contentStyle={tooltipStyle} /><Legend /><Bar dataKey="above" name="Cubos sobre umbral teórico" fill="#10b981" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div></div>
    </div>

    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800"><h3 className="font-display text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">Detalle exploratorio por banco</h3></div>
      <div className="overflow-x-auto"><table className="w-full text-xs"><thead className="bg-slate-50 font-mono text-slate-500 dark:bg-slate-950/50 dark:text-slate-400"><tr><th className="px-4 py-2 text-left">Banco</th><th className="px-4 py-2 text-right">Cubos con soporte</th><th className="px-4 py-2 text-right">Ley media %Cu</th><th className="px-4 py-2 text-right">Sobre umbral teórico</th><th className="px-4 py-2 text-right">Aporte medio USD/t ref.</th></tr></thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">{byBench.map(row => <tr key={row.bench} className="hover:bg-slate-50 dark:hover:bg-slate-800/40"><td className="px-4 py-2 font-mono font-bold">{row.bench}m</td><td className="px-4 py-2 text-right font-mono">{row.count}</td><td className="px-4 py-2 text-right font-mono">{row.meanGrade.toFixed(3)}</td><td className="px-4 py-2 text-right font-mono">{row.above}</td><td className="px-4 py-2 text-right font-mono">{row.contribution.toFixed(2)}</td></tr>)}</tbody>
      </table></div>
    </div>

    <div className={`${card} text-xs`}><h3 className="font-display text-sm font-bold">Comparación de clasificación del ejercicio</h3><p className="mt-2">Con estos supuestos, <strong>{summary.above.toLocaleString('es-PE')}</strong> cubos quedan sobre el umbral teórico según {model.model_name}. En <strong>{summary.differentFromIdw3.toLocaleString('es-PE')}</strong> cubos, IDW3 y {model.model_name} quedan en lados distintos del umbral. Esto indica sensibilidad al estimador, no un cambio medido de destino.</p></div>
    <div className={card}>
      <h3 className="font-display text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">Metodología y supuestos</h3>
      <div className="mt-3 grid grid-cols-1 gap-3 text-[10px] leading-relaxed text-slate-500 dark:text-slate-400 md:grid-cols-3">
        <p><strong className="block text-slate-700 dark:text-slate-200">Ley utilizada</strong>{model.model_name} estima %Cu en cubos reconstruidos con soporte. Cada cubo tiene el mismo peso en los promedios.</p>
        <p><strong className="block text-slate-700 dark:text-slate-200">Aporte por tonelada de referencia</strong>Valor de Cu recuperable bajo el precio supuesto, menos un costo conjunto supuesto. No incluye créditos de otros metales ni contratos.</p>
        <p><strong className="block text-slate-700 dark:text-slate-200">Límite</strong>Sin tonelaje, recuperación y costos validados no se calcula NSR, margen total, NPV ni destino de material.</p>
      </div>
    </div>
    <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-xs leading-relaxed text-amber-900 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-200"><div className="flex items-center gap-2 font-display text-sm font-bold"><ShieldAlert className="h-4 w-4" /> Resultado académico, sin valoración del proyecto</div><p className="mt-1">No hay tonelajes, recuperaciones, costos, contratos ni secuencia de extracción validados para los cubos reconstruidos. El modelo de ley tiene RMSE de validación de {model.comparison[model.model_name].mean_rmse.toFixed(3)} %Cu y la geometría del tajo es aproximada. Estos cálculos no justifican despacho, reservas, rentabilidad ni inversión.</p></div>
  </div>;
}
