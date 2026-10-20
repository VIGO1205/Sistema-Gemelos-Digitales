import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, BrainCircuit, Cpu, Layers, Sliders } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTheme } from '../../context/ThemeContext';
import { useCopperCreekStudy, type CopperCreekModelMetadata } from '../../hooks/useCopperCreekStudy';
import api from '../../services/api';
import { BlockQualityGallery3D, type CubeQuality, type QualityBlock } from './BlockQuality3D';
import { MiningLoader } from '../shared/MiningLoader';
import { ExportableFigure } from '../shared/ExportableContent';

type Tab = 'MODELS_OVERVIEW' | 'INTERACTIVE_INFERENCE' | 'SCENARIO_COMPARISON';
type Point = { x: number; y: number; z: number };
type Prediction = { model_name: string; predicted_cu_pct: number; support_holes: number; nearest_hole_m: number };
const panel = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm';
const inset = 'bg-slate-50 dark:bg-slate-950 p-3 rounded-xl border border-slate-200 dark:border-slate-800';

export const BayesianInferenceEngine: React.FC<{ onOpenViewer: () => void }> = ({ onOpenViewer }) => {
  const { isDark } = useTheme();
  const { scene, model, error } = useCopperCreekStudy();
  const [activeTab, setActiveTab] = useState<Tab>('MODELS_OVERVIEW');
  const [activeQuality, setActiveQuality] = useState<CubeQuality | null>(null);
  const [point, setPoint] = useState<Point | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predictError, setPredictError] = useState<string | null>(null);
  const [predicting, setPredicting] = useState(false);
  const requestId = useRef(0);

  const qualityItems = useMemo<QualityBlock[]>(() => {
    if (!scene?.blocks.length) return [];
    const sorted = [...scene.blocks].sort((a, b) => a.cu_bayesian - b.cu_bayesian);
    const middle = sorted.reduce((best, block) => Math.abs(block.cu_bayesian - 0.35) < Math.abs(best.cu_bayesian - 0.35) ? block : best, sorted[0]);
    return [
      { quality: 'BUENO', block: sorted[sorted.length - 1] },
      { quality: 'REGULAR', block: middle },
      { quality: 'NO_SIRVE', block: sorted[0] },
    ];
  }, [scene]);

  useEffect(() => {
    if (!point && scene?.blocks.length) {
      const block = scene.blocks[0];
      setPoint({ x: block.x, y: block.y, z: block.z });
    }
  }, [point, scene]);

  const comparisons = useMemo(() => model ? Object.entries(model.comparison)
    .map(([name, result]) => ({ name, ...(result as CopperCreekModelMetadata['comparison'][string]) }))
    .sort((a, b) => a.mean_rmse - b.mean_rmse) : [], [model]);

  const histogram = useMemo(() => {
    if (!scene) return [];
    const bins = new Map<number, number>();
    scene.blocks.forEach(block => {
      const bin = Math.min(10, Math.floor(block.cu_bayesian * 10));
      bins.set(bin, (bins.get(bin) ?? 0) + 1);
    });
    return Array.from(bins, ([bin, count]) => ({ bin: bin === 10 ? '≥1.0' : (bin / 10).toFixed(1), count }))
      .sort((a, b) => Number.parseFloat(a.bin.replace('≥', '')) - Number.parseFloat(b.bin.replace('≥', '')));
  }, [scene]);

  const selectQuality = (quality: CubeQuality | null) => {
    setActiveQuality(quality);
    const block = qualityItems.find(item => item.quality === quality)?.block;
    if (block) {
      requestId.current++;
      setPredicting(false);
      setPoint({ x: block.x, y: block.y, z: block.z });
      setPrediction(null);
      setPredictError(null);
    }
  };
  const changeCoordinate = (axis: keyof Point, raw: string) => {
    const value = Number(raw);
    if (!Number.isFinite(value)) return;
    requestId.current++;
    setPredicting(false);
    setPoint(current => current ? { ...current, [axis]: value } : current);
    setPrediction(null);
    setPredictError(null);
  };
  const predict = async () => {
    if (!point || !model) return;
    const id = ++requestId.current;
    setPredicting(true);
    setPredictError(null);
    setPrediction(null);
    try {
      const response = await api.post<Prediction>('/api/copper-creek/predict', point);
      if (id !== requestId.current) return;
      if (response.data.model_name !== model.model_name) setPredictError('FastAPI respondió con otro modelo.');
      else setPrediction(response.data);
    } catch (failure: unknown) {
      if (id !== requestId.current) return;
      const detail = failure as { response?: { data?: { detail?: string } }; message?: string };
      setPredictError(detail.response?.data?.detail || detail.message || 'No se pudo consultar FastAPI.');
    } finally {
      if (id === requestId.current) setPredicting(false);
    }
  };

  if (error) return <div role="alert" className={panel + ' text-rose-600'}>{error}</div>;
  if (!scene || !model || !point) return <MiningLoader title="Preparando el Motor IA" detail="Cargando el modelo publicado, los sondajes y la validación de Copper Creek." />;

  const reference = comparisons.find(item => item.name.toLowerCase().includes('idw'));
  const alternative = comparisons.find(item => item.name !== model.model_name && item.name !== reference?.name);
  const selectedCube = scene.blocks.find(block => block.x === point.x && block.y === point.y && block.z === point.z);
  const cards = [
    { name: model.model_name, tag: 'Seleccionado', title: 'a) Estimador publicado', description: 'Predice %Cu a partir de X/Y/Z y del soporte de sondajes. Se eligió por el menor RMSE medio.', color: 'text-amber-600 dark:text-amber-400' },
    { name: reference?.name ?? 'IDW3', tag: 'Referencia espacial', title: 'b) Interpolación IDW3', description: 'Promedia leyes de ensayos vecinos según su distancia. Es la referencia del visor 3D.', color: 'text-emerald-600 dark:text-emerald-400' },
    { name: alternative?.name ?? 'XGBoost', tag: 'Candidato evaluado', title: 'c) Modelo alternativo', description: 'Se comparó reservando sondajes completos con el mismo criterio de soporte.', color: 'text-cyan-600 dark:text-cyan-400' },
  ];
  const chartGrid = isDark ? '#1e293b' : '#e2e8f0';
  const chartText = isDark ? '#94a3b8' : '#64748b';

  return <div className="space-y-4 sm:space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-3 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex items-center gap-2"><BrainCircuit className="w-5 h-5 text-amber-500" />
        <h2 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 font-display uppercase tracking-wide">
          Modelo IA · Información y consulta de ley
          <span className="ml-2 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[9px] text-slate-500 dark:text-slate-400 font-mono font-bold normal-case">Copper Creek · {model.model_name}</span>
        </h2>
      </div>
      <div className="flex flex-wrap items-center gap-1 bg-slate-100 dark:bg-slate-950 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
        {([['MODELS_OVERVIEW', 'Modelos evaluados'], ['INTERACTIVE_INFERENCE', 'Consulta de ley'], ['SCENARIO_COMPARISON', 'Escenarios']] as const)
          .map(([tab, label]) => <button type="button" key={tab} onClick={() => setActiveTab(tab)}
            className={'px-3 py-1.5 rounded-lg font-medium transition-all ' + (activeTab === tab ? 'bg-amber-500 text-slate-950 font-bold shadow-sm' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800')}>{label}</button>)}
      </div>
    </div>

    {activeTab === 'MODELS_OVERVIEW' && <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
      {cards.map(card => {
        const metrics = model.comparison[card.name];
        return <div key={card.name} className={panel + ' space-y-4 relative overflow-hidden'}>
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <span className={'px-2.5 py-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-mono font-bold ' + card.color}>{card.name}</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">{card.tag}</span>
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">{card.title}</h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">{card.description}</p>
          <div className={inset + ' space-y-1.5 text-xs font-mono text-slate-700 dark:text-slate-300'}>
            <div className={card.color + ' font-bold'}>Validación por sondajes completos</div>
            <div>RMSE: {metrics?.mean_rmse.toFixed(3) ?? '—'} %Cu</div>
            <div>MAE: {metrics?.mean_mae.toFixed(3) ?? '—'} %Cu</div>
          </div>
        </div>;
      })}
      <div className={panel + ' md:col-span-3'}>
        <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2 mb-3"><Layers className="w-4 h-4 text-amber-500" /> Datos y límites del estudio</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          {[
            ['Sondajes', model.hole_count + ' sondajes públicos y ' + model.sample_count.toLocaleString('es-PE') + ' composites.'],
            ['Entradas', model.features.join(', ')],
            ['Salida', model.target + ' estimado en el centro del cubo.'],
            ['Soporte', 'Mínimo ' + model.support_rule.min_holes + ' sondajes a ≤ ' + model.support_rule.max_distance_m + ' m.'],
            ['Validación', model.validation],
            ['Alcance', 'Reconstrucción académica, sin reservas ni decisión operativa de despacho.'],
          ].map(([title, detail]) => <div key={title} className={inset}><span className="font-bold text-amber-600 dark:text-amber-400">{title}</span><p className="text-slate-600 dark:text-slate-300 mt-1">{detail}</p></div>)}
        </div>
      </div>
    </div>}

    {activeTab === 'INTERACTIVE_INFERENCE' && <>
      <BlockQualityGallery3D isDark={isDark} activeQuality={activeQuality} onSelect={selectQuality} items={qualityItems} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className={panel + ' space-y-4'}>
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2"><Sliders className="w-4 h-4 text-amber-500" /> Coordenadas de consulta</h3>
          <p className="text-xs text-slate-600 dark:text-slate-300">Centro de un cubo o punto X/Y/Z en EPSG:32612. FastAPI comprueba límites y soporte.</p>
          <div className="space-y-3 text-xs">
            {(['x', 'y', 'z'] as const).map(axis => <label key={axis} className="block"><span className="block font-medium text-slate-700 dark:text-slate-300 mb-1">{axis.toUpperCase()} (m)</span>
              <input type="number" step="0.1" value={point[axis]} onChange={event => changeCoordinate(axis, event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-mono dark:border-slate-800 dark:bg-slate-950" /></label>)}
            <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
              <span className="text-[10px] text-slate-500 dark:text-slate-400 block mb-1 font-mono">Cubo objetivo:</span>
              <div className="p-2 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800 flex justify-between items-center text-xs">
                <span className="font-mono font-bold text-amber-600 dark:text-amber-400">{selectedCube?.id ?? 'Punto libre'}</span>
                <span className="text-slate-500">{selectedCube ? 'Banco ' + selectedCube.bench + 'm' : 'Sin cubo exacto'}</span>
              </div>
            </div>
            <button type="button" onClick={predict} disabled={predicting} className="rounded-xl bg-amber-500 px-4 py-2 font-bold text-slate-950 disabled:opacity-50">{predicting ? 'Consultando…' : 'Predecir %Cu con FastAPI'}</button>
            {predictError && <p role="alert" className="text-rose-600">{predictError}</p>}
          </div>
        </div>
        <div className={panel + ' lg:col-span-2 space-y-4 flex flex-col'}>
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            <div><h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display">Distribución de ley estimada en cubos reconstruidos</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{scene.blocks.length.toLocaleString('es-PE')} cubos con soporte · distribución espacial, no posterior bayesiano</p></div>
            {prediction && <span className="px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/40 text-xs font-mono font-bold">{prediction.predicted_cu_pct.toFixed(4)} %Cu</span>}
          </div>
          <ExportableFigure title="Distribución de ley estimada" filename="copper-creek-distribucion-motor" interpretation={`El histograma agrupa ${scene.blocks.length.toLocaleString('es-PE')} cubos estimados con soporte. No representa una distribución posterior bayesiana.`}>
          <div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={histogram} margin={{ top: 10, right: 10, left: -15, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} /><XAxis dataKey="bin" stroke={chartText} tick={{ fontSize: 10 }} /><YAxis stroke={chartText} tick={{ fontSize: 10 }} />
            <Tooltip contentStyle={{ backgroundColor: isDark ? '#0f172a' : '#ffffff', borderColor: chartGrid, color: isDark ? '#f8fafc' : '#0f172a' }} />
            <Bar dataKey="count" name="Cubos" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart></ResponsiveContainer></div>
          </ExportableFigure>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs">
            <div className={inset}><span className="text-[10px] text-slate-500 block">Modelo publicado</span><span className="font-mono font-bold text-amber-600 dark:text-amber-400">{prediction?.model_name ?? model.model_name}</span></div>
            <div className={inset}><span className="text-[10px] text-slate-500 block">Sondajes de soporte</span><span className="font-mono font-bold text-cyan-600 dark:text-cyan-400">{prediction?.support_holes ?? selectedCube?.support_holes ?? '—'}</span></div>
            <div className={inset}><span className="text-[10px] text-slate-500 block">Sondaje más cercano</span><span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">{prediction ? prediction.nearest_hole_m.toFixed(1) : selectedCube?.nearest_drillhole_m.toFixed(1) ?? '—'} m</span></div>
          </div>
          {prediction && selectedCube && <p className="text-xs text-slate-500">Comparación con escena: {Math.abs(prediction.predicted_cu_pct - selectedCube.cu_bayesian) < 0.0002 ? 'coincide con el cubo publicado.' : 'difiere; revisar versión publicada.'}</p>}
        </div>
      </div>
    </>}

    {activeTab === 'SCENARIO_COMPARISON' && <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
      {[
        { name: reference?.name ?? 'IDW3', title: 'Escenario A: Referencia IDW3', border: 'border-amber-300 dark:border-amber-500/30', color: 'text-amber-600 dark:text-amber-400' },
        { name: model.model_name, title: 'Escenario B: ' + model.model_name + ' publicado', border: 'border-emerald-300 dark:border-emerald-500/40', color: 'text-emerald-600 dark:text-emerald-400' },
      ].map(item => {
        const metrics = model.comparison[item.name];
        return <div key={item.name} className={'bg-white dark:bg-slate-900 border ' + item.border + ' rounded-2xl p-5 space-y-4 shadow-sm'}>
          <h3 className={'text-sm font-bold font-display flex items-center gap-2 ' + item.color}><Activity className="w-4 h-4" />{item.title}</h3>
          <div className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
            {[
              ['RMSE medio', metrics ? metrics.mean_rmse.toFixed(3) + ' %Cu' : '—'],
              ['MAE medio', metrics ? metrics.mean_mae.toFixed(3) + ' %Cu' : '—'],
              ['R² medio', metrics?.mean_r2.toFixed(3) ?? '—'],
              ['Validación', (metrics?.folds.length ?? 0) + ' grupos de sondajes reservados'],
            ].map(([label, value]) => <div key={label} className="p-2.5 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800 flex justify-between gap-2"><span>{label}:</span><span className="font-mono font-bold text-right">{value}</span></div>)}
          </div>
        </div>;
      })}
      <div className={panel + ' md:col-span-2 text-xs text-slate-600 dark:text-slate-300'}>
        <h4 className="flex items-center gap-2 text-sm font-bold mb-2"><Cpu className="w-4 h-4 text-amber-500" /> Alcance de la comparación</h4>
        <p>El menor RMSE medio de {model.model_name} motivó su selección académica. Los errores miden ensayos reservados, no leyes verificadas de cada cubo. No hay intervalos bayesianos calibrados, datos de planta, reservas ni decisión automática de despacho.</p>
        <button type="button" onClick={onOpenViewer} className="mt-3 rounded-xl bg-amber-500 px-4 py-2 font-bold text-slate-950">Abrir Gemelo Digital 3D</button>
      </div>
    </div>}
  </div>;
};

