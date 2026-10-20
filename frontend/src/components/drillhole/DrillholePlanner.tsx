import { useMemo, useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Cell } from 'recharts';
import { ExportableFigure, ExportableTable } from '../shared/ExportableContent';
import { Crosshair, MapPin, Target, TrendingUp, Drill, Download, Info } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useCopperCreekStudy } from '../../hooks/useCopperCreekStudy';
import { MiningLoader } from '../shared/MiningLoader';
import type { BlockModelItem } from '../../types';

interface Candidate {
  block: BlockModelItem;
  score: number;
}

function percentile(values: number[], fraction: number): number {
  if (!values.length) return 1;
  const ordered = [...values].sort((a, b) => a - b);
  return ordered[Math.floor((ordered.length - 1) * fraction)] || 1;
}

function priorityColor(score: number): string {
  if (score >= 70) return '#ef4444';
  if (score >= 50) return '#f59e0b';
  return '#10b981';
}

const panel = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm';
const inset = 'bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3';

export function DrillholePlanner() {
  const { scene, model, error } = useCopperCreekStudy();
  const { isDark } = useTheme();
  const [plannerBench, setPlannerBench] = useState<number | 'ALL'>('ALL');
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);

  const planning = useMemo(() => {
    if (!scene || !model) return null;
    const pool = plannerBench === 'ALL' ? scene.blocks : scene.blocks.filter(block => block.bench === plannerBench);
    const spreadScale = percentile(scene.blocks.map(block => block.epistemic_unc), 0.9);
    const gradeScale = percentile(scene.blocks.map(block => block.cu_bayesian), 0.9);
    const minSupport = model.support_rule.min_holes;
    const maxSupport = model.support_rule.max_holes;
    const supportRange = Math.max(1, maxSupport - minSupport);
    const maxDistance = Math.max(1, model.support_rule.max_distance_m);
    const ranked = pool.map(block => {
      const spread = Math.min(1, block.epistemic_unc / spreadScale);
      const distance = Math.min(1, block.nearest_drillhole_m / maxDistance);
      const lowSupport = Math.max(0, Math.min(1, (maxSupport - (block.support_holes ?? minSupport)) / supportRange));
      const grade = Math.min(1, block.cu_bayesian / gradeScale);
      return { block, score: 100 * (0.4 * spread + 0.3 * distance + 0.2 * lowSupport + 0.1 * grade) };
    }).sort((a, b) => b.score - a.score);
    const recommendations: Candidate[] = [];
    for (const candidate of ranked) {
      const separate = recommendations.every(existing =>
        Math.hypot(
          candidate.block.x - existing.block.x,
          candidate.block.y - existing.block.y,
          candidate.block.z - existing.block.z,
        ) >= 80);
      if (separate) recommendations.push(candidate);
      if (recommendations.length === 10) break;
    }
    const average = (field: (block: BlockModelItem) => number) =>
      pool.length ? pool.reduce((sum, block) => sum + field(block), 0) / pool.length : 0;
    return {
      pool,
      recommendations,
      avgSpread: average(block => block.epistemic_unc),
      avgDistance: average(block => block.nearest_drillhole_m),
      lowSupportCount: pool.filter(block => (block.support_holes ?? 0) <= 4).length,
    };
  }, [scene, model, plannerBench]);

  if (error) return <div role="alert" className={panel + ' p-5 text-sm text-rose-600 dark:text-rose-400'}>{error}</div>;
  if (!scene || !model || !planning) return <MiningLoader title="Preparando el planificador" detail="Evaluando el soporte espacial de los cubos de Copper Creek." />;

  const benches = Array.from(new Set<number>(scene.blocks.map(block => Number(block.bench)))).sort((a, b) => b - a);
  const selected = planning.recommendations.find(item => item.block.id === selectedBlockId) ?? planning.recommendations[0];
  const heatMapData = planning.recommendations.map(item => ({
    x: item.block.x, y: item.block.y, z: item.score, block_id: item.block.id, bench: item.block.bench,
  }));
  const downloadRanking = () => {
    const header = 'rango,cubo,banco_m,x_m,y_m,z_m,cu_modelo_pct,dispersion_local_pct,distancia_m,sondajes_soporte,indice_revision';
    const rows = planning.recommendations.map((item, index) => [
      index + 1, item.block.id, item.block.bench, item.block.x, item.block.y, item.block.z,
      item.block.cu_bayesian.toFixed(4), item.block.epistemic_unc.toFixed(4),
      item.block.nearest_drillhole_m.toFixed(1), item.block.support_holes ?? '',
      item.score.toFixed(1),
    ].join(','));
    const csv = [header, ...rows].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'copper_creek_zonas_revision.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return <div className="space-y-4 sm:space-y-6">
    <div className={panel + ' p-4 sm:p-5 flex flex-wrap items-center justify-between gap-3'}>
      <div>
        <h2 className="text-sm sm:text-base font-bold font-display flex items-center gap-2"><Crosshair className="w-5 h-5 text-amber-600 dark:text-amber-400" /> Zonas para Revisar Sondajes · Copper Creek</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{model.model_name} publicado · {planning.pool.length.toLocaleString('es-PE')} cubos evaluados · priorización académica de zonas</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Banco:
          <select value={plannerBench} onChange={event => { setPlannerBench(event.target.value === 'ALL' ? 'ALL' : Number(event.target.value)); setSelectedBlockId(null); }}
            className="ml-2 px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-800 dark:text-slate-200">
            <option value="ALL">Todos</option>{benches.map(bench => <option key={bench} value={bench}>{bench} m</option>)}
          </select>
        </label>
        <button type="button" onClick={downloadRanking} disabled={!planning.recommendations.length}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 text-[11px] font-semibold disabled:opacity-40"><Download className="w-3.5 h-3.5" /> Descargar ranking</button>
      </div>
    </div>

    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {[
        { icon: TrendingUp, label: 'Dispersión local media', value: planning.avgSpread.toFixed(3) + ' %Cu', hint: 'variación entre ensayes vecinos' },
        { icon: MapPin, label: 'Distancia media', value: planning.avgDistance.toFixed(0) + ' m', hint: 'a la muestra más cercana' },
        { icon: Target, label: 'Índice máximo', value: planning.recommendations[0]?.score.toFixed(1) ?? '—', hint: 'escala relativa de 0 a 100' },
        { icon: Drill, label: 'Zonas a revisar', value: String(planning.recommendations.length), hint: planning.lowSupportCount + ' cubos con ≤4 sondajes de soporte' },
      ].map(kpi => <div key={kpi.label} className={panel + ' p-4'}>
        <div className="flex items-center gap-2 mb-2"><kpi.icon className="w-4 h-4 text-amber-500" /><span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">{kpi.label}</span></div>
        <div className="text-lg font-bold font-mono">{kpi.value}</div>
        <div className="text-[10px] text-slate-400 font-mono mt-1">{kpi.hint}</div>
      </div>)}
    </div>

    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
      <div className={panel + ' lg:col-span-2 p-4 sm:p-5'}>
        <h3 className="text-xs font-bold uppercase font-display tracking-wider mb-4 flex items-center gap-1.5"><Target className="w-3.5 h-3.5 text-amber-500" /> Mapa de zonas para revisión (UTM)</h3>
        <ExportableFigure title="Mapa de zonas para revisión" filename="copper-creek-zonas-revision" interpretation={`Se visualizan ${heatMapData.length} cubos del filtro. El color codifica un índice de prioridad académica, no ubicaciones aprobadas para perforación.`}>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#cbd5e1'} opacity={0.5} />
              <XAxis type="number" dataKey="x" name="X" tick={{ fontSize: 11 }} tickFormatter={value => (value / 1000).toFixed(1) + 'k'} />
              <YAxis type="number" dataKey="y" name="Y" tick={{ fontSize: 11 }} tickFormatter={value => (value / 1000).toFixed(1) + 'k'} />
              <ZAxis type="number" dataKey="z" range={[80, 260]} />
              <Tooltip contentStyle={{ backgroundColor: isDark ? '#0f172a' : '#ffffff', border: '1px solid #334155', borderRadius: '12px', fontSize: '12px' }}
                labelFormatter={(_, payload) => payload?.[0] ? payload[0].payload.block_id + ' · Banco ' + payload[0].payload.bench + ' m' : ''}
                formatter={value => [Number(value).toFixed(1), 'Índice de revisión']} />
              <Scatter data={heatMapData} onClick={point => { if (point?.block_id) setSelectedBlockId(point.block_id); }}>
                {heatMapData.map(item => <Cell key={item.block_id} fill={priorityColor(item.z)} />)}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        </ExportableFigure>
        <div className="flex flex-wrap justify-center gap-4 mt-2 text-[10px] font-mono text-slate-500">
          <span>🟢 Menor (&lt;50)</span><span>🟠 Media (50–70)</span><span>🔴 Mayor (&gt;70)</span>
        </div>
      </div>

      <div className={panel + ' p-4 sm:p-5'}>
        <h3 className="text-xs font-bold uppercase font-display tracking-wider mb-4 flex items-center gap-1.5"><Target className="w-3.5 h-3.5 text-amber-500" /> Detalle seleccionado</h3>
        {selected ? <div className="space-y-3">
          <div className="flex items-center justify-between gap-2"><strong className="text-sm font-mono text-amber-600 dark:text-amber-400">{selected.block.id}</strong><span className="text-[10px] font-mono">Índice {selected.score.toFixed(1)}</span></div>
          <div className="bg-gradient-to-br from-amber-500/15 to-amber-500/5 border border-amber-500/40 rounded-xl p-4 text-center">
            <div className="text-[10px] uppercase font-bold text-amber-700 dark:text-amber-400">Zona de revisión conceptual</div>
            <div className="text-2xl font-black font-mono text-amber-600 dark:text-amber-400 mt-1">{selected.block.bench} m</div>
            <div className="text-[10px] mt-1">Banco del cubo · sin collar ni profundidad diseñada</div>
          </div>
          <div className="space-y-2 text-xs">
            {[
              ['X / Y / Z', selected.block.x.toFixed(1) + ' / ' + selected.block.y.toFixed(1) + ' / ' + selected.block.z.toFixed(1) + ' m'],
              ['Ley Cu · ' + model.model_name, selected.block.cu_bayesian.toFixed(4) + ' %'],
              ['Referencia IDW3', (selected.block.cu_idw3 ?? selected.block.cu_base).toFixed(4) + ' %'],
              ['Dispersión local', selected.block.epistemic_unc.toFixed(4) + ' %'],
              ['Muestra más cercana', selected.block.nearest_drillhole_m.toFixed(1) + ' m'],
              ['Sondajes de soporte', String(selected.block.support_holes ?? '—')],
            ].map(([label, value]) => <div key={label} className="flex justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-1"><span className="text-slate-500">{label}:</span><span className="font-mono text-right">{value}</span></div>)}
          </div>
          <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3 text-[11px] text-amber-800 dark:text-amber-300">
            La prioridad combina dispersión local (40 %), distancia a la muestra (30 %), pocos sondajes de soporte (20 %) y ley estimada (10 %). Es un índice de revisión, no una propuesta de perforación lista para ejecutar.
          </div>
        </div> : <p className="text-xs text-slate-500 text-center py-8">No hay cubos en este banco.</p>}
      </div>
    </div>

    <div className={panel + ' overflow-hidden'}>
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800">
        <h3 className="text-xs font-bold uppercase font-display tracking-wider flex items-center gap-1.5"><Target className="w-3.5 h-3.5 text-amber-500" /> Ranking de zonas a revisar ({planning.recommendations.length})</h3>
        <p className="mt-1 text-[10px] text-slate-500">Máximo 10 cubos separados al menos 80 m en 3D. El ranking no genera un sondaje, ensaye ni clasificación de recursos.</p>
      </div>
      <ExportableTable title="Ranking de zonas a revisar" filename="copper-creek-ranking-zonas" interpretation={`El ranking presenta ${planning.recommendations.length} cubos candidatos separados espacialmente. No constituye un plan de sondajes ejecutable.`} className="px-3 pb-3">
      <div className="overflow-x-auto"><table className="w-full text-xs">
        <thead className="bg-slate-50 dark:bg-slate-950/50 text-slate-500 dark:text-slate-400 font-mono"><tr>
          <th className="px-4 py-2 text-left">#</th><th className="px-4 py-2 text-left">Cubo</th><th className="px-4 py-2 text-right">Banco</th>
          <th className="px-4 py-2 text-right">Cu {model.model_name}</th><th className="px-4 py-2 text-right">Dispersión</th>
          <th className="px-4 py-2 text-right">Distancia</th><th className="px-4 py-2 text-right">Soporte</th><th className="px-4 py-2 text-right">Índice</th>
        </tr></thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {planning.recommendations.map((item, index) => <tr key={item.block.id} onClick={() => setSelectedBlockId(item.block.id)}
            className={'hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer ' + (selected?.block.id === item.block.id ? 'bg-amber-50 dark:bg-amber-950/20' : '')}>
            <td className="px-4 py-2 font-mono font-bold text-amber-600 dark:text-amber-400">{index + 1}</td>
            <td className="px-4 py-2 font-mono">{item.block.id}</td><td className="px-4 py-2 text-right font-mono">{item.block.bench} m</td>
            <td className="px-4 py-2 text-right font-mono text-emerald-600">{item.block.cu_bayesian.toFixed(4)} %</td>
            <td className="px-4 py-2 text-right font-mono">{item.block.epistemic_unc.toFixed(4)} %</td>
            <td className="px-4 py-2 text-right font-mono">{item.block.nearest_drillhole_m.toFixed(1)} m</td>
            <td className="px-4 py-2 text-right font-mono">{item.block.support_holes ?? '—'}</td>
            <td className="px-4 py-2 text-right font-mono font-bold" style={{ color: priorityColor(item.score) }}>{item.score.toFixed(1)}</td>
          </tr>)}
        </tbody>
      </table></div>
      </ExportableTable>
      {!planning.recommendations.length && <div className="p-4 text-xs text-slate-500 flex items-center gap-2"><Info className="w-4 h-4" /> Sin zonas candidatas en este banco.</div>}
    </div>
  </div>;
}

