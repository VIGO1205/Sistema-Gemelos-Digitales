import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, FlaskConical, RefreshCw } from 'lucide-react';
import { MiningLoader } from '../shared/MiningLoader';
import {
  drillholeExperimentApi,
  type DrillholeExperimentMetadata,
  type DrillholePointPrediction,
} from '../../services/api';

type Axis = 'x' | 'y' | 'z';
const axes: Axis[] = ['x', 'y', 'z'];

function apiError(error: unknown): string {
  const response = (error as { response?: { status?: number; data?: { detail?: string } } })?.response;
  if (response?.status === 404) return 'Aún no hay un modelo exploratorio publicado. Entrénalo y publícalo en la Fase 6 del Motor IA.';
  return response?.data?.detail || 'No se pudo consultar el servicio de inferencia. Comprueba que el Motor IA esté en ejecución.';
}

export function DrillholeExperimentView() {
  const [metadata, setMetadata] = useState<DrillholeExperimentMetadata | null>(null);
  const [point, setPoint] = useState<Record<Axis, string>>({ x: '', y: '', z: '' });
  const [prediction, setPrediction] = useState<DrillholePointPrediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await drillholeExperimentApi.info();
      const model = response.data.model;
      setMetadata(model);
      setPoint({
        x: String(model.coordinate_bounds.x.median),
        y: String(model.coordinate_bounds.y.median),
        z: String(model.coordinate_bounds.z.median),
      });
      setPrediction(null);
    } catch (cause) {
      setMetadata(null);
      setError(apiError(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const predict = async () => {
    if (!metadata) return;
    const coordinates = { x: Number(point.x), y: Number(point.y), z: Number(point.z) };
    if (axes.some(axis => point[axis].trim() === '' || !Number.isFinite(coordinates[axis]))) {
      setError('Ingresa valores numéricos para X, Y y Z.');
      return;
    }
    for (const axis of axes) {
      const limits = metadata.coordinate_bounds[axis];
      if (coordinates[axis] < limits.min || coordinates[axis] > limits.max) {
        setError(`${axis.toUpperCase()} debe estar entre ${limits.min.toFixed(2)} y ${limits.max.toFixed(2)}.`);
        return;
      }
    }
    setPredicting(true);
    setError(null);
    setPrediction(null);
    try {
      const response = await drillholeExperimentApi.predict(coordinates);
      setPrediction(response.data);
    } catch (cause) {
      setError(apiError(cause));
    } finally {
      setPredicting(false);
    }
  };

  if (loading) return <MiningLoader title="Preparando Sondajes GeoMet" detail="Consultando el modelo exploratorio publicado y sus límites de coordenadas." />;

  return (
    <section className="space-y-5 max-w-6xl mx-auto">
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2"><FlaskConical className="w-5 h-5 text-amber-500" /> Sondajes GeoMet</h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">Experimento espacial de ley de cobre con datos públicos de sondajes.</p>
          </div>
          <button type="button" onClick={() => void refresh()} disabled={loading} className="flex items-center gap-2 rounded-xl border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50">
            <RefreshCw className="w-4 h-4" /> Actualizar estado
          </button>
        </div>
        <p className="text-xs text-amber-800 dark:text-amber-300 mt-3">Este experimento no pertenece a los bancos del proyecto del dashboard. No calcula tonelaje, recursos ni reconciliación con planta.</p>
      </div>

      {error && <div role="alert" className="rounded-2xl border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/20 p-4 text-sm text-rose-800 dark:text-rose-300 flex items-start gap-2"><AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />{error}</div>}

      {metadata && !loading && <>
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
          <div className="flex flex-wrap justify-between gap-2">
            <div>
              <h3 className="font-bold text-lg">{metadata.model_name}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{metadata.sample_count.toLocaleString()} muestras en el CSV · validación en {metadata.validation}</p>
            </div>
            <span className="text-xs text-slate-500 dark:text-slate-400">Publicado: {new Date(metadata.exported_at).toLocaleString()}</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {([['RMSE', metadata.metrics.rmse, '% Cu'], ['MAE', metadata.metrics.mae, '% Cu'], ['R²', metadata.metrics.r2, '']] as const).map(([label, value, unit]) => (
              <div key={label} className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
                <p className="text-xs text-slate-500 dark:text-slate-400">{label} en sondajes reservados</p>
                <p className="text-xl font-bold mt-1">{value.toFixed(4)} <span className="text-xs font-normal">{unit}</span></p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">El modelo usa solo X/Y/Z. Su error de prueba no garantiza precisión en un yacimiento distinto ni fuera de la zona muestreada.</p>
        </div>

        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
          <div>
            <h3 className="font-bold flex items-center gap-2"><Activity className="w-5 h-5 text-cyan-500" /> Consultar un punto X/Y/Z</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Usa el mismo sistema local de coordenadas del CSV GeoMet. Su referencia geográfica no está documentada.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {axes.map(axis => {
              const bounds = metadata.coordinate_bounds[axis];
              return <label key={axis} className="text-sm font-medium">
                {axis.toUpperCase()}
                <input type="number" step="any" value={point[axis]} onChange={event => { setPoint(current => ({ ...current, [axis]: event.target.value })); setPrediction(null); }} className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2" />
                <span className="block text-xs font-normal text-slate-500 dark:text-slate-400 mt-1">Rango: {bounds.min.toFixed(2)} a {bounds.max.toFixed(2)}</span>
              </label>;
            })}
          </div>
          <button type="button" onClick={() => void predict()} disabled={predicting} className="rounded-xl bg-amber-500 hover:bg-amber-600 disabled:opacity-50 px-4 py-2 font-bold text-slate-950 text-sm">
            {predicting ? 'Calculando…' : 'Estimar Cu en este punto'}
          </button>
          {prediction && <div aria-live="polite" className={`rounded-xl p-4 ${prediction.plausible ? 'bg-cyan-50 dark:bg-cyan-950/20 text-cyan-900 dark:text-cyan-200' : 'bg-rose-50 dark:bg-rose-950/20 text-rose-900 dark:text-rose-200'}`}>
            <p className="text-xs">{prediction.model_name} · predicción exploratoria</p>
            <p className="text-2xl font-bold my-1">{prediction.predicted_cu_pct.toFixed(4)} % Cu</p>
            <p className="text-xs">{prediction.message}</p>
          </div>}
        </div>
      </>}
    </section>
  );
}
