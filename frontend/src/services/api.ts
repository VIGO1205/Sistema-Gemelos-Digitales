import axios from 'axios';
import type { ActiveModelData } from '../types';

// Use empty baseURL for relative paths (Vite proxy handles /api -> backend)
const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor for JWT auth tokens
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('m6_auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ─── Projects ───
export const projectApi = {
  getAll: () => api.get('/api/projects'),
  getById: (projectId: string) => api.get(`/api/projects/${projectId}`),
};

// ─── Blocks ───
export const blockApi = {
  getAll: (params?: { project_id?: number; bench?: number; min_cu_bayesian?: number; max_epistemic_unc?: number; category?: string }) =>
    api.get('/api/blocks', { params }),
  getById: (blockId: string) => api.get(`/api/blocks/${blockId}`),
};

// ─── Drillholes ───
export const drillholeApi = {
  getAll: (projectId?: number) => api.get('/api/drillholes', { params: projectId ? { project_id: projectId } : undefined }),
  getById: (holeId: string) => api.get(`/api/drillholes/${holeId}`),
};

// ─── Alerts ───
export const alertApi = {
  getAll: (params?: { project_id?: number; severity?: string; acknowledged?: boolean; dismissed?: boolean }) =>
    api.get('/api/alerts', { params }),
  getById: (alertId: string) => api.get(`/api/alerts/${alertId}`),
  acknowledge: (alertId: string) => api.patch(`/api/alerts/${alertId}/acknowledge`),
  dismiss: (alertId: string) => api.patch(`/api/alerts/${alertId}/dismiss`),
};

// ─── Bayesian Engine ───
export const bayesianApi = {
  runInference: (blockId: string, params: {
    mc_samples?: number;
    prior_variance?: number;
    kl_weight?: number;
    spatial_matern_lengthscale?: number;
    epistemic_weight?: number;
    aleatoric_base_noise?: number;
  }) => api.post(`/api/bayesian/inference/${blockId}`, params),
  getReconciliation: (projectId: number, bench?: number) =>
    api.get('/api/bayesian/reconciliation', { params: { project_id: projectId, bench } }),
};

// ─── Reports ───
export const reportApi = {
  exportExcel: (projectId: number) =>
    api.get('/api/reports/excel', { params: { project_id: projectId }, responseType: 'blob' }),
  getSummary: (projectId: number, bench?: number) =>
    api.get('/api/reports/summary', { params: { project_id: projectId, bench } }),
};

// ─── Audit Logs ───
export const auditLogApi = {
  getAll: (params?: { project_id?: number; user_role?: string; action?: string; limit?: number; offset?: number }) =>
    api.get('/api/audit-logs', { params }),
};

// ─── Process Control ───
export const processControlApi = {
  getAll: (params?: { project_id?: number; bench?: number }) =>
    api.get('/api/process-control', { params }),
};

// ─── Chat IA ───
export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatContext {
  active_bench?: number;
  selected_block_id?: string;
  selected_block_cu?: number;
  selected_block_lithology?: string;
  project_name?: string;
  cut_off_grade?: number;
  avg_bench_grade?: number;
  total_bench_tonnage?: number;
  user_role?: string;
  user_name?: string;
}

export const chatApi = {
  sendMessage: (messages: ChatMessage[], context?: ChatContext, sessionId?: string) =>
    api.post('/api/chat', { messages, context, session_id: sessionId }),
};

// ─── Reconciliation Mine-to-Mill ───
export const reconciliationApi = {
  get: (params: { project_id: number; bench?: number }) =>
    api.get('/api/reconciliation', { params }),
};

// ─── Economic Analysis ───
export const economicsApi = {
  get: (params: {
    project_id: number;
    bench?: number;
    cu_price_usd_lb?: number;
    au_price_usd_oz?: number;
    drilling_usd_ton?: number;
    blasting_usd_ton?: number;
    loading_usd_ton?: number;
    hauling_base_usd_ton?: number;
    hauling_slope_usd_ton_m?: number;
    processing_cost_usd_ton?: number;
    g_and_a_usd_ton?: number;
    concentrate_cu_pct?: number;
    payability_cu_pct?: number;
    payability_au_pct?: number;
    tc_usd_t?: number;
    rc_usd_lb?: number;
    freight_usd_t?: number;
  }) => api.get('/api/economics', { params }),
  getCutoffs: (params: {
    project_id: number;
    cu_price_usd_lb?: number;
    au_price_usd_oz?: number;
    drilling_usd_ton?: number;
    blasting_usd_ton?: number;
    loading_usd_ton?: number;
    hauling_base_usd_ton?: number;
    hauling_slope_usd_ton_m?: number;
    processing_cost_usd_ton?: number;
    g_and_a_usd_ton?: number;
    concentrate_cu_pct?: number;
    payability_cu_pct?: number;
    payability_au_pct?: number;
    tc_usd_t?: number;
    rc_usd_lb?: number;
    freight_usd_t?: number;
  }) => api.get('/api/economics/cutoffs', { params }),
};

// ─── Export ───
export const exportApi = {
  csvBlocks: (params: { project_id: number; bench?: number }) =>
    api.get('/api/blocks/export/csv', { params, responseType: 'blob' }),
};

// ─── Drillhole Planning ───
export const drillholePlanningApi = {
  get: (params: { project_id: number; bench?: number; limit?: number }) =>
    api.get('/api/drillhole-planning', { params }),
  drill: (payload: {
    project_id: number;
    block_id: string;
    depth_m?: number;
    hole_type?: string;
    azimuth?: number;
    dip?: number;
  }) => api.post('/api/drillhole-planning/drill', payload),
};

// ─── Active Models (Motor IA) ───
export const activeModelApi = {
  getActive: (bench?: number) =>
    api.get('/api/models/active', { params: bench !== undefined ? { bench } : undefined }),
  getAllActive: () => api.get<{ active_models: ActiveModelData[] }>('/api/models/active'),
  getBenchmark: (bench: number) =>
    api.get('/api/models/benchmark', { params: { bench } }),
  predict: (bench: number, opts?: { persist?: boolean; with_uncertainty?: boolean }) =>
    api.post('/api/models/predict', {
      bench,
      persist: opts?.persist ?? true,
      with_uncertainty: opts?.with_uncertainty ?? true,
    }),
};

export interface DrillholeExperimentMetadata {
  mode: 'drillholes_exploratory';
  dataset: string;
  model_name: string;
  features: ['x', 'y', 'z'];
  target: string;
  validation: string;
  sample_count: number;
  coordinate_bounds: Record<'x' | 'y' | 'z', { min: number; max: number; median: number }>;
  metrics: { rmse: number; mae: number; r2: number; composite_score?: number };
  exported_at: string;
}

export interface DrillholePointPrediction {
  success: boolean;
  mode: 'drillholes_exploratory';
  model_name: string;
  x: number;
  y: number;
  z: number;
  predicted_cu_pct: number;
  plausible: boolean;
  message: string;
}

export const drillholeExperimentApi = {
  info: () => api.get<{ success: boolean; model: DrillholeExperimentMetadata }>(
    '/api/models/experiments/drillholes/info'
  ),
  predict: (point: { x: number; y: number; z: number }) =>
    api.post<DrillholePointPrediction>(
      '/api/models/experiments/drillholes/predict', point
    ),
};

// ─── Despacho de Contramedidas ───
export interface DispatchResult {
  success: boolean;
  channel: string;
  label: string;
  alert_id: string;
  mode: 'WEBHOOK' | 'SIMULADO';
  webhook_url?: string | null;
  http_status?: number | null;
  message: string;
}

export const dispatchApi = {
  send: (alertId: string, channel: string) =>
    api.post<DispatchResult>('/api/dispatch', { alert_id: alertId, channel }),
};

// ─── Health Check ───
export const healthApi = {
  check: () => api.get('/health'),
};

export default api;
