import { useMemo } from 'react';
import { Activity, BarChart3, Database, FlaskConical, Scale, ShieldAlert } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCopperCreekStudy } from '../../hooks/useCopperCreekStudy';
import { useTheme } from '../../context/ThemeContext';
import { MiningLoader } from '../shared/MiningLoader';
import { ExportableFigure, ExportableTable } from '../shared/ExportableContent';

const card = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm';

export function ReconciliationDashboard() {
  const { scene, model, error } = useCopperCreekStudy();
  const { isDark } = useTheme();
  const comparison = useMemo(() => model ? Object.keys(model.comparison)
    .map(name => ({ name, ...model.comparison[name] }))
    .sort((a, b) => a.mean_rmse - b.mean_rmse) : [], [model]);

  if (error) return <div role="alert" className="rounded-xl border border-rose-400 p-4 text-sm text-rose-700 dark:text-rose-300">{error}</div>;
  if (!scene || !model) return <MiningLoader title="Preparando la validación" detail="Comparando estimadores con sondajes completos reservados." />;

  const winner = model.comparison[model.model_name];
  const baseline = model.comparison.IDW3;
  const improvement = baseline.mean_rmse > 0 ? (baseline.mean_rmse - winner.mean_rmse) / baseline.mean_rmse * 100 : 0;
  const tested = winner.folds.reduce((sum, fold) => sum + fold.test_samples, 0);
  const supported = winner.folds.reduce((sum, fold) => sum + fold.supported_samples, 0);
  const foldSeries = winner.folds.map((fold, index) => ({
    group: `Grupo ${fold.fold}`,
    winner: fold.rmse,
    baseline: baseline.folds[index]?.rmse ?? 0,
    holes: fold.test_holes,
    supported: fold.supported_samples,
    tested: fold.test_samples,
  }));
  const tooltipStyle = {
    backgroundColor: isDark ? '#0f172a' : '#fff',
    borderColor: isDark ? '#334155' : '#cbd5e1',
    color: isDark ? '#f8fafc' : '#0f172a',
    borderRadius: 10,
  };

  return <div className="space-y-4 sm:space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div><h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2"><Scale className="h-5 w-5 text-amber-600 dark:text-amber-400" /> Validación de Leyes por Sondajes</h2>
      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Copper Creek · comparación de estimadores con ensayos de sondajes completos no vistos.</p></div>
      <span className="flex items-center gap-1 rounded-full border border-cyan-500/30 bg-cyan-500/15 px-2.5 py-1 font-mono text-[10px] font-bold text-cyan-700 dark:text-cyan-400">Motor IA: {model.model_name}</span>
    </div>

    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><FlaskConical className="h-4 w-4 text-emerald-500" /> Modelo seleccionado</div><div className="mt-2 font-display text-xl font-bold text-emerald-700 dark:text-emerald-400">{model.model_name}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Menor RMSE medio en cinco grupos.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><Activity className="h-4 w-4 text-cyan-500" /> RMSE de validación</div><div className="mt-2 font-mono text-2xl font-bold">{winner.mean_rmse.toFixed(3)} %Cu</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{improvement.toFixed(1)} % menor que IDW3 en promedio.</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><Database className="h-4 w-4 text-indigo-500" /> Ensayos evaluados con soporte</div><div className="mt-2 font-mono text-2xl font-bold">{supported.toLocaleString('es-PE')}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">De {tested.toLocaleString('es-PE')} composites reservados ({(supported / tested * 100).toFixed(1)} %).</p></div>
      <div className={card}><div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><BarChart3 className="h-4 w-4 text-amber-500" /> Cobertura de cubos</div><div className="mt-2 font-mono text-2xl font-bold">{scene.blocks.length.toLocaleString('es-PE')}</div><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{scene.metadata.skipped_unsupported_blocks.toLocaleString('es-PE')} candidatos omitidos sin soporte.</p></div>
    </div>

    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className={card}>
        <h3 className="font-display text-sm font-bold">RMSE por grupo de sondajes no vistos</h3>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Ambos estimadores se evalúan sobre los mismos composites con soporte.</p>
        <ExportableFigure title="RMSE por grupo de sondajes" filename="copper-creek-rmse-grupos" interpretation={`${model.model_name} presenta ${winner.mean_rmse.toFixed(3)} %Cu de RMSE medio frente a ${baseline.mean_rmse.toFixed(3)} %Cu de IDW3 en los grupos de sondajes reservados.`}>
        <div className="mt-4 h-72"><ResponsiveContainer width="100%" height="100%"><LineChart data={foldSeries}><CartesianGrid stroke={isDark ? '#334155' : '#e2e8f0'} strokeDasharray="3 3" /><XAxis dataKey="group" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} unit="%" /><Tooltip contentStyle={tooltipStyle} /><Legend /><Line type="monotone" dataKey="winner" name={model.model_name} stroke="#10b981" strokeWidth={2.5} dot={{ r: 4 }} /><Line type="monotone" dataKey="baseline" name="IDW3" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} /></LineChart></ResponsiveContainer></div>
        </ExportableFigure>
      </div>
      <div className={card}>
        <h3 className="font-display text-sm font-bold">Comparación de estimadores</h3>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Promedio de las cinco particiones por sondaje; menor RMSE y MAE es mejor.</p>
        <ExportableTable title="Comparación de estimadores" filename="copper-creek-comparacion-estimadores" interpretation={`${model.model_name} tiene el menor RMSE medio entre ${comparison.length} estimadores evaluados. Las métricas corresponden a sondajes reservados, no a una reconciliación de planta.`}>
        <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400"><tr><th className="py-2">Modelo</th><th className="py-2 text-right">RMSE %Cu</th><th className="py-2 text-right">MAE %Cu</th><th className="py-2 text-right">R² medio</th></tr></thead><tbody>{comparison.map(row => <tr key={row.name} className="border-b border-slate-100 dark:border-slate-800"><td className="py-3 font-semibold">{row.name}{row.name === model.model_name ? ' · seleccionado' : ''}</td><td className="py-3 text-right font-mono">{row.mean_rmse.toFixed(3)}</td><td className="py-3 text-right font-mono">{row.mean_mae.toFixed(3)}</td><td className="py-3 text-right font-mono">{row.mean_r2.toFixed(3)}</td></tr>)}</tbody></table></div>
        </ExportableTable>
        <p className="mt-4 text-xs leading-relaxed text-slate-600 dark:text-slate-300">{model.hole_count} sondajes y {model.sample_count.toLocaleString('es-PE')} composites de estudio. La validación reserva pozos completos para que muestras del mismo pozo no aparezcan a la vez en entrenamiento y prueba.</p>
      </div>
    </div>

    <div className={card}>
      <h3 className="font-display text-sm font-bold">Detalle de la validación por grupo</h3>
      <ExportableTable title="Validación por grupo" filename="copper-creek-validacion-grupos" interpretation={`La tabla muestra ${foldSeries.length} grupos de sondajes completos reservados. Se comparan los errores sobre composites con soporte del mismo grupo.`}>
      <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400"><tr><th className="py-2">Grupo</th><th className="py-2 text-right">Sondajes</th><th className="py-2 text-right">Composites con soporte</th><th className="py-2 text-right">RMSE {model.model_name}</th><th className="py-2 text-right">RMSE IDW3</th></tr></thead><tbody>{foldSeries.map(row => <tr key={row.group} className="border-b border-slate-100 dark:border-slate-800"><td className="py-2">{row.group}</td><td className="py-2 text-right font-mono">{row.holes}</td><td className="py-2 text-right font-mono">{row.supported} / {row.tested}</td><td className="py-2 text-right font-mono">{row.winner.toFixed(3)}</td><td className="py-2 text-right font-mono">{row.baseline.toFixed(3)}</td></tr>)}</tbody></table></div>
      </ExportableTable>
    </div>

    <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-xs leading-relaxed text-cyan-900 dark:border-cyan-900 dark:bg-cyan-950/20 dark:text-cyan-200"><div className="flex items-center gap-2 font-display text-sm font-bold"><ShieldAlert className="h-4 w-4" /> Alcance de la validación</div><p className="mt-1">Estas métricas miden el error frente a ensayos reservados de sondajes. Una futura reconciliación Mine-to-Mill necesitaría leyes de alimentación de planta, toneladas y fechas de extracción enlazadas a los mismos cubos. Esas mediciones no están en los archivos públicos.</p></div>
  </div>;
}
