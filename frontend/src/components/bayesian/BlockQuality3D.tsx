import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { BlockModelItem } from '../../types';
import { Download } from 'lucide-react';
import { downloadCanvasPng } from '../../services/visualExport';

export type CubeQuality = 'BUENO' | 'REGULAR' | 'NO_SIRVE';

export interface QualityBlock {
  quality: CubeQuality;
  block: BlockModelItem;
}

interface QualityCubeCanvasProps {
  quality: CubeQuality;
  active: boolean;
  isDark: boolean;
  large?: boolean;
}

const QUALITY_CONFIG: Record<CubeQuality, { color: number; emissive: number }> = {
  BUENO: { color: 0x10b981, emissive: 0x064e3b },
  REGULAR: { color: 0xf59e0b, emissive: 0x78350f },
  NO_SIRVE: { color: 0xf43f5e, emissive: 0x881337 },
};

const QUALITY_RING: Record<CubeQuality, string> = {
  BUENO: 'ring-emerald-400 border-emerald-400/60',
  REGULAR: 'ring-amber-400 border-amber-400/60',
  NO_SIRVE: 'ring-rose-400 border-rose-400/60',
};

const QUALITY_TEXT: Record<CubeQuality, string> = {
  BUENO: 'text-emerald-600 dark:text-emerald-400',
  REGULAR: 'text-amber-600 dark:text-amber-400',
  NO_SIRVE: 'text-rose-600 dark:text-rose-400',
};

const QUALITY_META: Record<CubeQuality, { label: string; tag: string; rule: string; desc: string }> = {
  BUENO: {
    label: 'Ley alta',
    tag: 'Ejemplo visual',
    rule: 'Ley estimada ≥ 0.45% Cu',
    desc: 'Requiere validación local antes de decidir destino',
  },
  REGULAR: {
    label: 'Ley intermedia',
    tag: 'Ejemplo visual',
    rule: 'Ley estimada cercana a 0.35% Cu',
    desc: 'El umbral es ilustrativo, no un corte económico validado',
  },
  NO_SIRVE: {
    label: 'Ley baja',
    tag: 'Ejemplo visual',
    rule: 'Ley estimada baja',
    desc: 'La ley sola no determina el destino del material',
  },
};

const QualityCubeCanvas: React.FC<QualityCubeCanvasProps> = ({ quality, active, isDark, large = false }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<{ renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera } | null>(null);
  const [exporting, setExporting] = React.useState(false);
  const [exportError, setExportError] = React.useState('');

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, container.clientWidth / Math.max(container.clientHeight, 1), 0.1, 100);
    camera.position.set(2.6, 2.2, 3.1);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    sceneRef.current = { renderer, scene, camera };
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, Math.max(container.clientHeight, 1));

    scene.add(new THREE.AmbientLight(isDark ? 0x8892b0 : 0xffffff, 0.75));
    const dir = new THREE.DirectionalLight(0xffffff, 1.2);
    dir.position.set(3, 5, 4);
    scene.add(dir);

    const cfg = QUALITY_CONFIG[quality];
    const geo = new THREE.BoxGeometry(1.6, 1.6, 1.6);
    const mat = new THREE.MeshStandardMaterial({
      color: cfg.color,
      emissive: cfg.emissive,
      emissiveIntensity: active ? 0.4 : 0.12,
      metalness: 0.15,
      roughness: 0.35,
    });
    const cube = new THREE.Mesh(geo, mat);

    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geo),
      new THREE.LineBasicMaterial({ color: active ? 0xffffff : 0x334155 })
    );

    const group = new THREE.Group();
    group.add(cube);
    group.add(edges);
    group.scale.setScalar(active ? 1.12 : 1.0);
    scene.add(group);

    const grid = new THREE.GridHelper(6, 12, 0x64748b, 0x334155);
    grid.position.y = -1.15;
    scene.add(grid);

    let rafId = 0;
    let disposed = false;
    const clock = new THREE.Clock();
    const animate = () => {
      if (disposed) return;
      rafId = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();
      group.rotation.y = t * 0.55;
      group.rotation.x = Math.sin(t * 0.4) * 0.14;
      group.position.y = -0.12 + Math.sin(t * 1.2) * 0.08;
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      const w = container.clientWidth;
      const h = Math.max(container.clientHeight, 1);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(container);

    return () => {
      disposed = true;
      cancelAnimationFrame(rafId);
      ro.disconnect();
      geo.dispose();
      mat.dispose();
      edges.geometry.dispose();
      (edges.material as THREE.Material).dispose();
      grid.geometry.dispose();
      (grid.material as THREE.Material).dispose();
      renderer.dispose();
      sceneRef.current = null;
    };
  }, [quality, active, isDark]);

  const exportCube = async () => {
    const context = sceneRef.current;
    const container = containerRef.current;
    if (!context || !container) return;
    setExporting(true);
    setExportError('');
    const { renderer, scene, camera } = context;
    const size = renderer.getSize(new THREE.Vector2());
    const ratio = renderer.getPixelRatio();
    const aspect = camera.aspect;
    try {
      const gl = renderer.getContext();
      const maxSize = Math.min(renderer.capabilities.maxTextureSize, gl.getParameter(gl.MAX_RENDERBUFFER_SIZE) as number);
      const width = Math.min(3600, maxSize);
      const height = Math.min(Math.round(width / Math.max(container.clientWidth / container.clientHeight, 0.1)), maxSize);
      const image = document.createElement('canvas');
      image.width = width;
      image.height = height;
      try {
        renderer.setPixelRatio(1);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.render(scene, camera);
        const pixels = image.getContext('2d');
        if (!pixels) throw new Error('No se pudo crear la imagen.');
        pixels.fillStyle = isDark ? '#0f172a' : '#f8fafc';
        pixels.fillRect(0, 0, width, height);
        pixels.drawImage(renderer.domElement, 0, 0, width, height);
      } finally {
        renderer.setPixelRatio(ratio);
        renderer.setSize(size.x, size.y, false);
        camera.aspect = aspect;
        camera.updateProjectionMatrix();
      }
      await downloadCanvasPng(image, `copper-creek-cubo-${quality.toLowerCase()}.png`, 600);
    } catch (cause) {
      setExportError(cause instanceof Error ? cause.message : 'No se pudo exportar el cubo.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div ref={containerRef} className={`group relative ${large ? 'h-56 sm:h-64' : 'h-24'}`}>
      <canvas ref={canvasRef} className="w-full h-full" />
      {large && <button type="button" title="Descargar PNG a 600 DPI" onClick={() => void exportCube()} disabled={exporting}
        className="absolute right-2 top-2 flex items-center gap-1 rounded-lg border border-slate-300 bg-white/95 px-2 py-1 text-[10px] font-semibold text-slate-800 opacity-0 shadow-sm transition-opacity hover:bg-amber-50 focus:opacity-100 group-hover:opacity-100 dark:border-slate-700 dark:bg-slate-900/95 dark:text-slate-100">
        <Download className="h-3 w-3" />{exporting ? 'Capturando…' : 'PNG 600 DPI'}
      </button>}
      {exportError && <span role="alert" className="absolute bottom-1 left-1 text-[10px] text-rose-600">{exportError}</span>}
    </div>
  );
};

interface BlockQualityGalleryProps {
  isDark: boolean;
  activeQuality: CubeQuality | null;
  onSelect: (q: CubeQuality | null) => void;
  items: QualityBlock[];
}

const Stat: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div className="p-2.5 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800">
    <span className="text-[10px] text-slate-500 dark:text-slate-400 block">{label}</span>
    <span className={`font-mono font-bold text-sm ${color ?? 'text-slate-800 dark:text-slate-200'}`}>{value}</span>
  </div>
);

export const BlockQualityGallery3D: React.FC<BlockQualityGalleryProps> = ({
  isDark,
  activeQuality,
  onSelect,
  items,
}) => {
  const activeItem = items.find(i => i.quality === activeQuality) || null;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm">
      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-display mb-1">
        Calidad de Bloques por Nivel de Ley (3D)
      </h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
        Tres cubos reconstruidos de Copper Creek ordenados por ley estimada. Haz clic para ver sus datos.
      </p>

      {/* Small cubes row */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        {items.map(item => {
          const meta = QUALITY_META[item.quality];
          const isActive = item.quality === activeQuality;
          return (
            <button
              key={item.quality}
              onClick={() => onSelect(isActive ? null : item.quality)}
              className={`relative rounded-2xl border bg-slate-50 dark:bg-slate-950/40 p-2 sm:p-3 text-left transition-all hover:shadow-md ${
                isActive ? `ring-2 ring-offset-2 ring-offset-white dark:ring-offset-slate-900 ${QUALITY_RING[item.quality]}` : 'border-slate-200 dark:border-slate-800'
              }`}
            >
              <QualityCubeCanvas quality={item.quality} active={isActive} isDark={isDark} />
              <div className="flex items-center justify-between mt-1.5">
                <span className={`text-[11px] sm:text-xs font-bold ${QUALITY_TEXT[item.quality]}`}>{meta.label}</span>
                <span className="text-[9px] font-mono text-slate-400">Nv {item.block.bench}m</span>
              </div>
              <span className="text-[9px] text-slate-400 block truncate">{item.block.id}</span>
            </button>
          );
        })}
      </div>

      {/* Expanded analysis */}
      {activeItem && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
          <div className={`rounded-2xl border bg-slate-50 dark:bg-slate-950/40 p-3 ${QUALITY_RING[activeItem.quality]}`}>
            <QualityCubeCanvas quality={activeItem.quality} active isDark={isDark} large />
            <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400"><strong>Interpretación determinística: </strong>El cubo {activeItem.block.id} del banco {activeItem.block.bench} m tiene una ley estimada de {activeItem.block.cu_bayesian.toFixed(3)} %Cu. Su etiqueta de calidad es ilustrativa y requiere validación local.</p>
            <div className="flex items-center justify-between mt-1">
              <span className={`text-xs font-bold ${QUALITY_TEXT[activeItem.quality]}`}>
                Nivel de calidad: {QUALITY_META[activeItem.quality].label}
              </span>
              <button
                onClick={() => onSelect(null)}
                className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 font-medium"
              >
                Cerrar ×
              </button>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[10px] font-mono font-bold text-slate-700 dark:text-slate-200">
                {activeItem.block.id}
              </span>
              <span className="px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                Banco {activeItem.block.bench}m
              </span>
              <span className="px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[10px] text-slate-500 dark:text-slate-400">
                {activeItem.block.lithology}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Stat label="Ley Random Forest" value={`${activeItem.block.cu_bayesian.toFixed(3)}% Cu`} color={QUALITY_TEXT[activeItem.quality]} />
              <Stat label="Referencia IDW3" value={`${(activeItem.block.cu_idw3 ?? 0).toFixed(3)}% Cu`} color="text-cyan-600 dark:text-cyan-400" />
              <Stat label="Sondajes de soporte" value={`${activeItem.block.support_holes ?? '—'}`} color="text-amber-600 dark:text-amber-400" />
              <Stat label="Sondaje más cercano" value={`${activeItem.block.nearest_drillhole_m.toFixed(1)} m`} color="text-cyan-600 dark:text-cyan-400" />
              <Stat label="Centro X / Y" value={`${activeItem.block.x.toFixed(0)} / ${activeItem.block.y.toFixed(0)} m`} color="text-emerald-600 dark:text-emerald-400" />
              <Stat label="Centro Z" value={`${activeItem.block.z.toFixed(0)} m`} color="text-slate-600 dark:text-slate-300" />
            </div>

            <div className="p-3 bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
              <span className="font-bold text-slate-700 dark:text-slate-200">{QUALITY_META[activeItem.quality].tag}.</span>{' '}
              {QUALITY_META[activeItem.quality].desc}. Criterio: <span className="font-mono">{QUALITY_META[activeItem.quality].rule}</span>.
              Predicción exploratoria; no clasifica recursos ni decide planta o botadero.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
