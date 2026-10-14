import { useState } from 'react';
import { Database, Globe, HardDrive, MapPin, Search } from 'lucide-react';
import { useCopperCreekStudy } from '../../hooks/useCopperCreekStudy';
import { MiningLoader } from '../shared/MiningLoader';
import { FootprintMap } from './FootprintMap';

type Tab = 'BLOCK_MODELS' | 'DRILLHOLES' | 'HYPERSPECTRAL' | 'PROJECTIONS_ETL';
const panel = 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm';
const inset = 'bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3';

export function GeospatialManager() {
  const { scene, model, error } = useCopperCreekStudy();
  const [activeTab, setActiveTab] = useState<Tab>('BLOCK_MODELS');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [selectedHoleId, setSelectedHoleId] = useState<string | null>(null);

  if (error) return <div role="alert" className={panel + ' p-5 text-sm text-rose-600 dark:text-rose-400'}>{error}</div>;
  if (!scene || !model) return <MiningLoader title="Preparando Gestión Geoespacial" detail="Cargando los cubos y sondajes de Copper Creek." />;

  const blocks = scene.blocks;
  const drillholes = scene.drillholes;
  const query = searchQuery.trim().toLowerCase();
  const filtered = query ? blocks.filter(block => block.id.toLowerCase().includes(query)) : blocks;
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const paged = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const selectedBlock = blocks.find(block => block.id === selectedBlockId);
  const selectedHole = drillholes.find(hole => hole.hole_id === selectedHoleId) ?? drillholes[0];
  const elevations = blocks.map(block => block.z);
  const kpis = [
    { label: 'Cubos reconstruidos', value: blocks.length.toLocaleString('es-PE'), hint: '20 × 20 × 12 m' },
    { label: 'Sondajes visibles', value: drillholes.length.toLocaleString('es-PE'), hint: 'trazas en la escena 3D' },
    { label: 'Sondajes del estudio', value: model.hole_count.toLocaleString('es-PE'), hint: 'muestras que sustentan el modelo' },
    { label: 'Composites usados', value: scene.metadata.used_composites.toLocaleString('es-PE'), hint: 'ensayes agrupados en ~6 m' },
    { label: 'Firmas SWIR', value: '0', hint: 'sin espectros publicados aquí' },
  ];

  return <div className="space-y-4 sm:space-y-6">
    <div className={panel + ' p-3 sm:p-4 flex flex-wrap items-center justify-between gap-3'}>
      <div className="flex items-center gap-2">
        <Database className="w-5 h-5 text-amber-500" />
        <h2 className="text-xs sm:text-sm font-bold font-display uppercase tracking-wide">Gestión de Datos Geoespaciales · Copper Creek</h2>
      </div>
      <div className="flex flex-wrap items-center gap-1 bg-slate-100 dark:bg-slate-950 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
        {([
          ['BLOCK_MODELS', 'Modelo de Bloques'],
          ['DRILLHOLES', 'Sondajes'],
          ['HYPERSPECTRAL', 'Estado SWIR'],
          ['PROJECTIONS_ETL', 'ETL & Arquitectura'],
        ] as const).map(([tab, label]) => <button key={tab} type="button" onClick={() => setActiveTab(tab)}
          className={'px-3 py-1.5 rounded-lg font-medium transition-all ' + (activeTab === tab ? 'bg-amber-500 text-slate-950 font-bold shadow-sm' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800')}>{label}</button>)}
      </div>
    </div>

    {activeTab === 'BLOCK_MODELS' && <>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {kpis.map(kpi => <div key={kpi.label} className={panel + ' p-4'}>
          <div className="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider">{kpi.label}</div>
          <div className="mt-1.5 text-2xl font-bold font-mono">{kpi.value}</div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">{kpi.hint}</div>
        </div>)}
      </div>
      <FootprintMap blocks={blocks} drillholes={drillholes} crs={scene.metadata.crs} modelName={model.model_name} />
      <div className={panel + ' overflow-hidden'}>
        <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input type="text" placeholder="Buscar cubo por ID..." value={searchQuery}
              onChange={event => { setSearchQuery(event.target.value); setPage(1); }}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-xs focus:outline-none focus:border-amber-500" />
          </div>
          <span className="text-[10px] text-slate-500 dark:text-slate-400">Ley del modelo publicado: {model.model_name} · IDW3 solo como referencia</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-mono">
              <tr>
                <th className="p-3.5 pl-5">Cubo</th><th className="p-3.5">X / Y / Z (m)</th><th className="p-3.5 text-right">Banco</th>
                <th className="p-3.5 text-right">Cu IDW3</th><th className="p-3.5 text-right text-amber-600 dark:text-amber-400">Cu {model.model_name}</th>
                <th className="p-3.5 text-right">Dispersión local</th><th className="p-3.5 text-right">Sondajes de soporte</th><th className="p-3.5 pr-5 text-right">Muestra más cercana</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80 font-mono text-[11px]">
              {paged.map(block => <tr key={block.id} onClick={() => setSelectedBlockId(block.id)}
                className={'hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer ' + (selectedBlockId === block.id ? 'bg-amber-500/10' : '')}>
                <td className="p-3.5 pl-5 font-bold">{block.id}</td>
                <td className="p-3.5 text-slate-500 dark:text-slate-400">{block.x.toFixed(0)} / {block.y.toFixed(0)} / {block.z.toFixed(0)}</td>
                <td className="p-3.5 text-right">{block.bench} m</td>
                <td className="p-3.5 text-right">{(block.cu_idw3 ?? block.cu_base).toFixed(4)} %</td>
                <td className="p-3.5 text-right font-bold text-amber-600 dark:text-amber-400">{block.cu_bayesian.toFixed(4)} %</td>
                <td className="p-3.5 text-right">{block.epistemic_unc.toFixed(4)} %</td>
                <td className="p-3.5 text-right">{block.support_holes ?? '—'}</td>
                <td className="p-3.5 pr-5 text-right">{block.nearest_drillhole_m.toFixed(1)} m</td>
              </tr>)}
            </tbody>
          </table>
        </div>
        {selectedBlock && <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300">
          <strong className="text-amber-600 dark:text-amber-400">{selectedBlock.id}</strong> · {model.model_name}: {selectedBlock.cu_bayesian.toFixed(4)} %Cu · referencia IDW3: {(selectedBlock.cu_idw3 ?? selectedBlock.cu_base).toFixed(4)} %Cu · {selectedBlock.support_holes ?? '—'} sondajes de soporte.
        </div>}
        <div className="flex items-center justify-between gap-2 px-4 py-4 border-t border-slate-100 dark:border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono">Mostrando {filtered.length ? (currentPage - 1) * pageSize + 1 : 0}–{Math.min(currentPage * pageSize, filtered.length)} de {filtered.length} cubos</span>
          <div className="flex items-center gap-1">
            <button type="button" onClick={() => setPage(value => Math.max(1, value - 1))} disabled={currentPage <= 1} className="px-2.5 py-1 rounded-lg text-[10px] bg-slate-100 dark:bg-slate-800 disabled:opacity-40">← Anterior</button>
            <span className="text-[10px] font-mono px-1.5">{currentPage} / {totalPages}</span>
            <button type="button" onClick={() => setPage(value => Math.min(totalPages, value + 1))} disabled={currentPage >= totalPages} className="px-2.5 py-1 rounded-lg text-[10px] bg-slate-100 dark:bg-slate-800 disabled:opacity-40">Siguiente →</button>
          </div>
        </div>
      </div>
    </>}

    {activeTab === 'DRILLHOLES' && <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
      <div className={panel + ' p-4 sm:p-5 space-y-3'}>
        <h3 className="text-xs font-bold uppercase font-display tracking-wider flex justify-between"><span>Sondajes visibles ({drillholes.length})</span><span className="text-[10px] font-mono text-slate-500">{scene.metadata.crs}</span></h3>
        <div className="space-y-2 max-h-[440px] overflow-y-auto pr-1">
          {drillholes.map(hole => <button key={hole.hole_id} type="button" onClick={() => setSelectedHoleId(hole.hole_id)}
            className={'w-full text-left p-3 rounded-xl border transition-all ' + (selectedHole?.hole_id === hole.hole_id ? 'bg-amber-500/10 border-amber-500 dark:bg-slate-800/90' : 'bg-slate-50 dark:bg-slate-950/70 border-slate-200 dark:border-slate-800')}>
            <div className="flex justify-between gap-2 text-xs"><strong className="font-mono">{hole.hole_id}</strong><span className="text-slate-500">{hole.type}</span></div>
            <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-1"><span>{hole.total_depth_m.toFixed(1)} m</span><span>Inicio visible: {(hole.trace_start_depth_m ?? 0).toFixed(1)} m</span></div>
          </button>)}
        </div>
      </div>
      <div className={panel + ' lg:col-span-2 p-4 sm:p-5 space-y-4'}>
        {selectedHole && <>
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h3 className="text-sm font-bold font-display flex items-center gap-2"><MapPin className="w-4 h-4 text-amber-500" /> Sondaje {selectedHole.hole_id}</h3>
            <p className="text-xs text-slate-500 mt-1">Collar y tramo visible de la reconstrucción; no representa el registro completo de ensayes.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            {[
              ['Collar X / Y / Z', selectedHole.x.toFixed(1) + ' / ' + selectedHole.y.toFixed(1) + ' / ' + selectedHole.z.toFixed(1) + ' m'],
              ['Profundidad registrada', selectedHole.total_depth_m.toFixed(1) + ' m'],
              ['Azimut / inclinación', selectedHole.azimuth.toFixed(1) + '° / ' + selectedHole.dip.toFixed(1) + '°'],
              ['Inicio del tramo visible', (selectedHole.trace_start_depth_m ?? 0).toFixed(1) + ' m'],
              ['Puntos de trayectoria mostrados', String(selectedHole.trace?.length ?? 0)],
              ['Año de perforación', selectedHole.date_drilled || 'No registrado'],
            ].map(([label, value]) => <div key={label} className={inset}><span className="block text-slate-500 dark:text-slate-400 mb-1">{label}</span><strong className="font-mono">{value}</strong></div>)}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">El estudio usa {model.hole_count} sondajes y {scene.metadata.used_composites.toLocaleString('es-PE')} composites. Solo {drillholes.length} trayectorias cruzan la ventana representada. Los intervalos de ensaye no están incluidos en esta escena.</p>
        </>}
      </div>
    </div>}

    {activeTab === 'HYPERSPECTRAL' && <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
      <div className={panel + ' p-4 sm:p-5 space-y-3'}>
        <h3 className="text-xs font-bold uppercase font-display tracking-wider">Minerales & Firmas Espectrales</h3>
        <div className={inset + ' text-xs'}><strong>Sin firmas SWIR verificadas</strong><p className="mt-2 text-slate-500 dark:text-slate-400">Los archivos usados para esta escena contienen collares, surveys y ensayes de cobre. No contienen espectros de reflectancia por cubo.</p></div>
      </div>
      <div className={panel + ' lg:col-span-2 p-4 sm:p-5 space-y-4'}>
        <h3 className="text-sm font-bold font-display">Alcance espectral de Copper Creek</h3>
        <p className="text-xs text-slate-600 dark:text-slate-300">El estimador publicado utiliza X/Y/Z para estimar %Cu a partir de los ensayes. La escena no atribuye minerales, alteración ni firmas VNIR/SWIR a los cubos.</p>
        <div className={inset + ' text-xs'}>Para habilitar una gráfica SWIR real se necesitan mediciones espectrales con longitud de onda, reflectancia, ubicación y vínculo verificable con los sondajes o cubos de Mammoth.</div>
      </div>
    </div>}

    {activeTab === 'PROJECTIONS_ETL' && <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
      <div className={panel + ' p-5 space-y-4'}>
        <h3 className="text-sm font-bold font-display flex items-center gap-2"><Globe className="w-4 h-4 text-amber-500" /> Sistema de coordenadas</h3>
        <div className="space-y-2 text-xs">
          <div className={inset}><span className="block text-slate-500">Referencia horizontal</span><strong className="font-mono">{scene.metadata.crs}</strong></div>
          <div className={inset}><span className="block text-slate-500">Ventana de bancos</span><strong className="font-mono">{Math.min(...elevations)}–{Math.max(...elevations)} m · bancos asumidos de 12 m</strong></div>
          <div className={inset}><span className="block text-slate-500">Tamaño de cubo académico</span><strong className="font-mono">20 × 20 × 12 m</strong></div>
        </div>
      </div>
      <div className={panel + ' p-5 space-y-4'}>
        <h3 className="text-sm font-bold font-display flex items-center gap-2"><HardDrive className="w-4 h-4 text-emerald-500" /> Datos y publicación</h3>
        <div className="space-y-2 text-xs">
          <div className={inset}><span className="block text-slate-500">Entradas del estudio</span><strong>Collares, surveys y ensayes públicos de Copper Creek</strong></div>
          <div className={inset}><span className="block text-slate-500">Estimador publicado</span><strong>{model.model_name} · validación por sondajes completos</strong></div>
          <div className={inset}><span className="block text-slate-500">Entrega de la escena</span><strong>Reconstrucción estática servida por FastAPI; inferencia puntual por FastAPI</strong></div>
        </div>
      </div>
      <div className="md:col-span-2 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-2xl p-4 text-[11px] text-amber-800 dark:text-amber-300 leading-relaxed">
        Reconstrucción académica aproximada de la ventana superior de Mammoth. Los contornos y bancos no son geometría topográfica levantada; las leyes de los cubos son estimaciones. No hay firmas SWIR, clasificación de recursos ni decisión operativa de despacho.
      </div>
    </div>}
  </div>;
}

