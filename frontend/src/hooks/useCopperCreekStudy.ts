import { useEffect, useState } from 'react';
import api from '../services/api';
import type { CopperCreekScene } from '../components/viewer3d/CopperCreekViewer';

export interface CopperCreekModelMetadata {
  model_name: string;
  exported_at: string;
  validation: string;
  sample_count: number;
  hole_count: number;
  features: string[];
  target: string;
  support_rule: { max_distance_m: number; min_holes: number; max_holes: number };
  comparison: Record<string, {
    mean_rmse: number;
    mean_mae: number;
    mean_r2: number;
    folds: Array<{
      fold: number;
      test_holes: number;
      test_samples: number;
      supported_samples: number;
      rmse: number;
      mae: number;
      r2: number;
    }>;
  }>;
}

export function useCopperCreekStudy() {
  const [scene, setScene] = useState<CopperCreekScene | null>(null);
  const [model, setModel] = useState<CopperCreekModelMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.get<CopperCreekScene>('/api/copper-creek/mammoth-reconstruction'),
      api.get<{ model: CopperCreekModelMetadata }>('/api/copper-creek/model-info'),
    ]).then(([sceneResponse, modelResponse]) => {
      if (!mounted) return;
      const study = sceneResponse.data;
      const published = modelResponse.data.model;
      if (study.metadata.model_name !== published.model_name ||
          study.metadata.model_exported_at !== published.exported_at) {
        setError('La escena y el modelo publicado no coinciden. Reconstruye Copper Creek.');
        return;
      }
      setScene(study);
      setModel(published);
    }).catch(() => {
      if (mounted) setError('No se pudo cargar Copper Creek o su modelo publicado por FastAPI.');
    });
    return () => { mounted = false; };
  }, []);

  return { scene, model, error };
}
