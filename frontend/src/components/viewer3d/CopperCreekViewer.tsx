import { useEffect, useRef, useState } from 'react';
import api from '../../services/api';
import type { BlockModelItem, Drillhole, MiningProject } from '../../types';
import { BlockModel3DViewer } from './BlockModel3DViewer';
import { MiningLoader } from '../shared/MiningLoader';

export interface CopperCreekScene {
  metadata: {
    project: string;
    status: string;
    source: string;
    crs: string;
    method: string;
    model_name: string;
    model_exported_at: string;
    model_validation: Record<string, { mean_rmse: number; mean_mae: number; mean_r2: number }>;
    support_method: string;
    geometry: string;
    study_holes: number;
    displayed_holes: number;
    used_composites: number;
    skipped_unsupported_blocks: number;
    invalid_cu_rows: number;
    reference_center: [number, number];
  };
  blocks: BlockModelItem[];
  drillholes: Drillhole[];
  pit_levels: { bench: number; points: [number, number][] }[];
}

interface CopperCreekModelInfo {
  success: boolean;
  model: { model_name: string; exported_at: string };
}

interface CopperCreekPrediction {
  success: boolean;
  model_name: string;
  predicted_cu_pct: number;
  support_holes: number;
  nearest_hole_m: number;
}

export function CopperCreekViewer() {
  const [scene, setScene] = useState<CopperCreekScene | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<BlockModelItem | null>(null);
  const [verification, setVerification] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestNumber = useRef(0);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.get<CopperCreekScene>('/api/copper-creek/mammoth-reconstruction'),
      api.get<CopperCreekModelInfo>('/api/copper-creek/model-info'),
    ])
      .then(([sceneResponse, modelResponse]) => {
        if (!mounted) return;
        const study = sceneResponse.data;
        const published = modelResponse.data.model;
        if (study.metadata.model_name !== published.model_name ||
            study.metadata.model_exported_at !== published.exported_at) {
          setError('La escena y el modelo publicado no coinciden. Regenera la reconstrucción de Copper Creek.');
          return;
        }
        setScene(study);
      })
      .catch(() => {
        if (mounted) setError('No se pudo cargar la reconstrucción o el modelo ganador. Comprueba FastAPI y la publicación Copper Creek.');
      });
    return () => { mounted = false; };
  }, []);

  const handleBlockSelect = (block: BlockModelItem) => {
    setSelectedBlock(block);
    setVerification('Comprobando predicción con FastAPI…');
    const currentRequest = ++requestNumber.current;
    api.post<CopperCreekPrediction>('/api/copper-creek/predict', {
      x: block.x, y: block.y, z: block.z,
    }).then(({ data }) => {
      if (requestNumber.current !== currentRequest) return;
      if (data.model_name !== scene?.metadata.model_name ||
          Math.abs(data.predicted_cu_pct - block.cu_bayesian) > 0.0002) {
        setVerification('La predicción no coincide con el cubo publicado. Reconstruye la escena.');
        return;
      }
      setVerification(`FastAPI · ${data.model_name}: ${data.predicted_cu_pct.toFixed(4)} %Cu · ${data.support_holes} sondajes`);
    }).catch((response) => {
      if (requestNumber.current !== currentRequest) return;
      setVerification(response?.response?.data?.detail || 'No se pudo verificar este cubo con FastAPI.');
    });
  };

  if (error) {
    return <div className="rounded-xl border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-300">{error}</div>;
  }
  if (!scene) {
    return <MiningLoader title="Preparando el Gemelo Digital 3D" detail="Cargando el tajo aproximado, los cubos estimados y los sondajes." className="h-full" />;
  }

  const project: MiningProject = {
    id: 'copper-creek-study',
    name: scene.metadata.project,
    mineSite: 'Copper Creek, Arizona',
    country: 'Estados Unidos',
    epsgCode: scene.metadata.crs,
    primaryCommodity: 'Cu',
    secondaryCommodity: 'Au',
    cutOffGrade: 0.13,
    highGradeThreshold: 0.45,
    densityT_m3: 2.6,
    totalBlocks: scene.blocks.length,
    activeBench: scene.pit_levels[0]?.bench ?? 1316,
    lastModelRun: 'Reconstrucción exploratoria',
  };

  return (
    <div className="relative h-full min-h-0 flex flex-col">
      <div className="min-h-0 flex-1">
        <BlockModel3DViewer
          blocks={scene.blocks}
          drillholes={scene.drillholes}
          project={project}
          selectedBlock={selectedBlock}
          onSelectBlock={handleBlockSelect}
          copperCreek
          copperCreekModelName={scene.metadata.model_name}
          hasAttachedFooter
          referenceCenter={scene.metadata.reference_center}
          referencePitLevels={scene.pit_levels}
        />
      </div>
      <div aria-live="polite" className="shrink-0 rounded-b-2xl border border-slate-200 border-t-cyan-300/60 bg-white px-3 py-2 text-[11px] font-mono text-cyan-900 dark:border-slate-800 dark:border-t-cyan-700/70 dark:bg-slate-900 dark:text-cyan-200">
        {verification ?? 'Haz clic en un cubo para verificar su ley de Cu con FastAPI y consultar cuántos sondajes lo respaldan.'}
      </div>
    </div>
  );
}
