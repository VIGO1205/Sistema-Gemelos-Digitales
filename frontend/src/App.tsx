import { useAuth } from './context/AuthContext';
import { LoginPage } from './components/auth/LoginPage';
import React, { useState, useMemo, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { UserRole, ActiveModelData } from './types';
import { useData } from './context/DataContext';
import { activeModelApi } from './services/api';
import { Sidebar, NavigationModule } from './components/navigation/Sidebar';
import { Header } from './components/navigation/Header';
import { ExecutiveDashboard } from './components/dashboard/ExecutiveDashboard';
import { CopperCreekViewer } from './components/viewer3d/CopperCreekViewer';
import { GeospatialManager } from './components/geospatial/GeospatialManager';
import { BayesianInferenceEngine } from './components/bayesian/BayesianInferenceEngine';
import { CopperCreekReportView } from './components/reports/CopperCreekReportView';
import { AlertsManager } from './components/alerts/AlertsManager';
import { FloatingChatWidget } from './components/ai/FloatingChatWidget';
import { ReconciliationDashboard } from './components/reconciliation/ReconciliationDashboard';
import { EconomicDashboard } from './components/economics/EconomicDashboard';
import { DrillholePlanner } from './components/drillhole/DrillholePlanner';
import { MiningLoader } from './components/shared/MiningLoader';

function AppContent() {
  const {
    project, blocks, alerts,
    loading, error, acknowledgeAlert,
  } = useData();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [activeModule, setActiveModule] = useState<NavigationModule>('DASHBOARD');
  const [selectedBlock, setSelectedBlock] = useState(blocks[0] || null);
  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const [activeBench, setActiveBench] = useState<number>(project?.activeBench ?? 3170);
  const [activeModelsByBench, setActiveModelsByBench] = useState<Record<number, ActiveModelData>>({});

  useEffect(() => {
    if (project) setActiveBench(project.activeBench);
  }, [project?.activeBench]);

  useEffect(() => {
    let cancelled = false;
    const loadActiveModels = () => {
      activeModelApi.getAllActive()
        .then(res => {
          if (cancelled) return;
          const list = res.data?.active_models ?? [];
          const map: Record<number, ActiveModelData> = {};
          for (const m of list) map[m.bench] = m;
          setActiveModelsByBench(map);
        })
        .catch(() => { if (!cancelled) setActiveModelsByBench({}); });
    };
    loadActiveModels();
    const interval = setInterval(loadActiveModels, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  useEffect(() => {
    const firstBlockOfBench = blocks.find(b => b.bench === activeBench);
    setSelectedBlock(firstBlockOfBench || null);
  }, [activeBench, blocks]);

  const currentRole: UserRole = user?.role || 'VIEWER';
  const handleBenchChange = (bench: number) => setActiveBench(bench);
  const activeBlocks = useMemo(() => blocks.filter(b => b.bench === activeBench), [blocks, activeBench]);
  const availableBenches = useMemo(() => {
    const set = new Set<number>(blocks.map(b => b.bench));
    return Array.from(set).sort((a, b) => b - a);
  }, [blocks]);
  const displayProject = project ? { ...project, activeBench } : null;
  const isCopperCreekView = ['VIEWER_3D', 'DASHBOARD', 'ALERTS', 'RECONCILIATION', 'ECONOMICS', 'BAYESIAN_ENGINE', 'GEOSPATIAL_ETL', 'DRILLHOLE_PLANNER', 'REPORTS'].includes(activeModule);
  const navigationProject = displayProject && isCopperCreekView
    ? { ...displayProject, name: 'Copper Creek · Mammoth', mineSite: 'Copper Creek, Arizona', epsgCode: 'EPSG:32612 (WGS 84 / UTM 12N)' }
    : displayProject;
  const unreadAlertsCount = alerts.filter(a => !a.acknowledged).length;

  if (!authLoading && !isAuthenticated) return <LoginPage />;
  if (loading || authLoading) {
    return <MiningLoader fullScreen title="Preparando el Gemelo Digital M-6" detail="Conectando los datos del proyecto y las vistas de minería." />;
  }
  if (error || !project) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-slate-900 border border-red-200 dark:border-red-800 rounded-2xl p-6 max-w-md w-full shadow-lg">
          <h2 className="text-lg font-bold text-red-600 dark:text-red-400 mb-2">Error de Conexión</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">{error || 'No se pudieron cargar los datos del proyecto. Verifica la conexión con el backend.'}</p>
          <button onClick={() => window.location.reload()} className="w-full px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs rounded-xl transition-colors">Reintentar</button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex font-sans selection:bg-amber-500 selection:text-slate-950 transition-colors overflow-hidden">
      <Sidebar
        activeModule={activeModule}
        onSelectModule={setActiveModule}
        project={navigationProject}
        currentRole={currentRole}
        onBenchChange={handleBenchChange}
        unreadAlertsCount={isCopperCreekView ? 0 : unreadAlertsCount}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        benches={availableBenches}
      />
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header
          activeModule={activeModule}
          project={navigationProject}
          currentRole={currentRole}
          alerts={isCopperCreekView ? [] : alerts}
          unreadAlertsCount={isCopperCreekView ? 0 : unreadAlertsCount}
          onOpenMobileMenu={() => setIsMobileOpen(true)}
          onSelectModule={setActiveModule}
          onBenchChange={handleBenchChange}
          onAcknowledgeAlert={acknowledgeAlert}
          benches={availableBenches}
          activeModelsByBench={activeModelsByBench}
        />
        <main className="flex flex-1 min-h-0 flex-col overflow-y-auto p-3.5 sm:p-5 lg:p-6 relative">
          {!isCopperCreekView && (
            <div role="note" className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
              Mina Esperanza Sur: escenario académico con datos generados. Esta sección no utiliza los sondajes ni los cubos de Copper Creek.
            </div>
          )}
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={activeModule}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className={activeModule === 'VIEWER_3D' ? 'flex-1 min-h-0' : 'flex-1 space-y-6'}
            >
              {activeModule === 'DASHBOARD' && <ExecutiveDashboard onOpenViewer={() => setActiveModule('VIEWER_3D')} />}
              {activeModule === 'VIEWER_3D' && (
                <div className="h-full min-h-[720px] sm:min-h-[620px] lg:min-h-0">
                  <CopperCreekViewer />
                </div>
              )}
              {activeModule === 'BAYESIAN_ENGINE' && <BayesianInferenceEngine onOpenViewer={() => setActiveModule('VIEWER_3D')} />}
              {activeModule === 'GEOSPATIAL_ETL' && <GeospatialManager />}
              {activeModule === 'ALERTS' && <AlertsManager onOpenViewer={() => setActiveModule('VIEWER_3D')} />}
              {activeModule === 'REPORTS' && <CopperCreekReportView currentRole={currentRole} userName={user?.full_name || 'Usuario'} />}
              {activeModule === 'RECONCILIATION' && <ReconciliationDashboard />}
              {activeModule === 'ECONOMICS' && <EconomicDashboard />}
              {activeModule === 'DRILLHOLE_PLANNER' && <DrillholePlanner />}
            </motion.div>
          </AnimatePresence>
        </main>
        <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800/80 py-3.5 px-4 sm:px-6 text-slate-500 dark:text-slate-400 text-xs font-mono transition-colors">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-semibold text-slate-700 dark:text-slate-300">{isCopperCreekView ? 'Copper Creek · reconstrucción académica de Mammoth' : 'Mina Esperanza Sur · simulación académica'}</span>
            </div>
            <div className="text-slate-500 dark:text-slate-400">{isCopperCreekView ? 'EPSG:32612 · Modelo espacial validado por sondaje · Sin clasificación de recursos' : `Datos sintéticos · sin certificación de recursos · Datum de ejemplo: ${project.epsgCode}`}</div>
          </div>
        </footer>
      </div>
      {!isCopperCreekView && <FloatingChatWidget project={displayProject} blocks={activeBlocks} selectedBlock={selectedBlock} userName={user?.full_name || 'Usuario'} userRole={currentRole} />}
    </div>
  );
}

export default AppContent;
