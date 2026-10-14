import React from 'react';
import { MiningProject, UserRole } from '../../types';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Box,
  Map,
  BrainCircuit,
  FileText,
  Bell,
  ChevronLeft,
  Sun,
  Moon,
  Radio,
  X,
  LogOut,
  User,
  Scale,
  DollarSign,
  Crosshair
} from 'lucide-react';

export type NavigationModule =
  | 'DASHBOARD'
  | 'VIEWER_3D'
  | 'BAYESIAN_ENGINE'
  | 'GEOSPATIAL_ETL'
  | 'ALERTS'
  | 'REPORTS'
  | 'RECONCILIATION'
  | 'ECONOMICS'
  | 'DRILLHOLE_PLANNER';

interface SidebarProps {
  activeModule: NavigationModule;
  onSelectModule: (module: NavigationModule) => void;
  project: MiningProject;
  currentRole: UserRole;
  onBenchChange?: (bench: number) => void;
  unreadAlertsCount: number;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  benches?: number[];
}

interface NavItem {
  id: NavigationModule;
  label: string;
  shortLabel: string;
  icon: React.ElementType;
  badge?: string;
  badgeType?: 'danger' | 'warning' | 'info' | 'ai' | 'success';
  description: string;
  allowedRoles: UserRole[];
}

interface NavGroup {
  category: string;
  items: NavItem[];
}

// ─── ROLE PERMISSIONS MATRIX ───
// Defines which navigation modules each role can access.
// This makes it CRYSTAL CLEAR what each role does.

const ALL_ROLES: UserRole[] = ['ADMIN', 'SENIOR_GEOLOGIST', 'JUNIOR_GEOLOGIST', 'PLANNING_ENGINEER', 'MINE_SUPERVISOR', 'VIEWER'];
const TECHNICAL_ROLES: UserRole[] = ['ADMIN', 'SENIOR_GEOLOGIST', 'JUNIOR_GEOLOGIST'];
const PLANNING_ROLES: UserRole[] = ['ADMIN', 'SENIOR_GEOLOGIST', 'PLANNING_ENGINEER'];
const SUPERVISOR_ROLES: UserRole[] = ['ADMIN', 'SENIOR_GEOLOGIST', 'MINE_SUPERVISOR'];
const GOVERNANCE_ROLES: UserRole[] = ['ADMIN', 'SENIOR_GEOLOGIST', 'PLANNING_ENGINEER', 'VIEWER'];
const ADMIN_ONLY: UserRole[] = ['ADMIN'];

export const Sidebar: React.FC<SidebarProps> = ({
  activeModule,
  onSelectModule,
  project,
  currentRole,
  unreadAlertsCount,
  isMobileOpen,
  onCloseMobile,
  isCollapsed,
  onToggleCollapse,
}) => {
  const { theme, toggleTheme, isDark } = useTheme();
  const { user, logout } = useAuth();

  const navGroups: NavGroup[] = [
    {
      category: 'Estudio Exploratorio',
      items: [
        {
          id: 'DASHBOARD',
          label: 'Resumen Exploratorio',
          shortLabel: 'Resumen',
          icon: LayoutDashboard,
          description: 'Cubos, leyes estimadas y validación espacial de Copper Creek',
          allowedRoles: ALL_ROLES
        },
        {
          id: 'VIEWER_3D',
          label: 'Gemelo Digital 3D',
          shortLabel: 'Visor 3D',
          icon: Box,
          badge: 'WebGL',
          badgeType: 'warning',
          description: 'Reconstrucción Copper Creek con ley del estimador seleccionado por validación',
          allowedRoles: ALL_ROLES
        },
        {
          id: 'ALERTS',
          label: 'Señales para Revisión',
          shortLabel: 'Señales',
          icon: Bell,
          badge: unreadAlertsCount > 0 ? `${unreadAlertsCount}` : undefined,
          badgeType: 'danger',
          description: 'Señales de revisión geológica de cubos Copper Creek',
          allowedRoles: SUPERVISOR_ROLES
        },
        {
          id: 'RECONCILIATION',
          label: 'Validación por Sondajes',
          shortLabel: 'Validación',
          icon: Scale,
          badge: 'VAL',
          badgeType: 'info',
          description: 'Comparación de modelos en sondajes completos no vistos',
          allowedRoles: ALL_ROLES
        },
        {
          id: 'ECONOMICS',
          label: 'Sensibilidad Económica',
          shortLabel: 'Sensibilidad',
          icon: DollarSign,
          badge: 'ESC',
          badgeType: 'success',
          description: 'Sensibilidad hipotética por ley estimada en Copper Creek',
          allowedRoles: ALL_ROLES
        }
      ]
    },
    {
      category: 'Modelación & IA',
      items: [
        {
          id: 'BAYESIAN_ENGINE',
          label: 'Modelo IA y Consulta de Ley',
          shortLabel: 'Modelo IA',
          icon: BrainCircuit,
          badge: 'INFO',
          badgeType: 'info',
          description: 'Modelo publicado de Copper Creek, validación y consulta por FastAPI',
          allowedRoles: TECHNICAL_ROLES
        },
        {
          id: 'GEOSPATIAL_ETL',
          label: 'Gestión Geoespacial',
          shortLabel: 'Geo ETL',
          icon: Map,
          badge: 'GEO',
          badgeType: 'success',
          description: 'Cubos y sondajes de Copper Creek; SWIR sin mediciones disponibles',
          allowedRoles: TECHNICAL_ROLES
        },
        {
          id: 'DRILLHOLE_PLANNER',
          label: 'Zonas para Revisar Sondajes',
          shortLabel: 'Zonas',
          icon: Crosshair,
          badge: 'REV',
          badgeType: 'ai',
          description: 'Zonas de revisión basadas en soporte espacial y ley del modelo publicado',
          allowedRoles: TECHNICAL_ROLES
        },
      ]
    },
    {
      category: 'Gobernanza & Sistema',
      items: [
        {
          id: 'REPORTS',
          label: 'Reportes Académicos',
          shortLabel: 'Reportes',
          icon: FileText,
          description: 'Informes de Copper Creek y del modelo publicado; sin certificación',
          allowedRoles: GOVERNANCE_ROLES
        }
      ]
    }
  ];

  // Filter groups based on role permissions
  const filteredGroups = navGroups.map(group => ({
    ...group,
    items: group.items.filter(item => item.allowedRoles.includes(currentRole))
  })).filter(group => group.items.length > 0);

  const handleNavClick = (id: NavigationModule) => {
    onSelectModule(id);
    if (isMobileOpen) {
      onCloseMobile();
    }
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        id="app-sidebar"
        className={`
          fixed lg:relative top-0 left-0 z-50
          flex flex-col
          h-screen lg:h-full
          transition-all duration-300 ease-in-out
          ${isCollapsed ? 'w-20' : 'w-72 sm:w-80 lg:w-72'}
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          bg-white dark:bg-slate-900
          border-r border-slate-200 dark:border-slate-800/90
          shadow-2xl lg:shadow-none
          text-slate-800 dark:text-slate-200
          overflow-hidden
          shrink-0
        `}
      >
        {/* Sidebar Header Brand */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800/90 bg-slate-50/50 dark:bg-slate-900/50 relative">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 shrink-0 rounded-xl bg-white dark:bg-slate-800 flex items-center justify-center overflow-hidden shadow-md ring-1 ring-slate-200 dark:ring-slate-700">
              <img
                src="/logo/LOGO-M6.png"
                alt="Logo M-6"
                className="w-10 h-10 object-contain p-1"
              />
            </div>

            {!isCollapsed && (
              <div className="min-w-0 flex-1 overflow-hidden">
                <div className="flex items-center gap-1.5">
                  <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-white font-display uppercase truncate whitespace-nowrap">
                    M-6 GEMELO DIGITAL
                  </h1>
                </div>
                <div className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400 font-mono truncate whitespace-nowrap">
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold truncate">{project.name}</span>
                </div>
              </div>
            )}
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={onCloseMobile}
            className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-800 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 touch-target flex items-center justify-center"
            aria-label="Cerrar menú lateral"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Desktop Floating Collapse/Expand Toggle — professional edge button */}
          <button
            onClick={onToggleCollapse}
            className={`
              hidden lg:flex absolute -right-3 top-1/2 -translate-y-1/2
              w-6 h-6 rounded-full items-center justify-center
              bg-white dark:bg-slate-800
              border border-slate-200 dark:border-slate-700
              text-slate-400 hover:text-amber-600 dark:hover:text-amber-400
              hover:border-amber-300 dark:hover:border-amber-700
              shadow-sm hover:shadow-md
              transition-all duration-200
              z-50
            `}
            title={isCollapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
            aria-label={isCollapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
          >
            <ChevronLeft
              className={`
                w-3.5 h-3.5 transition-transform duration-300
                ${isCollapsed ? 'rotate-180' : ''}
              `}
            />
          </button>
        </div>

        {/* Navigation Modules List */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
          {filteredGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              {!isCollapsed && (
                <div className="px-2.5 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 font-display">
                  {group.category}
                </div>
              )}

              {group.items.map(item => {
                const Icon = item.icon;
                const isActive = activeModule === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.id)}
                    title={isCollapsed ? `${item.label}: ${item.description}` : undefined}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all relative group
                      ${isActive
                        ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/10'
                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-900 dark:hover:text-white'
                      }
                    `}
                  >
                    <Icon className={`w-5 h-5 shrink-0 transition-transform group-hover:scale-110 ${isActive ? 'text-slate-950' : 'text-slate-500 dark:text-slate-400 group-hover:text-amber-500'}`} />

                    {!isCollapsed && (
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium truncate block">
                            {item.label}
                          </span>

                          {/* Badge indicator */}
                          {item.badge && (
                            <span
                              className={`
                                ml-1.5 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded-full
                                ${item.badgeType === 'danger' ? 'bg-rose-500 text-white animate-pulse' : ''}
                                ${item.badgeType === 'warning' ? (isActive ? 'bg-slate-950 text-amber-300' : 'bg-amber-500/20 text-amber-600 dark:text-amber-400') : ''}
                                ${item.badgeType === 'info' ? (isActive ? 'bg-slate-950 text-cyan-300' : 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400') : ''}
                                ${item.badgeType === 'success' ? (isActive ? 'bg-slate-950 text-emerald-300' : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400') : ''}
                                ${item.badgeType === 'ai' ? (isActive ? 'bg-slate-950 text-purple-300' : 'bg-purple-500/20 text-purple-600 dark:text-purple-400') : ''}
                              `}
                            >
                              {item.badge}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Active side indicator */}
                    {isActive && (
                      <span className="absolute right-1 top-2 bottom-2 w-1 rounded-full bg-slate-950 dark:bg-slate-950" />
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Sidebar Footer: User Info, Theme Toggle & Logout */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800/90 bg-slate-50 dark:bg-slate-950/60 space-y-2">
          {/* User Info Card */}
          {!isCollapsed ? (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80">
              <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                  {user?.full_name || 'Usuario'}
                </div>
                <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate">
                  {currentRole}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <User className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              </div>
            </div>
          )}

          {/* Theme Mode Toggle Button */}
          <button
            onClick={toggleTheme}
            className={`
              w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all
              bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80
              hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200
            `}
            title={isDark ? "Cambiar a Modo Claro" : "Cambiar a Modo Oscuro"}
          >
            <div className="flex items-center gap-2">
              {isDark ? (
                <Moon className="w-4 h-4 text-cyan-400 shrink-0" />
              ) : (
                <Sun className="w-4 h-4 text-amber-500 shrink-0" />
              )}
              {!isCollapsed && (
                <span>{isDark ? 'Modo Oscuro' : 'Modo Claro'}</span>
              )}
            </div>

            {!isCollapsed && (
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${isDark ? 'bg-cyan-500/20 text-cyan-300' : 'bg-amber-500/20 text-amber-700'}`}>
                {isDark ? '🌙 Oscuro' : '☀️ Claro'}
              </span>
            )}
          </button>

          {/* Logout Button */}
          <button
            onClick={logout}
            className={`
              w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all
              bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80
              hover:bg-red-50 dark:hover:bg-red-950/30 hover:border-red-200 dark:hover:border-red-800
              text-slate-700 dark:text-slate-200 hover:text-red-600 dark:hover:text-red-400
            `}
            title="Cerrar sesión"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            {!isCollapsed && <span>Cerrar Sesión</span>}
          </button>

          {/* Mining Telemetry & Sync indicator */}
          {!isCollapsed && activeModule !== 'VIEWER_3D' && (
            <div className="px-2 pt-1 flex items-center justify-between text-[10px] font-mono text-slate-600 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <Radio className="w-2.5 h-2.5 text-amber-500" /> Datos de ejemplo
              </span>
              <span className="text-slate-600 dark:text-slate-400">Cut-off: {project.cutOffGrade}%</span>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
