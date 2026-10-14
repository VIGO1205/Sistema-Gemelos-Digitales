import React, { useState, useRef, useEffect } from 'react';
import { MiningProject, UserRole, MiningAlert, ActiveModelData } from '../../types';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { NavigationModule } from './Sidebar';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Menu,
  Sun,
  Moon,
  Bell,
  ChevronRight,
  LogOut,
  User,
  X,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';

interface HeaderProps {
  activeModule: NavigationModule;
  project: MiningProject;
  currentRole: UserRole;
  alerts: MiningAlert[];
  unreadAlertsCount: number;
  onOpenMobileMenu: () => void;
  onSelectModule: (module: NavigationModule) => void;
  onBenchChange: (bench: number) => void;
  onAcknowledgeAlert?: (alertId: string) => void;
  benches?: number[];
  activeModelsByBench?: Record<number, ActiveModelData>;
}

const MODULE_TITLES: Record<NavigationModule, { title: string; subtitle: string; category: string }> = {
  DASHBOARD: {
    title: 'Resumen Exploratorio',
    subtitle: 'Cubos estimados, cobertura espacial y validación del modelo',
    category: 'Exploración'
  },
  VIEWER_3D: {
    title: 'Gemelo Digital 3D (WebGL)',
    subtitle: 'Reconstrucción académica de cubos, leyes de cobre y sondajes',
    category: 'Exploración'
  },
  BAYESIAN_ENGINE: {
    title: 'Modelo IA y Consulta de Ley',
    subtitle: 'Modelo publicado, validación y predicción puntual mediante FastAPI',
    category: 'Modelación IA'
  },
  GEOSPATIAL_ETL: {
    title: 'Gestión Geoespacial',
    subtitle: 'Cubos y sondajes de Copper Creek; estado de los datos SWIR',
    category: 'Modelación IA'
  },
  ALERTS: {
    title: 'Señales para Revisión',
    subtitle: 'Cubos con soporte limitado o discrepancias entre estimadores',
    category: 'Exploración'
  },
  REPORTS: {
    title: 'Generador de Reportes Académicos',
    subtitle: 'PDF, Excel y Word de Copper Creek · Mammoth y su modelo publicado',
    category: 'Gobernanza'
  },
  RECONCILIATION: {
    title: 'Validación por Sondajes',
    subtitle: 'Comparación de modelos en sondajes completos no vistos',
    category: 'Exploración'
  },
  ECONOMICS: {
    title: 'Sensibilidad Económica Académica',
    subtitle: 'Escenarios hipotéticos por ley estimada y supuestos editables',
    category: 'Exploración'
  },
  DRILLHOLE_PLANNER: {
    title: 'Zonas para Revisar Sondajes · Copper Creek',
    subtitle: 'Zonas para revisión académica según soporte y ley del modelo publicado',
    category: 'Modelación IA'
  }
};

export const Header: React.FC<HeaderProps> = ({
  activeModule,
  project,
  currentRole,
  alerts,
  unreadAlertsCount,
  onOpenMobileMenu,
  onSelectModule,
  onBenchChange,
  onAcknowledgeAlert,
  benches,
  activeModelsByBench,
}) => {
  const { theme, toggleTheme, isDark } = useTheme();
  const { user, logout } = useAuth();
  const [showAlertPanel, setShowAlertPanel] = useState(false);
  const alertPanelRef = useRef<HTMLDivElement>(null);
  const moduleInfo = MODULE_TITLES[activeModule] || MODULE_TITLES.DASHBOARD;

  // Click-outside handler: cierra la bandeja al hacer clic fuera de ella
  useEffect(() => {
    if (!showAlertPanel) return;
    
    const handleClickOutside = (event: MouseEvent) => {
      if (alertPanelRef.current && !alertPanelRef.current.contains(event.target as Node)) {
        setShowAlertPanel(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showAlertPanel]);
  const availableBenches = benches && benches.length > 0 ? benches : [3200, 3185, 3170, 3155, 3140, 3125, 3110, 3095, 3080, 3065];

  const currentActiveModel = activeModelsByBench?.[project.activeBench] ?? null;
  const hasActiveModel = !!currentActiveModel?.activated_at;
  const isCopperCreekStudy = project.name.startsWith('Copper Creek');

  useEffect(() => setShowAlertPanel(false), [activeModule]);

  const activeAlerts = alerts.filter(a => !a.acknowledged);
  const recentAlerts = activeAlerts.slice(0, 6);

  const severityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return <AlertTriangle className="w-4 h-4 text-rose-500" />;
      case 'WARNING': return <AlertCircle className="w-4 h-4 text-amber-500" />;
      default: return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  const severityBg = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20';
      case 'WARNING': return 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20';
      default: return 'bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20';
    }
  };

  return (
    <header className="sticky top-0 z-30 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 transition-colors">
      <div className="w-full px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-2 sm:gap-4">
          
          {/* Left: Mobile Hamburger & Active Section Title */}
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            {/* Hamburger Button for Mobile & Tablet */}
            <button
              onClick={onOpenMobileMenu}
              className="lg:hidden p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 touch-target flex items-center justify-center border border-slate-200 dark:border-slate-700/80"
              aria-label="Abrir menú de navegación"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Breadcrumb & Section Title */}
            <div className="min-w-0 overflow-hidden">
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500 dark:text-slate-400 truncate">
                <span className="hidden md:inline font-semibold truncate">{project.name}</span>
                <ChevronRight className="w-3 h-3 hidden md:inline text-slate-400 shrink-0" />
                <span className="text-amber-600 dark:text-amber-400 font-semibold truncate">{moduleInfo.category}</span>
                <span className="hidden lg:inline shrink-0">•</span>
                {!isCopperCreekStudy && <span className="hidden lg:inline text-emerald-600 dark:text-emerald-400 truncate">Banco {project.activeBench}m</span>}
              </div>
              <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 font-display truncate">
                {isCopperCreekStudy && activeModule === 'DASHBOARD' ? 'Resumen Exploratorio · Copper Creek'
                  : isCopperCreekStudy && activeModule === 'ALERTS' ? 'Alertas de revisión · Copper Creek'
                  : isCopperCreekStudy && activeModule === 'RECONCILIATION' ? 'Validación de leyes · Copper Creek'
                  : isCopperCreekStudy && activeModule === 'ECONOMICS' ? 'Sensibilidad económica · Copper Creek'
                  : isCopperCreekStudy && activeModule === 'BAYESIAN_ENGINE' ? 'Motor IA · Copper Creek'
                  : moduleInfo.title}
              </h2>
            </div>
          </div>

          {/* Right: Bench Quick Switch, Theme Toggle, Role Badge, Alerts */}
          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            
            {/* Bench Selector Dropdown */}
            {!isCopperCreekStudy && <div className="hidden sm:flex items-center gap-1.5 bg-slate-100 dark:bg-slate-950 px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-mono">
              <span className="text-slate-500 text-[11px] shrink-0">Banco:</span>
              <select
                value={project.activeBench}
                onChange={(e) => onBenchChange(Number(e.target.value))}
                className="bg-transparent text-slate-900 dark:text-slate-100 font-bold text-xs font-mono focus:outline-none cursor-pointer py-0.5 pr-1"
              >
                {availableBenches.map(b => (
                  <option key={b} value={b} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                    {b}m
                  </option>
                ))}
              </select>
              {hasActiveModel ? (
                <span
                  className="hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[9px] font-bold"
                  title={`Modelo activo: ${currentActiveModel?.model_name} (Score ${currentActiveModel?.composite_score?.toFixed(4) ?? '-'})`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  {currentActiveModel?.model_name && currentActiveModel.model_name.length > 12
                    ? currentActiveModel.model_name.substring(0, 12) + '…'
                    : currentActiveModel?.model_name}
                </span>
              ) : (
                <span
                  className="hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-300 dark:border-slate-700 text-[9px] font-bold"
                  title="Este banco no tiene modelo activo. Entrénalo y actívalo en el Motor IA (⚡ Lote Multi-Banco)."
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600" />
                  Sin modelo
                </span>
              )}
            </div>}

            {/* User Info Badge */}
            <div className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="text-slate-500 dark:text-slate-400 font-mono hidden md:inline">Rol:</span>
              <span className="font-bold text-amber-600 dark:text-amber-400 font-mono text-[11px] sm:text-xs truncate max-w-[90px] sm:max-w-none">
                {currentRole}
              </span>
            </div>

            {/* Logout Button */}
            <button
              onClick={logout}
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-950/30 border border-slate-200 dark:border-slate-700 hover:border-red-200 dark:hover:border-red-800 transition-all text-xs text-slate-600 dark:text-slate-300 hover:text-red-600 dark:hover:text-red-400"
              title="Cerrar sesión"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline font-semibold">Salir</span>
            </button>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-all border border-slate-200 dark:border-slate-700"
              title={isDark ? "Cambiar a Modo Claro (Light Mode)" : "Cambiar a Modo Oscuro (Dark Mode)"}
              aria-label="Alternar modo oscuro y claro"
            >
              {isDark ? (
                <Sun className="w-4 h-4 text-amber-400 hover:rotate-45 transition-transform" />
              ) : (
                <Moon className="w-4 h-4 text-cyan-600 hover:-rotate-12 transition-transform" />
              )}
            </button>

            {/* Operational Alerts Bell with Dropdown Panel */}
            {!isCopperCreekStudy && <div className="relative" ref={alertPanelRef}>
              <button
                onClick={() => setShowAlertPanel(!showAlertPanel)}
                className="relative p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-all border border-slate-200 dark:border-slate-700"
                title="Ver alertas operacionales"
                aria-label="Ver alertas operacionales"
              >
                <Bell className="w-4 h-4" />
                {unreadAlertsCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white font-mono text-[9px] font-bold flex items-center justify-center shadow animate-bounce">
                    {unreadAlertsCount}
                  </span>
                )}
              </button>

              <AnimatePresence>
                {showAlertPanel && (
                  <>
                    {/* Backdrop */}
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="fixed inset-0 z-40"
                      onClick={() => setShowAlertPanel(false)}
                    />
                    {/* Panel */}
                    <motion.div
                      initial={{ opacity: 0, y: -8, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -8, scale: 0.97 }}
                      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                      className="absolute right-0 top-full mt-2 w-80 sm:w-96 z-50 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden"
                    >
                      {/* Header */}
                      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50">
                        <div className="flex items-center gap-2">
                          <Bell className="w-4 h-4 text-amber-500" />
                          <span className="text-sm font-bold text-slate-900 dark:text-slate-100">Alertas Activas</span>
                          {activeAlerts.length > 0 && (
                            <span className="px-1.5 py-0.5 rounded-full bg-rose-500 text-white text-[10px] font-mono font-bold">
                              {activeAlerts.length}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => setShowAlertPanel(false)}
                          className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Alert List */}
                      <div className="max-h-[400px] overflow-y-auto">
                        {recentAlerts.length === 0 ? (
                          <div className="px-4 py-8 text-center text-xs text-slate-500 dark:text-slate-400">
                            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
                            <p>No hay alertas activas</p>
                            <p className="text-[10px] mt-1">Sin alertas en el escenario de ejemplo</p>
                          </div>
                        ) : (
                          <div className="divide-y divide-slate-100 dark:divide-slate-800">
                            {recentAlerts.map((alert) => (
                              <div key={alert.id} className={`p-3 ${severityBg(alert.severity)}`}>
                                <div className="flex items-start gap-2.5">
                                  {severityIcon(alert.severity)}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                                        {alert.title}
                                      </span>
                                      <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 shrink-0">
                                        Banco {alert.bench}m
                                      </span>
                                    </div>
                                    <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 line-clamp-2">
                                      {alert.description}
                                    </p>
                                    <div className="flex items-center justify-between mt-1.5">
                                      <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                                        {new Date(alert.timestamp).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: true })}
                                      </span>
                                      {onAcknowledgeAlert && (
                                        <button
                                          onClick={() => onAcknowledgeAlert(alert.id)}
                                          className="text-[10px] px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 hover:border-emerald-200 dark:hover:border-emerald-800 text-slate-600 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition-all"
                                        >
                                          Reconocer
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Footer */}
                      <div className="px-4 py-2.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50">
                        <button
                          onClick={() => {
                            setShowAlertPanel(false);
                            onSelectModule('ALERTS');
                          }}
                          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/20 transition-all"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          Ver todas las alertas
                        </button>
                      </div>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>}
          </div>

        </div>
      </div>
    </header>
  );
};
