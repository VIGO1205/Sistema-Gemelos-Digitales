import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { BlockModelItem, Drillhole, MiningProject } from '../../types';
import { useTheme } from '../../context/ThemeContext';
import { economicsApi } from '../../services/api';
import { 
  Layers, 
  Filter, 
  MapPin, 
  Mountain, 
  Activity,
  Sliders,
  ChevronDown,
  Maximize2,
  Minimize2,
  ChevronUp,
  Play,
  Pause,
  RotateCcw,
  Truck,
  Trash2,
  Factory,
  Download,
  TrendingUp,
  Target,
  ShieldCheck,
  Settings2,
  Volume2,
  VolumeX,
  Route,
  FileUp,
  Database
} from 'lucide-react';

interface BlockModel3DViewerProps {
  blocks: BlockModelItem[];
  drillholes: Drillhole[];
  project?: MiningProject;
  selectedBlock?: BlockModelItem | null;
  selectedBlockId?: string | null;
  onSelectBlock?: (block: BlockModelItem) => void;
  activeBench?: number;
  copperCreek?: boolean;
  copperCreekModelName?: string;
  hasAttachedFooter?: boolean;
  referenceCenter?: [number, number];
  referencePitLevels?: { bench: number; points: [number, number][] }[];
}

type ColorMode = 'CU_BAYESIAN' | 'CU_BASE' | 'UNCERTAINTY' | 'JORC_CATEGORY' | 'LITHOLOGY' | 'HYPERSPECTRAL' | 'DESPACHO_SIMULATION';
type DispatchStrategy = 'CUT_OFF' | 'MAX_GRADE' | 'BLEND_TARGET' | 'MIN_UNCERTAINTY' | 'ECON_NSR';
type BlockDestiny = 'PLANT' | 'WASTE';
type PitMode = 'PROCEDURAL' | 'REALISTIC' | 'IMPORTED' | 'REFERENCE';

interface PitPoint {
  bench: number;
  x: number;
  y: number;
}

interface PitLevel {
  bench: number;
  points: THREE.Vector3[];
}

interface StrategyConfig {
  capacityTonnes: number;
  targetGrade: number;
  blendTolerance: number;
}

interface EconLithologyRecovery {
  lithology: string;
  cu_recovery_pct: number;
  au_recovery_pct: number;
}

interface EconBenchCutoff {
  cut_off_grade_pct: number;
  mining_cost_usd_ton: number;
  processing_cost_usd_ton: number;
  g_and_a_usd_ton: number;
}

interface EconParams {
  cu_price_usd_lb: number;
  au_price_usd_g: number;
  concentrate_cu_pct: number;
  payability_cu_pct: number;
  payability_au_pct: number;
  tc_usd_t: number;
  rc_usd_lb: number;
  freight_usd_t: number;
  recovery_by_lithology: EconLithologyRecovery[];
}

interface EconState {
  params: EconParams;
  benches: Record<number, EconBenchCutoff>;
}

const ECON_LB_PER_TON = 2204.62;
const DEFAULT_RECOVERY_FALLBACK = { cu: 80, au: 55 };

const computeNSR = (block: BlockModelItem, p: EconParams): number => {
  const rec = p.recovery_by_lithology.find(r => r.lithology === block.lithology)
    || { cu_recovery_pct: DEFAULT_RECOVERY_FALLBACK.cu, au_recovery_pct: DEFAULT_RECOVERY_FALLBACK.au };
  const ton = block.tonnage ?? 15000;
  const cuPct = block.cu_bayesian ?? 0;
  const auPct = block.au_bayesian ?? 0;

  const cuMetalT = ton * (cuPct / 100);
  const cuPayableLb = cuMetalT * (rec.cu_recovery_pct / 100) * (p.payability_cu_pct / 100) * ECON_LB_PER_TON;
  const cuValue = cuPayableLb * p.cu_price_usd_lb;

  const auGrams = ton * (auPct / 100) * (rec.au_recovery_pct / 100) * 1000;
  const auValue = auGrams * (p.payability_au_pct / 100) * p.au_price_usd_g;

  const concentrateT = cuMetalT * (rec.cu_recovery_pct / 100) / (p.concentrate_cu_pct / 100);
  const deductions = concentrateT * (p.tc_usd_t + p.freight_usd_t) + cuPayableLb * p.rc_usd_lb;

  return cuValue + auValue - deductions;
};

// Realistic porphyry copper open-pit example dataset
// (kidney/oval shaped, characteristic of Andean porphyry mines)
const REALISTIC_PIT_DATA: PitLevel[] = (() => {
  const benches = [3200, 3185, 3170, 3155, 3140, 3125, 3110, 3095, 3080, 3065];
  const n = 144;
  const levels: PitLevel[] = [];
  benches.forEach((bench, bi) => {
    const t = bi / (benches.length - 1);
    const R = 210 - t * 145; // 210m at crest → 65m at floor
    const points: THREE.Vector3[] = [];
    // Slightly shifted center per bench (real pits meander)
    const cx = Math.sin(bi * 0.7) * 14;
    const cz = Math.cos(bi * 1.1) * 10;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      // Preferential radii: elongated kidney shape typical of porphyry pits
      const r = R * (
        1 +
        -0.14 * Math.cos(a) +                       // main elongation east-west
        0.06 * Math.cos(2 * a + 0.6) +              // secondary asymmetry
        0.05 * Math.sin(3 * a + 1.1) +              // waviness
        -0.04 * Math.cos(5 * a + 2.2) +
        0.03 * Math.sin(7 * a + 0.4) +
        (bi % 2 === 0 ? 0.02 : -0.02) * Math.sin(a * 9 + bi * 2.1)
      );
      points.push(new THREE.Vector3(cx + Math.cos(a) * r, 0, cz + Math.sin(a) * r));
    }
    levels.push({ bench, points });
  });
  return levels;
})();

// Parser for imported pit data
const parsePitCSV = (text: string): PitLevel[] => {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0 && !l.startsWith('#'));
  if (lines.length === 0) throw new Error('El archivo está vacío');
  const rows: PitPoint[] = [];
  let headerSkipped = false;
  for (const line of lines) {
    const parts = line.split(/[,\t;]/).map(p => p.trim());
    if (!headerSkipped) {
      const looksLikeHeader = parts.every(p => isNaN(Number(p)));
      if (looksLikeHeader) { headerSkipped = true; continue; }
      headerSkipped = true;
    }
    const nums = parts.map(Number);
    if (nums.some(isNaN) || nums.length < 3) continue;
    rows.push({ bench: nums[0], x: nums[1], y: nums[2] });
  }
  if (rows.length === 0) throw new Error('No se encontraron puntos válidos (deben ser números)');
  const benchSet = new Set(rows.map(r => r.bench));
  const levels: PitLevel[] = [];
  Array.from(benchSet).sort((a, b) => b - a).forEach(bench => {
    const pts = rows.filter(r => r.bench === bench).map(r => new THREE.Vector3(r.x, 0, r.y));
    if (pts.length >= 3) levels.push({ bench, points: pts });
  });
  if (levels.length < 2) throw new Error('Se necesitan al menos 2 niveles con 3+ puntos cada uno');
  return levels;
};

export const BlockModel3DViewer: React.FC<BlockModel3DViewerProps> = ({
  blocks,
  drillholes,
  project,
  selectedBlock,
  selectedBlockId,
  onSelectBlock,
  activeBench,
  copperCreek = false,
  copperCreekModelName = 'IDW3',
  hasAttachedFooter = false,
  referenceCenter,
  referencePitLevels,
}) => {
  const { isDark } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const activeSelectedId = selectedBlockId || selectedBlock?.id || null;
  const projectCutOff = project?.cutOffGrade ?? 0.35;

  // Filter States
  const [colorMode, setColorMode] = useState<ColorMode>('CU_BAYESIAN');
  const [selectedBench, setSelectedBench] = useState<number | 'ALL'>(activeBench ?? 'ALL');
  const [cutOffFilter, setCutOffFilter] = useState<number>(0.0);
  const [maxUncertaintyFilter] = useState<number>(copperCreek ? Number.POSITIVE_INFINITY : 0.5);
  const [showDrillholes, setShowDrillholes] = useState<boolean>(true);
  const [showPitWireframe, setShowPitWireframe] = useState<boolean>(true);
  const [hoveredBlock, setHoveredBlock] = useState<BlockModelItem | null>(null);
  const [hoveredDrillhole, setHoveredDrillhole] = useState<Drillhole | null>(null);
  const [hoveredPit, setHoveredPit] = useState<boolean>(false);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const [showMobileControls, setShowMobileControls] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showPitInfo, setShowPitInfo] = useState<boolean>(true);
  const [showTrajectories, setShowTrajectories] = useState<boolean>(true);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(false);
  const [pitMode, setPitMode] = useState<PitMode>(copperCreek ? 'REFERENCE' : 'PROCEDURAL');
  const [importedPitText, setImportedPitText] = useState<string>('');
  const [importedPitError, setImportedPitError] = useState<string>('');
  const [importedPitLevels, setImportedPitLevels] = useState<PitLevel[]>([]);
  const viewerRef = useRef<HTMLDivElement>(null);

  // Simulation States
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simProgress, setSimProgress] = useState<number>(0);
  const [simSpeed, setSimSpeed] = useState<number>(1); // blocks per tick
  const [simStats, setSimStats] = useState<{ toPlant: number; toWaste: number; totalTonnesPlant: number; totalTonnesWaste: number; avgGradePlant: number }>({
    toPlant: 0, toWaste: 0, totalTonnesPlant: 0, totalTonnesWaste: 0, avgGradePlant: 0
  });
  const [simMoney, setSimMoney] = useState<{ revenue: number; extraction: number; processing: number; cost: number; net: number }>({ revenue: 0, extraction: 0, processing: 0, cost: 0, net: 0 });
  const [strategy, setStrategy] = useState<DispatchStrategy>('CUT_OFF');
  const [strategyConfig, setStrategyConfig] = useState<StrategyConfig>({
    capacityTonnes: 100000,
    targetGrade: 0.45,
    blendTolerance: 0.15
  });
  const [showStrategyConfig, setShowStrategyConfig] = useState<boolean>(false);
  const [econState, setEconState] = useState<EconState | null>(null);
  const simBlocksRef = useRef<BlockModelItem[]>([]);
  const simProcessedRef = useRef<Set<string>>(new Set());
  const simIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const blockMeshesRef = useRef<Map<string, THREE.Mesh>>(new Map());
  const classifiedRef = useRef<Map<string, BlockDestiny>>(new Map());
  const trajectoryGroupRef = useRef<THREE.Group | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Camera orbit state persisted across re-renders
  const sphericalRef = useRef(new THREE.Spherical(420, Math.PI / 3.5, Math.PI / 4));
  const cameraTargetRef = useRef(new THREE.Vector3(0, 130, 0));
  const copperCameraInitialized = useRef(false);
  const updateCameraRef = useRef<(() => void) | null>(null);
  const isDraggingRef = useRef(false);
  const prevMouseRef = useRef({ x: 0, y: 0 });

  // Slider para subir/bajar la CÁMARA en posición (traslación vertical de la cámara, sin rotarla)
  const CAM_MIN_OFFSET = -80;
  const CAM_MAX_OFFSET = 260;
  const camOffsetToVal = (offset: number) =>
    Math.round(((CAM_MAX_OFFSET - offset) / (CAM_MAX_OFFSET - CAM_MIN_OFFSET)) * 100);
  const camValToOffset = (v: number) => CAM_MAX_OFFSET - (v / 100) * (CAM_MAX_OFFSET - CAM_MIN_OFFSET);
  const camHeightOffsetRef = useRef(0);
  const [camHeightVal, setCamHeightVal] = useState<number>(() => camOffsetToVal(0));

  const handleCamHeightChange = (v: number) => {
    setCamHeightVal(v);
    camHeightOffsetRef.current = camValToOffset(v);
    if (updateCameraRef.current) updateCameraRef.current();
  };

  // Sync bench if activeBench prop changes
  useEffect(() => {
    if (activeBench !== undefined) {
      setSelectedBench(activeBench);
    }
  }, [activeBench]);

  // Fullscreen toggle
  const toggleFullscreen = async () => {
    if (!viewerRef.current) return;
    try {
      if (!document.fullscreenElement) {
        await viewerRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch {
      // Fallback: toggle a class-based fullscreen state for unsupported browsers
      setIsFullscreen(prev => !prev);
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  // Bench levels derived from the real block model (no phantom levels)
  const benches = useMemo(() => {
    const found: number[] = [];
    for (const b of blocks) {
      const bn = b.bench;
      if (bn !== undefined && !found.includes(bn)) found.push(bn);
    }
    return found.sort((x, y) => y - x);
  }, [blocks]);

  // Color Mapping Helper Functions
  const getGradeColor = (val: number): THREE.Color => {
    if (copperCreek) {
      if (val < 0.13) return new THREE.Color(0.2, 0.45, 0.9);
      if (val < 0.45) return new THREE.Color(0.12, 0.75, 0.43);
      if (val < 0.8) return new THREE.Color(0.95, 0.72, 0.18);
      return new THREE.Color(0.92, 0.26, 0.19);
    }
    if (val < 0.35) {
      const t = Math.max(0, (val - 0.1) / 0.25);
      return new THREE.Color(0.2, 0.4 + t * 0.4, 0.9 - t * 0.4);
    } else if (val < 0.70) {
      const t = (val - 0.35) / 0.35;
      return new THREE.Color(0.1 + t * 0.3, 0.8 + t * 0.1, 0.3 - t * 0.2);
    } else if (val < 1.10) {
      const t = (val - 0.70) / 0.40;
      return new THREE.Color(0.6 + t * 0.4, 0.8 - t * 0.2, 0.1);
    } else {
      const t = Math.min(1.0, (val - 1.10) / 0.60);
      return new THREE.Color(0.95, 0.3 - t * 0.2, 0.1 + t * 0.3);
    }
  };

  const getUncertaintyColor = (unc: number): THREE.Color => {
    if (unc < 0.10) {
      return new THREE.Color(0.1, 0.7, 0.4);
    } else if (unc < 0.22) {
      return new THREE.Color(0.95, 0.7, 0.15);
    } else {
      return new THREE.Color(0.95, 0.2, 0.25);
    }
  };

  const getJorcColor = (cat: string): THREE.Color => {
    switch (cat) {
      case 'Measured': return new THREE.Color(0.15, 0.75, 0.35);
      case 'Indicated': return new THREE.Color(0.95, 0.65, 0.15);
      case 'Inferred': return new THREE.Color(0.90, 0.30, 0.25);
      default: return new THREE.Color(0.5, 0.5, 0.55);
    }
  };

  const getLithologyColor = (litho: string): THREE.Color => {
    switch (litho) {
      case 'Brecha Hidrotermal': return new THREE.Color(0.85, 0.25, 0.65);
      case 'Pórfido Cuprífero': return new THREE.Color(0.95, 0.55, 0.15);
      case 'Skarn Mineralizado': return new THREE.Color(0.20, 0.75, 0.85);
      case 'Andesita Huinquintipa': return new THREE.Color(0.35, 0.45, 0.55);
      default: return new THREE.Color(0.4, 0.4, 0.4);
    }
  };

  const getHyperspectralColor = (mineral: string): THREE.Color => {
    if (mineral.includes('Bornita') || mineral.includes('Biotita')) return new THREE.Color(0.95, 0.4, 0.1);
    if (mineral.includes('Illita') || mineral.includes('Fílica')) return new THREE.Color(0.2, 0.6, 0.95);
    if (mineral.includes('Clorita') || mineral.includes('Epidota')) return new THREE.Color(0.15, 0.7, 0.35);
    if (mineral.includes('Crisocola') || mineral.includes('Malaquita')) return new THREE.Color(0.1, 0.85, 0.75);
    return new THREE.Color(0.5, 0.5, 0.5);
  };

  // Filter blocks
  const visibleBlocks = useMemo(() => {
    return blocks.filter(b => {
      if (selectedBench !== 'ALL' && b.bench !== selectedBench) return false;
      if (b.cu_bayesian < cutOffFilter) return false;
      if (b.epistemic_unc > maxUncertaintyFilter) return false;
      return true;
    });
  }, [blocks, selectedBench, cutOffFilter, maxUncertaintyFilter]);

  // Fetch economic cut-offs for unified dispatch criteria (real NSR economics)
  useEffect(() => {
    if (copperCreek) {
      setEconState(null);
      return;
    }
    const projectId = project?.databaseId;
    if (projectId == null) {
      setEconState(null);
      return;
    }
    economicsApi.getCutoffs({ project_id: projectId })
      .then(r => {
        const d = r.data;
        const benches: Record<number, EconBenchCutoff> = {};
        (d.benches || []).forEach((b: any) => {
          benches[b.bench] = {
            cut_off_grade_pct: b.cut_off_grade_pct,
            mining_cost_usd_ton: b.mining_cost_usd_ton,
            processing_cost_usd_ton: b.processing_cost_usd_ton,
            g_and_a_usd_ton: b.g_and_a_usd_ton,
          };
        });
        setEconState({
          params: {
            cu_price_usd_lb: d.params.cu_price_usd_lb,
            au_price_usd_g: d.params.au_price_usd_g,
            concentrate_cu_pct: d.params.concentrate_cu_pct,
            payability_cu_pct: d.params.payability_cu_pct,
            payability_au_pct: d.params.payability_au_pct,
            tc_usd_t: d.params.tc_usd_t,
            rc_usd_lb: d.params.rc_usd_lb,
            freight_usd_t: d.params.freight_usd_t,
            recovery_by_lithology: d.params.recovery_by_lithology || [],
          },
          benches,
        });
      })
      .catch(() => setEconState(null));
  }, [project?.databaseId, copperCreek]);

  // Classify all visible blocks according to selected strategy
  const classifyBlocks = useMemo(() => {
    const result = new Map<string, BlockDestiny>();
    if (visibleBlocks.length === 0) return result;

    switch (strategy) {
      case 'CUT_OFF': {
        visibleBlocks.forEach(b => {
          const perBenchCutOff = econState?.benches[b.bench]?.cut_off_grade_pct;
          const effectiveCutOff = perBenchCutOff != null ? perBenchCutOff : projectCutOff;
          result.set(b.id, (b.cu_bayesian ?? 0) >= effectiveCutOff ? 'PLANT' : 'WASTE');
        });
        break;
      }
      case 'ECON_NSR': {
        visibleBlocks.forEach(b => {
          const bc = econState?.benches[b.bench];
          if (econState && bc) {
            const costPerTon = bc.mining_cost_usd_ton + bc.processing_cost_usd_ton + bc.g_and_a_usd_ton;
            const nsr = computeNSR(b, econState.params);
            result.set(b.id, nsr >= (b.tonnage ?? 15000) * costPerTon ? 'PLANT' : 'WASTE');
          } else {
            result.set(b.id, (b.cu_bayesian ?? 0) >= projectCutOff ? 'PLANT' : 'WASTE');
          }
        });
        break;
      }
      case 'MAX_GRADE': {
        const sorted = [...visibleBlocks].sort((a, b) => (b.cu_bayesian ?? 0) - (a.cu_bayesian ?? 0));
        let cumTonnage = 0;
        sorted.forEach(b => {
          const t = b.tonnage ?? 15000;
          if (cumTonnage < strategyConfig.capacityTonnes) {
            result.set(b.id, 'PLANT');
            cumTonnage += t;
          } else {
            result.set(b.id, 'WASTE');
          }
        });
        break;
      }
      case 'BLEND_TARGET': {
        const target = strategyConfig.targetGrade;
        const tol = strategyConfig.blendTolerance;
        // Greedy: pick blocks closest to target first to maintain blend
        const sorted = [...visibleBlocks].sort((a, b) =>
          Math.abs((a.cu_bayesian ?? 0) - target) - Math.abs((b.cu_bayesian ?? 0) - target)
        );
        let cumTonnage = 0;
        let cumGrade = 0;
        sorted.forEach(b => {
          const t = b.tonnage ?? 15000;
          const grade = b.cu_bayesian ?? 0;
          const potentialAvg = (cumGrade + grade * t) / (cumTonnage + t);
          // Accept if it keeps us within tolerance of target, OR if we need more tonnage
          if (cumTonnage < strategyConfig.capacityTonnes && Math.abs(potentialAvg - target) <= tol) {
            result.set(b.id, 'PLANT');
            cumTonnage += t;
            cumGrade += grade * t;
          } else if (cumTonnage < strategyConfig.capacityTonnes * 0.5 && grade >= target) {
            // Fallback: if below 50% capacity, accept high-grade blocks
            result.set(b.id, 'PLANT');
            cumTonnage += t;
            cumGrade += grade * t;
          } else {
            result.set(b.id, 'WASTE');
          }
        });
        break;
      }
      case 'MIN_UNCERTAINTY': {
        const sorted = [...visibleBlocks].sort((a, b) => (a.epistemic_unc ?? 1) - (b.epistemic_unc ?? 1));
        let cumTonnage = 0;
        sorted.forEach(b => {
          const t = b.tonnage ?? 15000;
          if (cumTonnage < strategyConfig.capacityTonnes) {
            result.set(b.id, 'PLANT');
            cumTonnage += t;
          } else {
            result.set(b.id, 'WASTE');
          }
        });
        break;
      }
    }
    return result;
  }, [visibleBlocks, strategy, strategyConfig, projectCutOff, econState]);

  // Simulation control functions (after visibleBlocks)
  const startSimulation = () => {
    if (visibleBlocks.length === 0) return;
    if (simProgress >= visibleBlocks.length) {
      resetSimulation();
    }
    setIsSimulating(true);
  };

  const pauseSimulation = () => {
    setIsSimulating(false);
  };

  const resetSimulation = () => {
    setIsSimulating(false);
    setSimProgress(0);
    simProcessedRef.current = new Set();
    setSimStats({ toPlant: 0, toWaste: 0, totalTonnesPlant: 0, totalTonnesWaste: 0, avgGradePlant: 0 });
    setSimMoney({ revenue: 0, extraction: 0, processing: 0, cost: 0, net: 0 });
    // Reset all block materials back to dimmed (unprocessed) without rebuilding scene
    blockMeshesRef.current.forEach((mesh) => {
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.color.set(0.5, 0.5, 0.55);
      mat.emissive.set(0, 0, 0);
      mat.roughness = 0.8;
      mat.metalness = 0.0;
      mat.opacity = 0.25;
      mat.transparent = true;
      mat.depthWrite = false;
      mat.needsUpdate = true;
    });
    // Clear trajectory group
    if (trajectoryGroupRef.current && sceneRef.current) {
      sceneRef.current.remove(trajectoryGroupRef.current);
      trajectoryGroupRef.current.traverse(child => {
        if (child instanceof THREE.Line || child instanceof THREE.Mesh) {
          child.geometry.dispose();
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
          else child.material.dispose();
        }
      });
      trajectoryGroupRef.current = null;
    }
  };

  // Sync classification map to ref for interval access
  useEffect(() => {
    classifiedRef.current = classifyBlocks;
  }, [classifyBlocks]);

  // Simulation effects (must be after visibleBlocks declaration)
  useEffect(() => {
    if (colorMode !== 'DESPACHO_SIMULATION') {
      pauseSimulation();
    }
  }, [colorMode]);

  useEffect(() => {
    if (!isSimulating) {
      if (simIntervalRef.current) {
        clearInterval(simIntervalRef.current);
        simIntervalRef.current = null;
      }
      return;
    }
    simBlocksRef.current = visibleBlocks;
    simIntervalRef.current = setInterval(() => {
      setSimProgress(prev => {
        const next = Math.min(prev + simSpeed, simBlocksRef.current.length);
        if (next === prev) return prev;

        // OPTIMIZATION: update only newly processed block materials directly
        // instead of rebuilding the entire Three.js scene
        for (let i = prev; i < next; i++) {
          const block = simBlocksRef.current[i];
          if (!block) continue;
          const mesh = blockMeshesRef.current.get(block.id);
          if (!mesh) continue;

          const mat = mesh.material as THREE.MeshStandardMaterial;
          const destiny = classifiedRef.current.get(block.id);
          if (destiny === 'PLANT') {
            // To plant — green glow
            mat.color.set(0.15, 0.85, 0.35);
            mat.emissive.set(0.05, 0.3, 0.05);
            mat.roughness = 0.2;
            mat.metalness = 0.4;
          } else {
            // To waste — red
            mat.color.set(0.75, 0.25, 0.25);
            mat.emissive.set(0, 0, 0);
            mat.roughness = 0.7;
            mat.metalness = 0.05;
          }
          mat.opacity = 1.0;
          mat.transparent = false;
          mat.depthWrite = true;
          mat.needsUpdate = true;

          // Trajectory lines — short elegant dash + destination dot
          if (showTrajectories && sceneRef.current) {
            const start = mesh.position.clone();
            const dir = destiny === 'PLANT'
              ? new THREE.Vector3(0.6, -0.3, 0.4).normalize()
              : new THREE.Vector3(-0.6, 0.2, -0.4).normalize();
            const end = start.clone().add(dir.multiplyScalar(18));

            // Short dash line
            const points = [start, end];
            const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
            const lineMat = new THREE.LineDashedMaterial({
              color: destiny === 'PLANT' ? 0x22c55e : 0xef4444,
              transparent: true,
              opacity: 0.6,
              dashSize: 3,
              gapSize: 2,
              depthWrite: false,
            });
            const line = new THREE.Line(lineGeo, lineMat);
            line.computeLineDistances();
            sceneRef.current.add(line);

            // Small destination dot
            const dotGeo = new THREE.SphereGeometry(1.2, 8, 8);
            const dotMat = new THREE.MeshBasicMaterial({
              color: destiny === 'PLANT' ? 0x22c55e : 0xef4444,
              transparent: true,
              opacity: 0.7,
              depthWrite: false,
            });
            const dot = new THREE.Mesh(dotGeo, dotMat);
            dot.position.copy(end);
            sceneRef.current.add(dot);

            // Add to group ref for cleanup
            if (!trajectoryGroupRef.current) {
              trajectoryGroupRef.current = new THREE.Group();
              sceneRef.current.add(trajectoryGroupRef.current);
            }
            trajectoryGroupRef.current.add(line);
            trajectoryGroupRef.current.add(dot);

            // Fade out after 1.5s
            setTimeout(() => {
              lineMat.opacity = 0.2;
              dotMat.opacity = 0.2;
              setTimeout(() => {
                if (trajectoryGroupRef.current) {
                  trajectoryGroupRef.current.remove(line);
                  trajectoryGroupRef.current.remove(dot);
                }
                lineGeo.dispose();
                lineMat.dispose();
                dotGeo.dispose();
                dotMat.dispose();
              }, 1000);
            }, 1500);
          }

          // Sound effect — staggered via single AudioContext with incremental delays
          if (soundEnabled && typeof window !== 'undefined') {
            try {
              if (!audioCtxRef.current) {
                audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
              }
              const ctx = audioCtxRef.current;
              if (ctx.state === 'suspended') ctx.resume();

              const blockIndexInTick = i - prev; // 0, 1, 2... within this tick
              const delay = blockIndexInTick * 0.06; // 60ms stagger per block
              const t = ctx.currentTime + delay;

              const osc = ctx.createOscillator();
              const gain = ctx.createGain();
              osc.connect(gain);
              gain.connect(ctx.destination);

              osc.type = 'triangle';
              osc.frequency.setValueAtTime(destiny === 'PLANT' ? 700 : 350, t);
              osc.frequency.exponentialRampToValueAtTime(destiny === 'PLANT' ? 900 : 450, t + 0.08);

              gain.gain.setValueAtTime(0, t);
              gain.gain.linearRampToValueAtTime(0.04, t + 0.02);
              gain.gain.exponentialRampToValueAtTime(0.001, t + 0.15);

              osc.start(t);
              osc.stop(t + 0.15);
            } catch { /* ignore audio errors */ }
          }
        }

        // Mark processed
        for (let i = prev; i < next; i++) {
          const block = simBlocksRef.current[i];
          if (block) simProcessedRef.current.add(block.id);
        }

        return next;
      });
    }, 80); // tick every 80ms
    return () => {
      if (simIntervalRef.current) {
        clearInterval(simIntervalRef.current);
        simIntervalRef.current = null;
      }
    };
  }, [isSimulating, simSpeed, visibleBlocks, projectCutOff, showTrajectories, soundEnabled]);

  useEffect(() => {
    // Update stats when progress changes
    const processed = simBlocksRef.current.slice(0, simProgress);
    const toPlant = processed.filter(b => classifyBlocks.get(b.id) === 'PLANT');
    const toWaste = processed.filter(b => classifyBlocks.get(b.id) === 'WASTE');
    const totalTonnesPlant = toPlant.reduce((s, b) => s + (b.tonnage ?? 15000), 0);
    const avgGradePlant = totalTonnesPlant > 0
      ? toPlant.reduce((s, b) => s + (b.cu_bayesian ?? 0) * (b.tonnage ?? 15000), 0) / totalTonnesPlant
      : 0;
    setSimStats({
      toPlant: toPlant.length,
      toWaste: toWaste.length,
      totalTonnesPlant,
      totalTonnesWaste: toWaste.reduce((s, b) => s + (b.tonnage ?? 15000), 0),
      avgGradePlant,
    });
    // Money calculation — uses real NSR/OPEX economics when available, else legacy constants
    let plantRevenue = 0;
    let extractionCost = 0;
    let processingCost = 0;
    if (econState) {
      plantRevenue = toPlant.reduce((s, b) => s + computeNSR(b, econState.params), 0);
      processed.forEach(b => {
        const bc = econState.benches[b.bench];
        const isPlant = classifyBlocks.get(b.id) === 'PLANT';
        const ton = b.tonnage ?? 15000;
        const mining = bc ? bc.mining_cost_usd_ton : 2.5;
        extractionCost += ton * mining;
        if (isPlant) {
          const processing = bc ? bc.processing_cost_usd_ton + bc.g_and_a_usd_ton : 2.5;
          processingCost += ton * processing;
        }
      });
    } else {
      const copperPricePerTon = 9000; // USD per ton of copper metal (fallback)
      const movementCostPerTon = 2.5; // USD per ton moved (fallback)
      plantRevenue = toPlant.reduce((s, b) => s + (b.tonnage ?? 15000) * (b.cu_bayesian ?? 0) / 100 * copperPricePerTon, 0);
      extractionCost = processed.reduce((s, b) => s + (b.tonnage ?? 15000) * movementCostPerTon, 0);
      processingCost = 0;
    }
    const totalCost = extractionCost + processingCost;
    setSimMoney({
      revenue: plantRevenue,
      extraction: extractionCost,
      processing: processingCost,
      cost: totalCost,
      net: plantRevenue - totalCost,
    });
    simProcessedRef.current = new Set(processed.map(b => b.id));
    // Auto-pause when finished
    if (simProgress > 0 && simProgress >= simBlocksRef.current.length) {
      setIsSimulating(false);
      // Completion chime
      if (soundEnabled && typeof window !== 'undefined') {
        try {
          if (!audioCtxRef.current) {
            audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
          }
          const ctx = audioCtxRef.current;
          if (ctx.state === 'suspended') ctx.resume();
          const t = ctx.currentTime + 0.3;

          // Two ascending tones: DING-DING!
          [523.25, 783.99].forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            const noteT = t + idx * 0.18;
            osc.frequency.setValueAtTime(freq, noteT);
            gain.gain.setValueAtTime(0, noteT);
            gain.gain.linearRampToValueAtTime(0.06, noteT + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.001, noteT + 0.4);
            osc.start(noteT);
            osc.stop(noteT + 0.4);
          });
        } catch { /* ignore audio errors */ }
      }
    }
  }, [simProgress, classifyBlocks, soundEnabled, econState]);

  // Three.js Interactive Setup
  useEffect(() => {
    if (!containerRef.current || !canvasRef.current) return;

    const width = Math.max(1, containerRef.current.clientWidth);
    const height = Math.max(1, containerRef.current.clientHeight);

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    const bgColor = isDark ? 0x0a0f1d : 0xf1f5f9;
    scene.background = new THREE.Color(bgColor);
    scene.fog = new THREE.FogExp2(bgColor, copperCreek ? 0.00065 : 0.0025);

    const camera = new THREE.PerspectiveCamera(45, width / height, 1, copperCreek ? 5000 : 3000);
    camera.position.set(220, 240, 260);

    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;

    // Ambient and Directional Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, isDark ? 0.8 : 1.0);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffeedd, isDark ? 1.4 : 1.2);
    dirLight1.position.set(150, 300, 200);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x88bbff, 0.6);
    dirLight2.position.set(-150, 100, -200);
    scene.add(dirLight2);

    // Rectangular 20 m reference grid, separate from the last bench surface.
    const gridHelper = new THREE.GridHelper(
      copperCreek ? 900 : 400,
      copperCreek ? 45 : 20,
      isDark ? 0x334155 : 0x94a3b8,
      isDark ? 0x1e293b : 0xcbd5e1
    );
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Reference center for UTM coordinate centering in 3D scene
    const refX = referenceCenter?.[0] ?? 512490;
    const refY = referenceCenter?.[1] ?? 7416290;
    const refZ = copperCreek ? Math.min(...benches) : 3065;
    const verticalScale = copperCreek ? 2.6 : 2.0;

    // Coordinate Axes Helper (X=red, Y=green, Z=blue)
    const axesHelper = new THREE.AxesHelper(60);
    axesHelper.position.set(-180, 10, -180);
    scene.add(axesHelper);

    // Block Group
    const blockGroup = new THREE.Group();
    const blockMeshMap = new Map<THREE.Mesh, BlockModelItem>();

    const boxGeo = copperCreek
      ? new THREE.BoxGeometry(18, 12 * verticalScale - 1.5, 18)
      : new THREE.BoxGeometry(8.2, 8.2, 8.2);

    if (copperCreek) {
      const material = new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.08 });
      const mesh = new THREE.InstancedMesh(boxGeo, material, visibleBlocks.length);
      const instance = new THREE.Object3D();
      visibleBlocks.forEach((block, index) => {
        instance.position.set(block.x - refX, (block.z - refZ) * verticalScale, block.y - refY);
        instance.updateMatrix();
        mesh.setMatrixAt(index, instance.matrix);
        const color = colorMode === 'CU_BASE'
          ? getGradeColor(copperCreek ? block.cu_idw3 ?? block.cu_base : block.cu_base)
          : colorMode === 'UNCERTAINTY'
            ? getUncertaintyColor(block.epistemic_unc)
            : getGradeColor(block.cu_bayesian);
        mesh.setColorAt(index, block.id === activeSelectedId ? new THREE.Color(0xffd700) : color);
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      blockGroup.add(mesh);
    } else visibleBlocks.forEach(b => {
      let color: THREE.Color;
      let roughness = 0.35;
      let metalness = 0.15;
      let emissive = new THREE.Color(0, 0, 0);
      let opacity = 1.0;
      let transparent = false;

      if (colorMode === 'DESPACHO_SIMULATION') {
        const isProcessed = simProcessedRef.current.has(b.id);
        const destiny = classifyBlocks.get(b.id);
        if (!isProcessed) {
          // Not yet processed — dimmed / wireframe-like
          color = new THREE.Color(0.5, 0.5, 0.55);
          opacity = 0.25;
          transparent = true;
          roughness = 0.8;
          metalness = 0.0;
        } else if (destiny === 'PLANT') {
          // To plant — golden / green glow
          color = new THREE.Color(0.15, 0.85, 0.35);
          emissive = new THREE.Color(0.05, 0.3, 0.05);
          roughness = 0.2;
          metalness = 0.4;
        } else {
          // To waste — red / grey
          color = new THREE.Color(0.75, 0.25, 0.25);
          roughness = 0.7;
          metalness = 0.05;
        }
      } else {
        switch (colorMode) {
          case 'CU_BAYESIAN': color = getGradeColor(b.cu_bayesian ?? 0); break;
          case 'CU_BASE': color = getGradeColor(copperCreek ? b.cu_idw3 ?? b.cu_base : b.cu_base ?? 0); break;
          case 'UNCERTAINTY': color = getUncertaintyColor(b.epistemic_unc ?? 0); break;
          case 'JORC_CATEGORY': color = getJorcColor(b.category ?? ''); break;
          case 'LITHOLOGY': color = getLithologyColor(b.lithology ?? ''); break;
          case 'HYPERSPECTRAL': color = getHyperspectralColor(b.hyperspectral_mineral ?? ''); break;
          default: color = getGradeColor(b.cu_bayesian ?? 0);
        }
      }

      const isSelected = activeSelectedId === b.id;
      if (isSelected) {
        emissive = new THREE.Color(0.5, 0.4, 0.05);
        roughness = 0.1;
        metalness = 0.5;
      }

      const mat = new THREE.MeshStandardMaterial({
        color: color,
        roughness: isSelected ? 0.1 : roughness,
        metalness: isSelected ? 0.5 : metalness,
        emissive: isSelected ? new THREE.Color(0.5, 0.4, 0.05) : emissive,
        transparent: transparent,
        opacity: opacity,
        depthWrite: !transparent,
      });

      const mesh = new THREE.Mesh(boxGeo, mat);
      const posX = (b.x ?? refX) - refX;
      const posY = (b.y ?? refY) - refY;
      const posZ = ((b.z ?? refZ) - refZ) * verticalScale;
      mesh.position.set(posX, posZ, posY);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      // Add visible edges to ALL blocks for clarity
      const edges = new THREE.EdgesGeometry(boxGeo);
      const edgeColor = isSelected ? 0xffd700 : (isDark ? 0x334155 : 0x94a3b8);
      const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: edgeColor, linewidth: 1 }));
      mesh.add(line);

      if (isSelected) {
        mesh.scale.set(1.25, 1.25, 1.25);
        // Add a glow ring around selected block
        const glowGeo = new THREE.BoxGeometry(9.5, 9.5, 9.5);
        const glowMat = new THREE.MeshBasicMaterial({
          color: 0xffd700,
          transparent: true,
          opacity: 0.15,
          depthWrite: false,
        });
        const glowMesh = new THREE.Mesh(glowGeo, glowMat);
        mesh.add(glowMesh);
      }

      blockGroup.add(mesh);
      blockMeshMap.set(mesh, b);
      blockMeshesRef.current.set(b.id, mesh);
    });
    scene.add(blockGroup);

    // Pit Irregular Bench Steps — Organic contour-like shapes
    const pitMeshes: THREE.Mesh[] = [];
    if (showPitWireframe) {
      const segments = 96;
      const crestZ = copperCreek ? Math.max(...benches) : 3200;
      const floorZ = refZ;

      // Color gradient helper (light top → dark bottom)
      const getLevelColor = (t: number): number => {
        const topColor = new THREE.Color(isDark ? 0xd6d3d1 : 0xe7e5e4);
        const bottomColor = new THREE.Color(isDark ? 0x57534e : 0x78716c);
        const c = topColor.clone().lerp(bottomColor, t);
        return c.getHex();
      };

      // Bench contour line color — soft slate, clearly visible in light mode (never black)
      const getContourColor = (t: number): number => {
        const topColor = new THREE.Color(isDark ? 0x8a93a1 : 0x94a3b8);
        const bottomColor = new THREE.Color(isDark ? 0x6b7280 : 0x64748b);
        const c = topColor.clone().lerp(bottomColor, t);
        return c.getHex();
      };

      // Build the pit from an array of PitLevel (points in LOCAL coordinates, y=0)
      const buildPitFromLevels = (levels: PitLevel[]) => {
        if (levels.length < 2) return;
        const nLevels = levels.length;
        const levelShapes = levels.map(l => l.points);

        // Walls connecting each pair of levels
        for (let i = 0; i < nLevels - 1; i++) {
          const topShape = levelShapes[i];
          const bottomShape = levelShapes[i + 1];
          const topY = (levels[i].bench - refZ) * verticalScale;
          const bottomY = (levels[i + 1].bench - refZ) * verticalScale;
          const tMid = (i + 0.5) / (nLevels - 1);

          const topLen = topShape.length;
          const bottomLen = bottomShape.length;
          if (topLen < 3 || bottomLen < 3) continue;

          const wallVertices: number[] = [];
          const wallIndices: number[] = [];
          const count = Math.max(topLen, bottomLen);
          for (let j = 0; j <= count; j++) {
            const tIdx = j % topLen;
            const bIdx = j % bottomLen;
            wallVertices.push(topShape[tIdx].x, topY, topShape[tIdx].z);
            wallVertices.push(bottomShape[bIdx].x, bottomY, bottomShape[bIdx].z);
          }
          for (let j = 0; j < count; j++) {
            const tl = j * 2;
            const bl = j * 2 + 1;
            const tr = (j + 1) * 2;
            const br = (j + 1) * 2 + 1;
            wallIndices.push(tl, bl, tr);
            wallIndices.push(tr, bl, br);
          }
          const wallGeo = new THREE.BufferGeometry();
          wallGeo.setAttribute('position', new THREE.Float32BufferAttribute(wallVertices, 3));
          wallGeo.setIndex(wallIndices);
          wallGeo.computeVertexNormals();
          const wallMat = new THREE.MeshBasicMaterial({
            color: getLevelColor(tMid),
            transparent: true,
            opacity: isDark ? 0.10 : 0.18,
            side: THREE.DoubleSide,
          });
          const wallMesh = new THREE.Mesh(wallGeo, wallMat);
          scene.add(wallMesh);
          pitMeshes.push(wallMesh);

          // Top edge line (fine contour line)
          const edgeGeo = new THREE.BufferGeometry().setFromPoints(topShape);
          const edgeMat = new THREE.LineBasicMaterial({ color: getContourColor(i / (nLevels - 1)), linewidth: 1 });
          const edgeLine = new THREE.LineLoop(edgeGeo, edgeMat);
          edgeLine.position.y = topY;
          scene.add(edgeLine);
        }

        // Bottom edge line
        const bottomShape = levelShapes[nLevels - 1];
        const bottomY = (levels[nLevels - 1].bench - refZ) * verticalScale;
        if (bottomShape.length >= 3) {
          const bottomEdgeGeo = new THREE.BufferGeometry().setFromPoints(bottomShape);
          const bottomEdgeMat = new THREE.LineBasicMaterial({ color: getContourColor(1.0), linewidth: 1 });
          const bottomEdgeLine = new THREE.LineLoop(bottomEdgeGeo, bottomEdgeMat);
          bottomEdgeLine.position.y = bottomY;
          scene.add(bottomEdgeLine);

          // The filled surface follows the last bench; the rectangular grid
          // remains a separate reference plane around it.
          const floorShape2D = new THREE.Shape(bottomShape.map(p => new THREE.Vector2(p.x, p.z)));
          const floorGeo = new THREE.ShapeGeometry(floorShape2D);
          const floorMat = new THREE.MeshBasicMaterial({
            color: copperCreek ? (isDark ? 0x263447 : 0xd5dfe9) : getLevelColor(1.0),
            transparent: true,
            opacity: copperCreek ? (isDark ? 0.55 : 0.6) : (isDark ? 0.15 : 0.25),
            side: THREE.DoubleSide,
            depthWrite: !copperCreek,
          });
          const floorMesh = new THREE.Mesh(floorGeo, floorMat);
          floorMesh.rotation.x = Math.PI / 2;
          floorMesh.position.y = bottomY - 0.5;
          scene.add(floorMesh);
          pitMeshes.push(floorMesh);
        }

        // Bench elevation labels — always-visible sprites at the right side of each level
        const createTextSprite = (text: string, color: string, bgColor: string): THREE.Sprite => {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d')!;
          const fontSize = 48;
          ctx.font = `bold ${fontSize}px monospace`;
          const textWidth = ctx.measureText(text).width;
          const padding = 16;
          canvas.width = textWidth + padding * 2;
          canvas.height = fontSize + padding;

          ctx.fillStyle = bgColor;
          ctx.beginPath();
          ctx.roundRect(0, 0, canvas.width, canvas.height, 8);
          ctx.fill();

          ctx.font = `bold ${fontSize}px monospace`;
          ctx.fillStyle = color;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(text, canvas.width / 2, canvas.height / 2);

          const texture = new THREE.CanvasTexture(canvas);
          texture.minFilter = THREE.LinearFilter;
          const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.9 });
          const sprite = new THREE.Sprite(spriteMat);
          sprite.scale.set(canvas.width * 0.08, canvas.height * 0.08, 1);
          return sprite;
        };

        const labelColor = isDark ? '#e7e5e4' : '#1c1917';
        const labelBg = isDark ? 'rgba(28, 25, 23, 0.75)' : 'rgba(231, 229, 228, 0.85)';

        for (let i = 0; i < nLevels; i++) {
          const shape = levelShapes[i];
          if (shape.length === 0) continue;
          const y = (levels[i].bench - refZ) * verticalScale;
          let maxX = -Infinity;
          let maxZ = 0;
          for (const p of shape) {
            if (p.x > maxX) {
              maxX = p.x;
              maxZ = p.z;
            }
          }
          const label = createTextSprite(`${Math.round(levels[i].bench)} msnm`, labelColor, labelBg);
          label.position.set(maxX + 18, y, maxZ);
          scene.add(label);
        }

        // Invisible hit-test meshes approximated by cylinders per level band
        for (let i = 0; i < nLevels - 1; i++) {
          const topShape = levelShapes[i];
          const bottomShape = levelShapes[i + 1];
          if (topShape.length < 3 || bottomShape.length < 3) continue;
          const topY2 = (levels[i].bench - refZ) * verticalScale;
          const bottomY2 = (levels[i + 1].bench - refZ) * verticalScale;
          let maxR = 0;
          topShape.forEach(p => maxR = Math.max(maxR, Math.sqrt(p.x * p.x + p.z * p.z)));
          bottomShape.forEach(p => maxR = Math.max(maxR, Math.sqrt(p.x * p.x + p.z * p.z)));
          const hitGeo = new THREE.CylinderGeometry(maxR, maxR, Math.abs(topY2 - bottomY2), 32, 1, true);
          const hitMat = new THREE.MeshBasicMaterial({ visible: false });
          const hitMesh = new THREE.Mesh(hitGeo, hitMat);
          hitMesh.position.set(0, (topY2 + bottomY2) / 2, 0);
          scene.add(hitMesh);
          pitMeshes.push(hitMesh);
        }
      };

      if (pitMode === 'REFERENCE' && referencePitLevels?.length) {
        const levels: PitLevel[] = referencePitLevels.map(level => ({
          bench: level.bench,
          points: level.points.map(([x, y]) => new THREE.Vector3(x - refX, 0, y - refY)),
        }));
        buildPitFromLevels(levels);
      } else if (pitMode === 'PROCEDURAL') {
        // Procedural pit: organic irregular contours around centered circles
        const pitSteps = 10;
        const crestRadius = 240;
        const floorRadius = 60;

        const generateIrregularShape = (radius: number, seed: number): THREE.Vector3[] => {
          const points: THREE.Vector3[] = [];
          for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            const variation =
              Math.sin(angle * 3 + seed) * 0.12 +
              Math.sin(angle * 7 + seed * 1.7) * 0.06 +
              Math.sin(angle * 11 + seed * 2.3) * 0.03 +
              Math.sin(angle * 17 + seed * 3.1) * 0.015;
            const r = radius * (1 + variation);
            points.push(new THREE.Vector3(Math.cos(angle) * r, 0, Math.sin(angle) * r));
          }
          return points;
        };

        const levels: PitLevel[] = [];
        for (let i = 0; i < pitSteps; i++) {
          const t = i / (pitSteps - 1);
          const radius = crestRadius - t * (crestRadius - floorRadius);
          const bench = Math.round(crestZ - t * (crestZ - floorZ));
          levels.push({ bench, points: generateIrregularShape(radius, i * 13.7 + 1.3) });
        }
        buildPitFromLevels(levels);
      } else if (pitMode === 'REALISTIC') {
        // Realistic porphyry example pit — convert absolute coords to local
        const levels: PitLevel[] = REALISTIC_PIT_DATA.map(l => ({
          bench: l.bench,
          points: l.points.map(p => new THREE.Vector3(p.x, 0, p.y)),
        }));
        buildPitFromLevels(levels);
      } else if (pitMode === 'IMPORTED' && importedPitLevels.length >= 2) {
        // User-imported pit from CSV/mining data (absolute coords → local)
        const levels: PitLevel[] = importedPitLevels.map(l => ({
          bench: l.bench,
          points: l.points.map(p => new THREE.Vector3(p.x - refX, 0, p.y - refY)),
        }));
        buildPitFromLevels(levels);
      }
    }

    // Drillholes Visualizer
    const drillholeCollarMap = new Map<THREE.Mesh, Drillhole>();
    if (showDrillholes) {
      const drillGroup = new THREE.Group();
      drillholes.forEach(dh => {
        if (copperCreek) {
          if (!dh.trace || dh.trace.length < 2) return;
          const points = dh.trace.map(([x, y, z]) => new THREE.Vector3(x - refX, (z - refZ) * verticalScale, y - refY));
          const line = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints(points),
            new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.75 })
          );
          drillGroup.add(line);
          const startMarker = new THREE.Mesh(
            new THREE.SphereGeometry(2.5, 10, 10),
            new THREE.MeshBasicMaterial({ color: (dh.trace_start_depth_m ?? 0) === 0 ? 0xf59e0b : 0x38bdf8 })
          );
          startMarker.position.copy(points[0]);
          drillGroup.add(startMarker);
          drillholeCollarMap.set(startMarker, dh);
          return;
        }
        const posX = ((dh.x ?? (dh as any).collar_x) ?? refX) - refX;
        const posY = ((dh.y ?? (dh as any).collar_y) ?? refY) - refY;
        const posZ = (((dh.z ?? (dh as any).collar_z) ?? refZ) - refZ) * verticalScale;
        const depth = dh.total_depth_m ?? 50;
        const azRad = ((dh.azimuth ?? 0) * Math.PI) / 180;
        const dipRad = ((dh.dip ?? -90) * Math.PI) / 180;

        const startVec = new THREE.Vector3(posX, posZ, posY);
        const endX = posX - Math.sin(azRad) * (Math.abs(Math.cos(dipRad)) * depth * 0.4 || 15);
        const endZ = posZ + (Math.sin(dipRad) * depth * 0.8);
        const endY = posY - Math.cos(azRad) * (Math.abs(Math.cos(dipRad)) * depth * 0.4 || 15);
        const endVec = new THREE.Vector3(endX, endZ, endY);

        const lineGeo = new THREE.BufferGeometry().setFromPoints([startVec, endVec]);
        const lineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2 });
        const line = new THREE.Line(lineGeo, lineMat);
        drillGroup.add(line);

        const collarGeo = new THREE.SphereGeometry(3.0, 12, 12);
        const collarMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
        const collarMesh = new THREE.Mesh(collarGeo, collarMat);
        collarMesh.position.copy(startVec);
        drillGroup.add(collarMesh);
        drillholeCollarMap.set(collarMesh, dh);
      });
      scene.add(drillGroup);
    }

    // Camera Orbit Controls
    const sph = sphericalRef.current;
    const target = cameraTargetRef.current;
    if (copperCreek && !copperCameraInitialized.current) {
      sph.radius = Math.min(2500, 1300 * Math.max(1, 1.3 / (width / height)));
      target.set(0, (Math.max(...benches) - refZ) * verticalScale * 0.55, 0);
      copperCameraInitialized.current = true;
    }

    const updateCameraPosition = () => {
      camera.position.setFromSpherical(sph).add(target);
      camera.position.y += camHeightOffsetRef.current;
      camera.lookAt(target);
    };
    updateCameraPosition();
    updateCameraRef.current = updateCameraPosition;

    const onMouseDown = (e: MouseEvent) => {
      if (e.button === 0) {
        isDraggingRef.current = true;
        prevMouseRef.current = { x: e.clientX, y: e.clientY };
      }
    };

    const onMouseUp = () => {
      isDraggingRef.current = false;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (isDraggingRef.current) {
        const deltaX = e.clientX - prevMouseRef.current.x;
        const deltaY = e.clientY - prevMouseRef.current.y;

        sph.theta -= deltaX * 0.006;
        sph.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, sph.phi - deltaY * 0.006));

        updateCameraPosition();
        prevMouseRef.current = { x: e.clientX, y: e.clientY };
      }

      if (!isDraggingRef.current && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, camera);

        // Priority 1: Blocks
        const blockIntersects = raycaster.intersectObjects(blockGroup.children, true);
        if (blockIntersects.length > 0) {
          let topMesh = blockIntersects[0].object as THREE.Mesh;
          if (!blockMeshMap.has(topMesh) && topMesh.parent && blockMeshMap.has(topMesh.parent as THREE.Mesh)) {
            topMesh = topMesh.parent as THREE.Mesh;
          }
          const matched = copperCreek && topMesh instanceof THREE.InstancedMesh
            ? visibleBlocks[blockIntersects[0].instanceId ?? -1]
            : blockMeshMap.get(topMesh);
          if (matched) {
            setHoveredBlock(matched);
            setHoveredDrillhole(null);
            setHoveredPit(false);
            setTooltipPos({ x: Math.min(e.clientX - rect.left + 15, rect.width - 290), y: Math.max(10, e.clientY - rect.top - 140) });
            return;
          }
        }

        // Priority 2: Drillhole collars
        if (drillholeCollarMap.size > 0) {
          const collarIntersects = raycaster.intersectObjects(Array.from(drillholeCollarMap.keys()), false);
          if (collarIntersects.length > 0) {
            const matched = drillholeCollarMap.get(collarIntersects[0].object as THREE.Mesh);
            if (matched) {
              setHoveredBlock(null);
              setHoveredDrillhole(matched);
              setHoveredPit(false);
              setTooltipPos({ x: Math.min(e.clientX - rect.left + 15, rect.width - 260), y: Math.max(10, e.clientY - rect.top - 100) });
              return;
            }
          }
        }

        // Priority 3: Pit bench rings
        if (pitMeshes.length > 0) {
          const pitIntersects = raycaster.intersectObjects(pitMeshes, false);
          if (pitIntersects.length > 0) {
            setHoveredBlock(null);
            setHoveredDrillhole(null);
            setHoveredPit(true);
            setTooltipPos({ x: Math.min(e.clientX - rect.left + 15, rect.width - 220), y: Math.max(10, e.clientY - rect.top - 80) });
            return;
          }
        }

        // Nothing hovered
        setHoveredBlock(null);
        setHoveredDrillhole(null);
        setHoveredPit(false);
        setTooltipPos(null);
      }
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      sph.radius = Math.max(80, Math.min(copperCreek ? 2500 : 900, sph.radius + e.deltaY * 0.4));
      updateCameraPosition();
    };

    const onClick = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(blockGroup.children, true);
      if (intersects.length > 0) {
        let topMesh = intersects[0].object as THREE.Mesh;
        if (!blockMeshMap.has(topMesh) && topMesh.parent && blockMeshMap.has(topMesh.parent as THREE.Mesh)) {
          topMesh = topMesh.parent as THREE.Mesh;
        }
        const matched = copperCreek && topMesh instanceof THREE.InstancedMesh
          ? visibleBlocks[intersects[0].instanceId ?? -1]
          : blockMeshMap.get(topMesh);
        if (matched && onSelectBlock) {
          onSelectBlock(matched);
        }
      }
    };

    const canvasElem = canvasRef.current;
    canvasElem.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mouseup', onMouseUp);
    canvasElem.addEventListener('mousemove', onMouseMove);
    canvasElem.addEventListener('wheel', onWheel, { passive: false });
    canvasElem.addEventListener('click', onClick);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(containerRef.current);
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      canvasElem.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mouseup', onMouseUp);
      canvasElem.removeEventListener('mousemove', onMouseMove);
      canvasElem.removeEventListener('wheel', onWheel);
      canvasElem.removeEventListener('click', onClick);
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      renderer.dispose();
      blockMeshesRef.current.clear();
      sceneRef.current = null;
      trajectoryGroupRef.current = null;
      if (audioCtxRef.current) {
        audioCtxRef.current.close();
        audioCtxRef.current = null;
      }
    };
  }, [visibleBlocks, drillholes, colorMode, showDrillholes, showPitWireframe, activeSelectedId, isDark, pitMode, importedPitLevels, copperCreek, referenceCenter, referencePitLevels]);

  return (
    <div
      ref={viewerRef}
      className={`
        relative w-full min-h-0 flex flex-col bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xl
        ${isFullscreen ? 'fixed inset-0 z-[100] rounded-none border-0 h-screen' : hasAttachedFooter ? 'h-full rounded-t-2xl border-b-0' : 'h-full rounded-2xl'}
      `}
    >
      
      {/* 3D Viewport Controls Bar */}
      <div className="shrink-0 flex flex-wrap items-center justify-between gap-2 sm:gap-3 px-3 sm:px-4 py-3 bg-white/90 dark:bg-slate-900/90 backdrop-blur border-b border-slate-200 dark:border-slate-800 z-10">
        <div className="min-w-0 flex flex-wrap items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <h2 className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 font-display tracking-wide uppercase">
            <Layers className="w-4 h-4 text-amber-500" />
            {copperCreek ? 'Copper Creek · Mammoth (reconstrucción)' : 'Gemelo Digital 3D - Modelo de Bloques & Rajo'}
          </h2>
          <span className="px-2 py-0.5 text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700">
            {visibleBlocks.length} Bloques
          </span>
        </div>

        {/* Color Mapping Mode Selector */}
        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-950 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs overflow-x-auto max-w-full">
          <span className="text-slate-500 dark:text-slate-400 px-1.5 font-medium hidden sm:inline shrink-0">Modo:</span>

          <button
            onClick={() => setColorMode('CU_BAYESIAN')}
            className={`px-2 py-1 rounded-lg transition-all font-medium text-[11px] sm:text-xs shrink-0 ${
              colorMode === 'CU_BAYESIAN'
                ? 'bg-amber-500 text-slate-950 shadow-sm font-bold'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            {copperCreek ? `Ley Cu · ${copperCreekModelName}` : 'Ley Cu Bayesiana'}
          </button>

          <button
            onClick={() => setColorMode('CU_BASE')}
            className={`px-2 py-1 rounded-lg transition-all font-medium text-[11px] sm:text-xs shrink-0 ${
              colorMode === 'CU_BASE'
                ? 'bg-amber-500 text-slate-950 shadow-sm font-bold'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            {copperCreek ? 'IDW3 de referencia' : 'Kriging Base'}
          </button>

          <button
            onClick={() => setColorMode('UNCERTAINTY')}
            className={`px-2 py-1 rounded-lg transition-all font-medium text-[11px] sm:text-xs shrink-0 ${
              colorMode === 'UNCERTAINTY'
                ? 'bg-amber-500 text-slate-950 shadow-sm font-bold'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            {copperCreek ? 'Variación entre sondajes' : 'Incertidumbre (σ)'}
          </button>

          {!copperCreek && <button
            onClick={() => setColorMode('JORC_CATEGORY')}
            className={`px-2 py-1 rounded-lg transition-all font-medium text-[11px] sm:text-xs shrink-0 ${
              colorMode === 'JORC_CATEGORY'
                ? 'bg-amber-500 text-slate-950 shadow-sm font-bold'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            JORC
          </button>}

          {!copperCreek && <button
            onClick={() => setColorMode('LITHOLOGY')}
            className={`px-2 py-1 rounded-lg transition-all font-medium text-[11px] sm:text-xs shrink-0 ${
              colorMode === 'LITHOLOGY'
                ? 'bg-amber-500 text-slate-950 shadow-sm font-bold'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            Litología
          </button>}

          {!copperCreek && <button
            onClick={() => setColorMode('DESPACHO_SIMULATION')}
            className={`px-2 py-1 rounded-lg transition-all font-medium text-[11px] sm:text-xs shrink-0 flex items-center gap-1 ${
              colorMode === 'DESPACHO_SIMULATION'
                ? 'bg-emerald-500 text-white shadow-sm font-bold'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            <Truck className="w-3 h-3" />
            Despacho
          </button>}
        </div>

        {/* Quick Layer Toggles & Fullscreen */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setShowDrillholes(!showDrillholes)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border transition-colors ${
              showDrillholes
                ? 'bg-blue-500/20 border-blue-500/40 text-blue-600 dark:text-blue-300 font-medium'
                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400'
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sondajes</span> ({drillholes.length})
          </button>

          <button
            onClick={() => setShowPitWireframe(!showPitWireframe)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border transition-colors ${
              showPitWireframe
                ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-700 dark:text-cyan-300 font-medium'
                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400'
            }`}
          >
            <Mountain className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Tajo</span>
          </button>

          {showPitWireframe && !copperCreek && (
            <select
              value={pitMode}
              onChange={(e) => setPitMode(e.target.value as PitMode)}
              className="px-2 py-1 rounded-lg text-xs border bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
              title="Modo de geometría del tajo"
            >
              <option value="PROCEDURAL">Tajo Procedural</option>
              <option value="REALISTIC">Tajo Realista Ejemplo</option>
              <option value="IMPORTED">Tajo Importado (CSV)</option>
            </select>
          )}
          {showPitWireframe && copperCreek && (
            <span className="px-2 py-1 rounded-lg text-xs border border-cyan-500/40 text-cyan-700 dark:text-cyan-300">Tajo Mammoth aproximado</span>
          )}

          {showPitWireframe && pitMode === 'IMPORTED' && (
            <button
              onClick={() => document.getElementById('pitImportPanel')?.classList.toggle('hidden')}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border transition-colors bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
              title="Importar tajo desde CSV"
            >
              <FileUp className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Importar</span>
            </button>
          )}

          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border transition-colors bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
            title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{isFullscreen ? 'Restaurar' : 'Expandir'}</span>
          </button>
        </div>
      </div>

      {/* Second Controls Bar — Bench & Cut-off Filters */}
      <div className="shrink-0 flex flex-wrap items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 bg-white/80 dark:bg-slate-900/80 backdrop-blur border-b border-slate-200 dark:border-slate-800 z-10">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium shrink-0">
            <Filter className="w-3 h-3 inline -mt-0.5 mr-0.5" />
            Banco:
          </span>
          <div className="flex flex-wrap gap-1">
            <button
              onClick={() => setSelectedBench('ALL')}
              className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-medium border ${
                selectedBench === 'ALL'
                  ? 'bg-amber-500 border-amber-400 text-slate-950 font-bold'
                  : 'bg-slate-100 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-400'
              }`}
            >
              Todos
            </button>
            {benches.map(b => (
              <button
                key={b}
                onClick={() => setSelectedBench(b)}
                className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-medium border ${
                  selectedBench === b
                    ? 'bg-amber-500 border-amber-400 text-slate-950 font-bold'
                    : 'bg-slate-100 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-400'
                }`}
              >
                {b}m
              </button>
            ))}
          </div>
        </div>

        <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 hidden sm:block" />

        <div className="flex items-center gap-2 flex-1 min-w-[200px] max-w-xs">
          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium shrink-0">{copperCreek ? 'Filtro Cu:' : 'Cut-off Cu:'}</span>
          <input
            type="range"
            min="0.0"
            max="1.20"
            step="0.05"
            value={cutOffFilter}
            onChange={e => setCutOffFilter(parseFloat(e.target.value))}
            className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
          <span className="text-[10px] font-mono text-amber-600 dark:text-amber-400 font-bold w-14 text-right">{cutOffFilter.toFixed(2)}%</span>
        </div>
      </div>

      {/* Main 3D Canvas Container */}
      <div ref={containerRef} className="relative flex-1 min-h-0 w-full overflow-hidden cursor-grab active:cursor-grabbing">
        <canvas ref={canvasRef} className="block w-full h-full" />

        {/* Overlay Floating Controls (Legend only) */}
        <div className="absolute top-3 left-3 flex flex-col gap-2 max-w-[280px] sm:max-w-xs z-10">
          {/* Color Scale Legend */}
          <div className={`bg-white/95 dark:bg-slate-900/95 backdrop-blur p-3 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl text-xs ${copperCreek ? 'min-w-[240px]' : ''}`}>
            <div className="font-semibold text-slate-800 dark:text-slate-200 mb-1.5 font-display flex items-center justify-between">
              <span>Leyenda: {copperCreek ? (colorMode === 'CU_BASE' ? 'IDW3 de referencia' : colorMode === 'UNCERTAINTY' ? 'Dispersión vecina' : `Ley Cu ${copperCreekModelName}`) : colorMode.replace('_', ' ')}</span>
            </div>

            {colorMode === 'DESPACHO_SIMULATION' ? (
              <div className="flex flex-col gap-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-emerald-500 inline-block shadow-sm" />
                  <span className="text-slate-700 dark:text-slate-300 font-medium">A Planta</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-red-500 inline-block shadow-sm" />
                  <span className="text-slate-700 dark:text-slate-300 font-medium">A Botadero</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-slate-400 inline-block opacity-40" />
                  <span className="text-slate-500 dark:text-slate-400">Pendiente de evaluar</span>
                </div>
                <div className="mt-1 pt-1.5 border-t border-slate-200 dark:border-slate-800 text-[10px] text-slate-500 dark:text-slate-400">
                  Estrategia: {strategy === 'CUT_OFF' ? (econState ? 'Cut-off Económico (por banco)' : 'Cut-off Rígido') : strategy === 'ECON_NSR' ? 'Económico NSR' : strategy === 'MAX_GRADE' ? 'Ley Máxima' : strategy === 'BLEND_TARGET' ? 'Mezcla Controlada' : 'Mínima Incertidumbre'}
                </div>
              </div>
            ) : colorMode === 'CU_BAYESIAN' || colorMode === 'CU_BASE' ? (
              <div>
                <div className="h-2.5 w-full rounded bg-gradient-to-r from-blue-600 via-emerald-500 via-amber-400 to-red-600 border border-slate-300 dark:border-slate-700" />
                <div className="flex justify-between text-[10px] font-mono text-slate-500 dark:text-slate-400 mt-1">
                  <span>{copperCreek ? '< 0.13%' : '< 0.20%'}</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">{projectCutOff}%</span>
                  <span>{copperCreek ? '0.45%' : '0.80%'}</span>
                  <span className="text-red-500 font-bold">{copperCreek ? '> 0.80%' : '> 1.40%'}</span>
                </div>
              </div>
            ) : colorMode === 'UNCERTAINTY' ? (
              <div>
                <div className="h-2.5 w-full rounded bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-600 border border-slate-300 dark:border-slate-700" />
                <div className="flex justify-between text-[10px] font-mono text-slate-500 dark:text-slate-400 mt-1">
                  <span className="text-emerald-600 dark:text-emerald-400">{copperCreek ? 'Menor dispersión' : 'Baja (σ < 0.08)'}</span>
                  <span className="text-amber-600 dark:text-amber-400">Media</span>
                  <span className="text-rose-500 font-bold">{copperCreek ? 'Mayor dispersión' : 'Alta (σ > 0.25)'}</span>
                </div>
              </div>
            ) : colorMode === 'JORC_CATEGORY' ? (
              <div className="flex flex-col gap-1 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-emerald-500 inline-block" />
                  <span className="text-slate-700 dark:text-slate-300">Medido (Measured)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block" />
                  <span className="text-slate-700 dark:text-slate-300">Indicado (Indicated)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block" />
                  <span className="text-slate-700 dark:text-slate-300">Inferido (Inferred)</span>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-1 text-[10px]">
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-fuchsia-500" /><span>Brecha</span></div>
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-amber-500" /><span>Pórfido</span></div>
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-cyan-500" /><span>Skarn</span></div>
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-slate-500" /><span>Andesita</span></div>
              </div>
            )}
          </div>

          {/* Estimación Económica — debajo de la Leyenda, solo modo Despacho */}
          {colorMode === 'DESPACHO_SIMULATION' && (simMoney.revenue > 0 || simMoney.cost > 0) && (
            <div className="bg-white/95 dark:bg-slate-900/95 backdrop-blur p-3 rounded-xl border border-blue-200 dark:border-blue-800 shadow-xl text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200 font-display mb-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                Estimación Económica
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-[10px]">
                  <span className="text-slate-500 dark:text-slate-400">Ingresos (planta):</span>
                  <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">${(simMoney.revenue / 1000).toFixed(1)}k</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-slate-500 dark:text-slate-400">Costo de extracción (minado):</span>
                  <span className="font-mono text-red-500 font-bold">-${(simMoney.extraction / 1000).toFixed(1)}k</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-slate-500 dark:text-slate-400">Costo de procesamiento:</span>
                  <span className="font-mono text-red-500 font-bold">-${(simMoney.processing / 1000).toFixed(1)}k</span>
                </div>
                <div className="border-t border-blue-200 dark:border-blue-800 pt-1 mt-1 flex justify-between text-[11px]">
                  <span className="text-slate-700 dark:text-slate-300 font-semibold">Neto estimado:</span>
                  <span className={`font-mono font-bold ${simMoney.net >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500'}`}>
                    ${(simMoney.net / 1000).toFixed(1)}k
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Slider vertical de subida/bajada de cámara — sobre la guía de navegación */}
        <div className="absolute bottom-16 left-3 z-10 flex flex-col items-center gap-1 bg-white/95 dark:bg-slate-900/95 backdrop-blur p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl">
          <span className="text-[9px] font-mono font-semibold text-slate-600 dark:text-slate-300">Cámara ⬆</span>
          <input
            type="range"
            min={0}
            max={100}
            value={camHeightVal}
            onChange={e => handleCamHeightChange(Number(e.target.value))}
            aria-label="Subir y bajar cámara"
            className="h-36 accent-amber-500 cursor-pointer"
            style={{ WebkitAppearance: 'slider-vertical' as any, writingMode: 'vertical-lr' }}
          />
          <span className="text-[9px] font-mono text-slate-500 dark:text-slate-400">⬇</span>
        </div>

        {/* Simulation Control Panel — Bottom Right, compact */}
        {colorMode === 'DESPACHO_SIMULATION' && (
          <div className="absolute bottom-3 right-3 z-20 bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-emerald-500/50 rounded-2xl shadow-2xl text-xs w-72 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 bg-emerald-500/10 border-b border-emerald-500/20">
              <div className="flex items-center gap-1.5">
                <Truck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="font-bold text-emerald-700 dark:text-emerald-300">Simulación de Despacho</span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                {Math.round((simProgress / Math.max(visibleBlocks.length, 1)) * 100)}%
              </span>
            </div>
            <div className="px-3 py-2 space-y-2">
              {/* Strategy Selector */}
              <div>
                <label className="text-[10px] font-medium text-slate-600 dark:text-slate-400 mb-1 block">Estrategia:</label>
                <select
                  value={strategy}
                  onChange={e => { setStrategy(e.target.value as DispatchStrategy); resetSimulation(); }}
                  className="w-full px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                >
                  <option value="CUT_OFF">{econState ? 'Cut-off Económico (por banco)' : 'Cut-off Rígido'}</option>
                  <option value="ECON_NSR">Económico NSR</option>
                  <option value="MAX_GRADE">Ley Máxima</option>
                  <option value="BLEND_TARGET">Mezcla Controlada</option>
                  <option value="MIN_UNCERTAINTY">Mínima Incertidumbre</option>
                </select>
              </div>

              {/* Strategy Config Toggle */}
              {(strategy === 'MAX_GRADE' || strategy === 'BLEND_TARGET' || strategy === 'MIN_UNCERTAINTY') && (
                <div>
                  <button
                    onClick={() => setShowStrategyConfig(!showStrategyConfig)}
                    className="flex items-center gap-1 text-[10px] text-slate-500 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                  >
                    <Settings2 className="w-3 h-3" />
                    {showStrategyConfig ? 'Ocultar configuración' : 'Configurar parámetros'}
                  </button>
                  {showStrategyConfig && (
                    <div className="mt-1.5 space-y-1.5 bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg p-2">
                      {(strategy === 'MAX_GRADE' || strategy === 'MIN_UNCERTAINTY') && (
                        <div>
                          <div className="flex justify-between text-[10px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Capacidad diaria:</span>
                            <span className="font-mono text-emerald-600 dark:text-emerald-400">{strategyConfig.capacityTonnes.toLocaleString()} t</span>
                          </div>
                          <input
                            type="range"
                            min="10000"
                            max="500000"
                            step="10000"
                            value={strategyConfig.capacityTonnes}
                            onChange={e => setStrategyConfig(c => ({ ...c, capacityTonnes: parseInt(e.target.value) }))}
                            className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                          />
                        </div>
                      )}
                      {strategy === 'BLEND_TARGET' && (
                        <>
                          <div>
                            <div className="flex justify-between text-[10px] text-slate-600 dark:text-slate-400 mb-0.5">
                              <span>Ley objetivo:</span>
                              <span className="font-mono text-emerald-600 dark:text-emerald-400">{strategyConfig.targetGrade.toFixed(2)}% Cu</span>
                            </div>
                            <input
                              type="range"
                              min="0.20"
                              max="0.80"
                              step="0.05"
                              value={strategyConfig.targetGrade}
                              onChange={e => setStrategyConfig(c => ({ ...c, targetGrade: parseFloat(e.target.value) }))}
                              className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                            />
                          </div>
                          <div>
                            <div className="flex justify-between text-[10px] text-slate-600 dark:text-slate-400 mb-0.5">
                              <span>Tolerancia:</span>
                              <span className="font-mono text-emerald-600 dark:text-emerald-400">±{strategyConfig.blendTolerance.toFixed(2)}%</span>
                            </div>
                            <input
                              type="range"
                              min="0.05"
                              max="0.30"
                              step="0.05"
                              value={strategyConfig.blendTolerance}
                              onChange={e => setStrategyConfig(c => ({ ...c, blendTolerance: parseFloat(e.target.value) }))}
                              className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                            />
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Visual & Audio Toggles */}
              <div className="flex gap-2">
                <button
                  onClick={() => setShowTrajectories(!showTrajectories)}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg text-[10px] border transition-colors ${
                    showTrajectories
                      ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-700 dark:text-indigo-300 font-medium'
                      : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400'
                  }`}
                >
                  <Route className="w-3 h-3" />
                  Trayectorias
                </button>
                <button
                  onClick={() => setSoundEnabled(!soundEnabled)}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg text-[10px] border transition-colors ${
                    soundEnabled
                      ? 'bg-violet-500/20 border-violet-500/40 text-violet-700 dark:text-violet-300 font-medium'
                      : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400'
                  }`}
                >
                  {soundEnabled ? <Volume2 className="w-3 h-3" /> : <VolumeX className="w-3 h-3" />}
                  Sonido
                </button>
              </div>

              {/* Progress Bar */}
              <div>
                <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-100"
                    style={{ width: `${(simProgress / Math.max(visibleBlocks.length, 1)) * 100}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 font-mono">
                  <span>0</span>
                  <span>{simProgress} / {visibleBlocks.length}</span>
                </div>
              </div>

              {/* Stats — horizontal compact */}
              <div className="flex gap-2">
                <div className="flex-1 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold text-[10px]">
                    <Factory className="w-3 h-3" />
                    Planta
                  </div>
                  <div className="text-base font-bold text-emerald-600 dark:text-emerald-400 font-mono leading-tight">{simStats.toPlant}</div>
                  <div className="text-[9px] text-slate-500 dark:text-slate-400">
                    {(simStats.totalTonnesPlant / 1000).toFixed(1)}k t
                  </div>
                </div>
                <div className="flex-1 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1 text-red-700 dark:text-red-400 font-semibold text-[10px]">
                    <Trash2 className="w-3 h-3" />
                    Botadero
                  </div>
                  <div className="text-base font-bold text-red-600 dark:text-red-400 font-mono leading-tight">{simStats.toWaste}</div>
                  <div className="text-[9px] text-slate-500 dark:text-slate-400">
                    {(simStats.totalTonnesWaste / 1000).toFixed(1)}k t
                  </div>
                </div>
              </div>

              {/* Average Grade */}
              {simStats.toPlant > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1 text-amber-700 dark:text-amber-400 font-semibold text-[10px]">
                    <Target className="w-3 h-3" />
                    Ley Promedio a Planta
                  </div>
                  <div className="text-lg font-bold text-amber-600 dark:text-amber-400 font-mono leading-tight">{simStats.avgGradePlant.toFixed(3)}% Cu</div>
                </div>
              )}

              {/* Controls */}
              <div className="flex items-center gap-1.5">
                {simProgress >= visibleBlocks.length && visibleBlocks.length > 0 ? (
                  <button
                    onClick={resetSimulation}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Reiniciar
                  </button>
                ) : !isSimulating ? (
                  <button
                    onClick={startSimulation}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold transition-colors"
                  >
                    <Play className="w-3 h-3" />
                    {simProgress > 0 ? 'Continuar' : 'Iniciar'}
                  </button>
                ) : (
                  <button
                    onClick={pauseSimulation}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 text-[11px] font-semibold transition-colors"
                  >
                    <Pause className="w-3 h-3" />
                    Pausar
                  </button>
                )}
              </div>

              {/* Speed Control */}
              <div>
                <div className="flex justify-between text-[10px] font-medium text-slate-600 dark:text-slate-400 mb-0.5">
                  <span>Velocidad:</span>
                  <span className="font-mono text-emerald-600 dark:text-emerald-400">{simSpeed}x</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="1"
                  value={simSpeed}
                  onChange={e => setSimSpeed(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
              </div>

              {/* Export CSV */}
              {simProgress >= visibleBlocks.length && visibleBlocks.length > 0 && (
                <button
                  onClick={() => {
                    const rows = visibleBlocks.map(b => ({
                      id: b.id,
                      bench: b.bench,
                      x: b.x,
                      z: b.z,
                      cu_bayesian: b.cu_bayesian,
                      destiny: classifyBlocks.get(b.id) === 'PLANT' ? 'Planta' : 'Botadero',
                      tonnage: b.tonnage ?? 15000,
                    }));
                    const headers = ['Block ID', 'Banco', 'X', 'Z', 'Ley Cu Bayesian', 'Destino', 'Tonelaje (t)'];
                    const csv = [
                      headers.join(','),
                      ...rows.map(r => [r.id, r.bench, r.x, r.z, r.cu_bayesian, r.destiny, r.tonnage].join(','))
                    ].join('\n');
                    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `despacho_${strategy.toLowerCase()}_${new Date().toISOString().slice(0,10)}.csv`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Exportar CSV
                </button>
              )}
            </div>
          </div>
        )}

        {/* 3D Navigation Guide Pill */}
        <div className="absolute bottom-3 left-3 bg-white/90 dark:bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 font-mono flex items-center gap-2 sm:gap-3 shadow-md">
          <span>🖱️ Arrastrar: Rotar</span>
          <span>•</span>
          <span>📜 Scroll: Zoom</span>
          <span>•</span>
          <span>📍 Barra lateral: Subir/Bajar</span>
          <span>•</span>
          <span>🎯 Click: Seleccionar bloque</span>
        </div>

        {/* Hovered Block Telemetry Tooltip */}
        {hoveredBlock && tooltipPos && (
          <div 
            className="absolute pointer-events-none z-30 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-amber-500/50 rounded-2xl p-3.5 shadow-2xl text-xs w-72 transition-all duration-75"
            style={{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }}
          >
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2 mb-2">
              <span className="font-mono font-bold text-amber-600 dark:text-amber-400">{hoveredBlock.id}</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                Banco {hoveredBlock.bench}m
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] mb-2.5">
              <div>
                <span className="text-slate-500 dark:text-slate-400 block text-[10px]">{copperCreek ? `Ley Cu ${copperCreekModelName}:` : 'Ley Cu Fusión M-6:'}</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-bold font-mono text-sm">{copperCreek ? hoveredBlock.cu_bayesian.toFixed(4) : hoveredBlock.cu_bayesian}% Cu</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400 block text-[10px]">{copperCreek ? 'IDW3 referencia:' : 'Kriging Base:'}</span>
                <span className="text-slate-700 dark:text-slate-300 font-mono text-sm">{copperCreek ? (hoveredBlock.cu_idw3 ?? hoveredBlock.cu_base).toFixed(4) : hoveredBlock.cu_base}% Cu</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400 block text-[10px]">{copperCreek ? 'Dispersión vecina:' : 'Incertidumbre (σ):'}</span>
                <span className="text-amber-600 dark:text-amber-400 font-mono">{copperCreek ? hoveredBlock.epistemic_unc.toFixed(4) : `±${hoveredBlock.epistemic_unc}`}%</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400 block text-[10px]">{copperCreek ? 'Sondaje más cercano:' : 'P10-P90:'}</span>
                <span className="text-slate-700 dark:text-slate-300 font-mono">{copperCreek ? `${hoveredBlock.nearest_drillhole_m.toFixed(1)} m` : `[${hoveredBlock.p10}% - ${hoveredBlock.p90}%]`}</span>
              </div>
            </div>

            {!copperCreek && <div className="border-t border-slate-200 dark:border-slate-800 pt-2 space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Categoría JORC:</span>
                <span className={`font-semibold ${
                  hoveredBlock.category === 'Measured' ? 'text-emerald-600 dark:text-emerald-400' :
                  hoveredBlock.category === 'Indicated' ? 'text-amber-600 dark:text-amber-400' : 'text-rose-500'
                }`}>
                  {hoveredBlock.category}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Litología:</span>
                <span className="text-slate-800 dark:text-slate-200">{hoveredBlock.lithology}</span>
              </div>
            </div>}
            {copperCreek && <div className="border-t border-slate-200 dark:border-slate-800 pt-2 text-[10px] text-slate-500 dark:text-slate-400">
              <div className="flex justify-between gap-3 mb-1">
                <span>Sondajes de soporte:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">{hoveredBlock.support_holes ?? '—'}</span>
              </div>
              Estimación exploratoria; sin clasificación de recursos.
            </div>}
          </div>
        )}

        {/* Hovered Drillhole Tooltip */}
        {hoveredDrillhole && tooltipPos && (
          <div 
            className="absolute pointer-events-none z-30 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-blue-500/50 rounded-2xl p-3 shadow-2xl text-xs w-60 transition-all duration-75"
            style={{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }}
          >
            <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2 mb-2">
              <MapPin className="w-4 h-4 text-blue-500" />
              <span className="font-mono font-bold text-blue-600 dark:text-blue-400">{hoveredDrillhole.hole_id}</span>
            </div>
            <div className="space-y-1 text-[11px]">
              {copperCreek && <div className="text-cyan-600 dark:text-cyan-300">{(hoveredDrillhole.trace_start_depth_m ?? 0) > 0 ? `Tramo visible desde ${hoveredDrillhole.trace_start_depth_m} m de profundidad` : 'Collar y tramo visible'}</div>}
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Tipo:</span>
                <span className="text-slate-800 dark:text-slate-200">{hoveredDrillhole.type?.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Profundidad:</span>
                <span className="font-mono">{hoveredDrillhole.total_depth_m}m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Azimuth/Dip:</span>
                <span className="font-mono">{hoveredDrillhole.azimuth}° / {hoveredDrillhole.dip}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Collar Z:</span>
                <span className="font-mono">{hoveredDrillhole.z}m</span>
              </div>
            </div>
          </div>
        )}

        {/* Pit Import Panel — shown when IMPORTED mode + toggled via button */}
        {showPitWireframe && pitMode === 'IMPORTED' && (
          <div id="pitImportPanel" className="absolute bottom-24 right-3 z-20 hidden w-80 bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-cyan-500/50 rounded-2xl shadow-xl text-xs p-4 space-y-3">
            <div className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="font-bold text-cyan-700 dark:text-cyan-300">Importar Tajo Real</span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Pega aquí los contornos del pit shell en formato CSV (un punto por línea):
              <br />
              <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 rounded">nivel,x,y</code> para cada punto del contorno, o
              <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 rounded ml-0.5">nivel,x,y,z</code>.
              <br />
              Los niveles se agrupan automáticamente y deben ir de la cresta (arriba) al piso.
            </p>
            <textarea
              value={importedPitText}
              onChange={(e) => setImportedPitText(e.target.value)}
              placeholder={'3200,512400,7416200\n3200,512420,7416215\n...\n3065,512450,7416300'}
              className="w-full h-28 p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-mono text-[11px] resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
            {importedPitError && (
              <p className="text-[11px] text-red-500 dark:text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-2 py-1.5">
                {importedPitError}
              </p>
            )}
            {importedPitLevels.length >= 2 && (
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-2 py-1.5">
                {importedPitLevels.length} niveles cargados ({importedPitLevels.reduce((a, l) => a + l.points.length, 0)} puntos)
              </p>
            )}
            <button
              onClick={() => {
                try {
                  const levels = parsePitCSV(importedPitText);
                  setImportedPitLevels(levels);
                  setImportedPitError('');
                } catch (err) {
                  setImportedPitLevels([]);
                  setImportedPitError(err instanceof Error ? err.message : 'Error al parsear el CSV');
                }
              }}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white transition-colors"
            >
              <FileUp className="w-3.5 h-3.5" />
              Cargar Tajo
            </button>
            {importedPitLevels.length >= 2 && (
              <button
                onClick={() => { setImportedPitLevels([]); setImportedPitText(''); setImportedPitError(''); }}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Limpiar
              </button>
            )}
          </div>
        )}

        {/* Pit Info Panel — Fixed top-right inside canvas */}
        {showPitWireframe && (
          <div className="absolute top-3 right-3 z-20 bg-white/90 dark:bg-slate-900/90 backdrop-blur border border-cyan-500/50 rounded-2xl shadow-xl text-xs w-52 overflow-hidden">
            <button
              onClick={() => setShowPitInfo(!showPitInfo)}
              className="w-full flex items-center justify-between px-3 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 transition-colors"
            >
              <div className="flex items-center gap-1.5">
                <Mountain className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                <span className="font-bold text-cyan-700 dark:text-cyan-300">Tajo</span>
              </div>
              {showPitInfo ? <ChevronUp className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" /> : <ChevronDown className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />}
            </button>
            {showPitInfo && (() => {
              const pitLevels = pitMode === 'REFERENCE'
                ? (referencePitLevels ?? []).map(level => level.bench)
                : pitMode === 'PROCEDURAL'
                ? Array.from({ length: 10 }, (_, i) => Math.round(3200 - i * (75 / 9)))
                : pitMode === 'REALISTIC'
                  ? REALISTIC_PIT_DATA.map(l => l.bench)
                  : importedPitLevels.map(l => l.bench);
              const nLev = pitLevels.length;
              const topLev = pitLevels.length ? pitLevels[0] : 3200;
              const bottomLev = pitLevels.length ? pitLevels[nLev - 1] : 3065;
              return (
                <div className="px-3 py-2.5 space-y-1 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Cresta:</span>
                    <span className="font-mono text-slate-700 dark:text-slate-200">{topLev} msnm</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Talud:</span>
                    <span className="font-mono text-slate-700 dark:text-slate-200">{copperCreek ? 'No modelado' : '45°'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Bancos:</span>
                    <span className="font-mono text-slate-700 dark:text-slate-200">{nLev}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">{copperCreek ? 'Último nivel:' : 'Piso:'}</span>
                    <span className="font-mono text-slate-700 dark:text-slate-200">{bottomLev} msnm</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">{copperCreek ? 'Tramo mostrado:' : 'Profundidad:'}</span>
                    <span className="font-mono text-slate-700 dark:text-slate-200">{topLev - bottomLev} m</span>
                  </div>
                  <div className="pt-1.5 border-t border-slate-200 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 block text-[10px] mb-1">Niveles:</span>
                    <div className="flex flex-wrap gap-1">
                      {pitLevels.map(b => (
                        <span key={b} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          {b}m
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="pt-1.5 border-t border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 dark:text-slate-500 block text-[10px]">
                      {pitMode === 'PROCEDURAL' && 'Geometría: procedimental (forma orgánica sintética)'}
                      {pitMode === 'REALISTIC' && 'Geometría: ejemplo realista de pórfido cuprífero (forma riñón)'}
                      {pitMode === 'IMPORTED' && 'Geometría: datos importados del pit shell real'}
                      {pitMode === 'REFERENCE' && 'Sección superior abierta · contornos aproximados · bancos de 12 m · altura visual 2,6×'}
                    </span>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

      </div>
    </div>
  );
};
