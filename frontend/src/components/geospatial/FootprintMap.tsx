import React, { useMemo, useState } from 'react';
import { BlockModelItem, Drillhole } from '../../types';
import { useTheme } from '../../context/ThemeContext';
import { ExportableFigure } from '../shared/ExportableContent';

interface FootprintMapProps {
  blocks: BlockModelItem[];
  drillholes: Drillhole[];
  crs: string;
  modelName: string;
}

const gradeColor = (value: number): string => {
  if (value < 0.13) return '#3b82f6';
  if (value < 0.45) return '#10b981';
  if (value < 0.8) return '#f59e0b';
  return '#ef4444';
};

const W = 820;
const H = 520;
const PAD = 46;

export const FootprintMap: React.FC<FootprintMapProps> = ({ blocks, drillholes, crs, modelName }) => {
  const { isDark } = useTheme();
  const [bench, setBench] = useState<string>('ALL');

  const benches = useMemo(() => {
    const found: number[] = [];
    for (const b of blocks) {
      const bn = b.bench ?? 0;
      if (!found.includes(bn)) found.push(bn);
    }
    return found.sort((x, y) => y - x);
  }, [blocks]);

  const filtered = bench === 'ALL' ? blocks : blocks.filter(b => b.bench === Number(bench));

  const extent = useMemo(() => {
    if (!blocks.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    const xs = [...blocks.map(b => b.x), ...drillholes.map(dh => dh.x)];
    const ys = [...blocks.map(b => b.y), ...drillholes.map(dh => dh.y)];
    return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
  }, [blocks, drillholes]);

  const px = (v: number) => PAD + ((v - extent.minX) / (extent.maxX - extent.minX || 1)) * (W - 2 * PAD);
  const py = (v: number) => H - PAD - ((v - extent.minY) / (extent.maxY - extent.minY || 1)) * (H - 2 * PAD);

  const textColor = isDark ? '#94a3b8' : '#64748b';
  const gridColor = isDark ? '#1e293b' : '#e2e8f0';
  const holeColor = '#06b6d4';
  const holeStroke = isDark ? '#0f172a' : '#ffffff';

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <div>
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase font-display tracking-wider">
            Plano de Huella — Distribución Espacial
          </h3>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Cubos coloreados por ley Cu de {modelName}; collares de los sondajes visibles · {crs}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Nivel:</span>
          <select
            value={bench}
            onChange={e => setBench(e.target.value)}
            className="px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
          >
            <option value="ALL">Todos</option>
            {benches.map(b => (
              <option key={b} value={b}>{b}m</option>
            ))}
          </select>
        </div>
      </div>

      <ExportableFigure title="Plano de huella espacial" filename="copper-creek-huella-espacial" interpretation={`El plano proyecta ${filtered.length} cubos del nivel seleccionado y ${drillholes.length} collares visibles en ${crs}. El color representa la ley Cu estimada por ${modelName}.`}>
      <div className="rounded-xl overflow-hidden bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ fontFamily: 'ui-monospace, monospace' }}>
          {/* Light grid */}
          {Array.from({ length: 9 }, (_, i) => (
            <line key={`v${i}`} x1={PAD + i * ((W - 2 * PAD) / 8)} y1={PAD} x2={PAD + i * ((W - 2 * PAD) / 8)} y2={H - PAD} stroke={gridColor} strokeWidth={1} opacity={0.5} />
          ))}
          {Array.from({ length: 7 }, (_, i) => (
            <line key={`h${i}`} x1={PAD} y1={PAD + i * ((H - 2 * PAD) / 6)} x2={W - PAD} y2={PAD + i * ((H - 2 * PAD) / 6)} stroke={gridColor} strokeWidth={1} opacity={0.5} />
          ))}

          {/* Blocks */}
          {filtered.map(b => (
            <circle
              key={b.id}
              cx={px(b.x)}
              cy={py(b.y)}
              r={bench === 'ALL' ? 3.2 : 4}
              fill={gradeColor(b.cu_bayesian)}
              opacity={0.88}
              stroke="#0f172a"
              strokeWidth={0.4}
              style={{ cursor: 'pointer' }}
            >
              <title>{`${b.id} · Banco ${b.bench} m · ${b.cu_bayesian.toFixed(4)} %Cu · ${b.support_holes ?? '—'} sondajes de soporte`}</title>
            </circle>
          ))}

          {/* Drillholes */}
          {drillholes.map(dh => (
            <g key={dh.hole_id}>
              <line x1={px(dh.x) - 7} y1={py(dh.y)} x2={px(dh.x) + 7} y2={py(dh.y)} stroke={holeColor} strokeWidth={2.2} />
              <line x1={px(dh.x)} y1={py(dh.y) - 7} x2={px(dh.x)} y2={py(dh.y) + 7} stroke={holeColor} strokeWidth={2.2} />
              <circle cx={px(dh.x)} cy={py(dh.y)} r={8} fill="none" stroke={holeStroke} strokeWidth={1.4} opacity={0.9} />
              <text x={px(dh.x)} y={py(dh.y) - 12} textAnchor="middle" fontSize={11} fontWeight="bold" fill={holeColor} stroke={holeStroke} strokeWidth={2.6} paintOrder="stroke">
                {dh.hole_id}
              </text>
            </g>
          ))}
        </svg>
      </div>
      </ExportableFigure>

      {/* Grade legend + drillhole legend */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="h-2.5 w-40 rounded bg-gradient-to-r from-blue-600 via-emerald-500 via-amber-400 to-red-600 border border-slate-300 dark:border-slate-700" />
          <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">&lt; 0.13% · 0.13% · 0.45% · &gt; 0.80%</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3.5 h-3.5 rotate-45 border-2 border-cyan-500" />
            Collar visible
          </span>
          <span>Vista en planta · {crs}</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">
          {bench === 'ALL' ? `${blocks.length}` : `${filtered.length}`} bloques/{benches.length} niveles
        </span>
      </div>
    </div>
  );
};
