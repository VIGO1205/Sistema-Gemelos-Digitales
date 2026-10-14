import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  MiningProject,
  BlockModelItem,
  DrillholeAssay,
  HyperspectralSignature,
  MiningAlert,
  AuditLogEntry,
  ProcessControlPoint,
} from '../types';
import api, {
  projectApi,
  blockApi,
  drillholeApi,
  alertApi,
  auditLogApi,
  processControlApi,
} from '../services/api';
import { getAuthToken } from '../services/authApi';
import { useAuth } from './AuthContext';

interface DataContextType {
  project: MiningProject | null;
  blocks: BlockModelItem[];
  drillholes: DrillholeAssay[];
  signatures: HyperspectralSignature[];
  alerts: MiningAlert[];
  auditLogs: AuditLogEntry[];
  processControl: ProcessControlPoint[];
  loading: boolean;
  error: string | null;
  refreshData: () => void;
  acknowledgeAlert: (alertId: string) => Promise<void>;
  dismissAlert: (alertId: string) => Promise<void>;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export function DataProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();

  const [project, setProject] = useState<MiningProject | null>(null);
  const [blocks, setBlocks] = useState<BlockModelItem[]>([]);
  const [drillholes, setDrillholes] = useState<DrillholeAssay[]>([]);
  const [signatures, setSignatures] = useState<HyperspectralSignature[]>([]);
  const [alerts, setAlerts] = useState<MiningAlert[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [processControl, setProcessControl] = useState<ProcessControlPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const clearData = useCallback(() => {
    setProject(null);
    setBlocks([]);
    setDrillholes([]);
    setSignatures([]);
    setAlerts([]);
    setAuditLogs([]);
    setProcessControl([]);
    setError(null);
    setLoading(false);
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    // Skip data fetch if not authenticated
    if (!getAuthToken()) {
      setLoading(false);
      return;
    }

    try {
      // 1. Fetch project
      const projRes = await projectApi.getById('proj-m6-esperanza');
      const projData = projRes.data;
      const mappedProject: MiningProject = {
        id: projData.project_id,
        databaseId: projData.id,
        name: projData.name,
        mineSite: projData.mine_site,
        country: projData.country,
        epsgCode: projData.epsg_code,
        primaryCommodity: projData.primary_commodity,
        secondaryCommodity: projData.secondary_commodity,
        cutOffGrade: projData.cut_off_grade,
        highGradeThreshold: projData.high_grade_threshold,
        densityT_m3: projData.density_t_m3,
        totalBlocks: projData.total_blocks,
        activeBench: projData.active_bench,
        lastModelRun: projData.last_model_run,
      };
      setProject(mappedProject);

      // 2. Fetch blocks
      const blocksRes = await blockApi.getAll({ project_id: projData.id });
      const mappedBlocks: BlockModelItem[] = blocksRes.data.map((b: any) => ({
        id: b.block_id,
        x: b.x,
        y: b.y,
        z: b.z,
        bench: b.bench,
        dx: b.dx,
        dy: b.dy,
        dz: b.dz,
        cu_base: b.cu_base,
        cu_bayesian: b.cu_bayesian,
        cu_variance: b.cu_variance,
        au_base: b.au_base,
        au_bayesian: b.au_bayesian,
        epistemic_unc: b.epistemic_unc,
        aleatoric_unc: b.aleatoric_unc,
        total_unc: b.total_unc,
        p10: b.p10,
        p50: b.p50,
        p90: b.p90,
        confidence_pct: b.confidence_pct,
        tonnage: b.tonnage,
        density: b.density,
        lithology: b.lithology,
        alteration: b.alteration,
        hyperspectral_mineral: b.hyperspectral_mineral,
        dominant_mineral: b.dominant_mineral,
        category: b.category,
        deviation_pct: b.deviation_pct,
        nearest_drillhole_m: b.nearest_drillhole_m,
      }));
      setBlocks(mappedBlocks);

      // 3. Fetch drillholes
      const dhRes = await drillholeApi.getAll(projData.id);
      const mappedDrillholes: DrillholeAssay[] = dhRes.data.map((dh: any) => ({
        hole_id: dh.hole_id,
        type: dh.hole_type,
        x: dh.x,
        y: dh.y,
        z: dh.z,
        total_depth_m: dh.total_depth_m,
        azimuth: dh.azimuth,
        dip: dh.dip,
        date_drilled: dh.date_drilled,
        samples: dh.samples.map((s: any) => ({
          from_m: s.from_m,
          to_m: s.to_m,
          length_m: s.length_m,
          cu_pct: s.cu_pct,
          au_gpt: s.au_gpt,
          lithology: s.lithology,
          alteration: s.alteration,
          recovery_pct: s.recovery_pct,
          rqd_pct: s.rqd_pct,
        })),
      }));
      setDrillholes(mappedDrillholes);

      // 4. Fetch hyperspectral signatures
      try {
        const sigRes = await api.get('/api/hyperspectral', { params: { project_id: projData.id } });
        const sigData = sigRes.data;
        const mappedSigs: HyperspectralSignature[] = sigData.map((s: any) => ({
          mineral: s.mineral,
          code: s.code,
          color: s.color,
          spectrum: s.spectrum.map((p: any) => ({
            wavelength: p.wavelength,
            reflectance: p.reflectance,
          })),
        }));
        setSignatures(mappedSigs);
      } catch {
        // Fallback: keep empty
      }

      // 5. Fetch alerts
      const alertRes = await alertApi.getAll({ project_id: projData.id });
      const mappedAlerts: MiningAlert[] = alertRes.data.map((a: any) => ({
        id: a.alert_id,
        type: a.alert_type,
        severity: a.severity,
        bench: a.bench,
        block_id: a.block_id,
        title: a.title,
        description: a.description,
        current_val: a.current_val,
        threshold_val: a.threshold_val,
        timestamp: a.timestamp,
        acknowledged: a.acknowledged,
        assignedRole: a.assigned_role,
        action_recommended: a.action_recommended,
      }));
      setAlerts(mappedAlerts);

      // 6. Fetch audit logs
      const logRes = await auditLogApi.getAll({ project_id: projData.id, limit: 100 });
      const mappedLogs: AuditLogEntry[] = logRes.data.map((l: any) => ({
        id: l.log_id,
        timestamp: l.timestamp,
        userId: l.user_id,
        userName: l.user_name,
        userRole: l.user_role,
        action: l.action,
        module: l.module,
        details: l.details,
        ip_address: l.ip_address,
        status: l.status,
      }));
      setAuditLogs(mappedLogs);

      // 7. Fetch process control
      const pcRes = await processControlApi.getAll({ project_id: projData.id });
      const mappedPC: ProcessControlPoint[] = pcRes.data.map((p: any) => ({
        id: p.point_id,
        blast_id: p.blast_id,
        timestamp: p.timestamp,
        bench: p.bench,
        tonnage: p.tonnage,
        plant_feed_grade: p.plant_feed_grade,
        predicted_base_krig: p.predicted_base_krig,
        predicted_bayesian: p.predicted_bayesian,
        predicted_active_model: p.predicted_active_model,
        residual_base: p.residual_base,
        residual_bayesian: p.residual_bayesian,
        residual_active: p.residual_active,
        cusum_high: p.cusum_high,
        cusum_low: p.cusum_low,
        ewma_grade: p.ewma_grade,
        ucl: p.ucl,
        lcl: p.lcl,
        target_grade: p.target_grade,
      }));
      setProcessControl(mappedPC);

    } catch (err: any) {
      console.error('Error loading data from backend:', err);
      setError(err.message || 'Error al cargar datos del servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  // Acknowledge alert: optimistic update + API call
  const acknowledgeAlert = useCallback(async (alertId: string) => {
    // Optimistic update: mark as acknowledged locally immediately
    setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, acknowledged: true } : a));
    
    try {
      await alertApi.acknowledge(alertId);
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      // Revert on error
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, acknowledged: false } : a));
    }
  }, []);

  // Dismiss alert: optimistic removal + API call
  const dismissAlert = useCallback(async (alertId: string) => {
    // Optimistic update: remove from list locally immediately
    setAlerts(prev => prev.filter(a => a.id !== alertId));

    try {
      await alertApi.dismiss(alertId);
    } catch (err) {
      console.error('Error dismissing alert:', err);
    }
  }, []);

  // Auto-fetch data when auth state changes
  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    } else {
      clearData();
    }
  }, [isAuthenticated, fetchData, clearData]);

  return (
    <DataContext.Provider
      value={{
        project,
        blocks,
        drillholes,
        signatures,
        alerts,
        auditLogs,
        processControl,
        loading,
        error,
        refreshData: fetchData,
        acknowledgeAlert,
        dismissAlert,
      }}
    >
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
}
