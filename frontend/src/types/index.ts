export type ResourceCategory = 'Measured' | 'Indicated' | 'Inferred' | 'Unclassified';

export type CommodityType = 'Cu' | 'Au' | 'Ag' | 'Fe' | 'Mo';

export type UserRole = 
  | 'ADMIN' 
  | 'SENIOR_GEOLOGIST' 
  | 'JUNIOR_GEOLOGIST' 
  | 'PLANNING_ENGINEER' 
  | 'MINE_SUPERVISOR' 
  | 'VIEWER';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar: string;
  projectAccess: string[];
}

export interface MiningProject {
  id: string;
  databaseId?: number;
  name: string;
  mineSite: string;
  country: string;
  epsgCode: string;
  primaryCommodity: CommodityType;
  secondaryCommodity: CommodityType;
  cutOffGrade: number; // e.g. 0.35% Cu
  highGradeThreshold: number; // e.g. 0.85% Cu
  densityT_m3: number;
  totalBlocks: number;
  activeBench: number;
  lastModelRun: string;
}

export interface BlockModelItem {
  id: string;
  x: number;
  y: number;
  z: number;
  bench: number;
  // Dimensions
  dx: number;
  dy: number;
  dz: number;
  // Grades
  cu_base: number;       // Base Ordinary Kriging (%)
  cu_bayesian: number;   // Bayesian Fused Mean (%)
  cu_idw3?: number;      // Copper Creek IDW3 baseline (% Cu)
  support_holes?: number; // Independent nearby holes supporting a study block
  cu_variance: number;   // Variance
  au_base: number;       // g/t
  au_bayesian: number;   // g/t
  // Uncertainty Quantification
  epistemic_unc: number; // Model Uncertainty (std dev)
  aleatoric_unc: number; // Data Noise (std dev)
  total_unc: number;     // Combined uncertainty
  p10: number;           // 10th percentile (Pessimistic)
  p50: number;           // Median
  p90: number;           // 90th percentile (Optimistic)
  confidence_pct: number; // (1 - CV) * 100
  // Geology & Physical
  tonnage: number;
  density: number;
  lithology: 'Pórfido Cuprífero' | 'Brecha Hidrotermal' | 'Andesita Huinquintipa' | 'Skarn Mineralizado' | 'Lava Riolítica' | 'Sobrecarga/Estéril';
  alteration: 'Potásica' | 'Fílica' | 'Argílica Avanzada' | 'Propilítica' | 'Supérgena';
  hyperspectral_mineral: string;
  dominant_mineral: 'Calcopirita' | 'Bornita' | 'Calcosina' | 'Crisocola' | 'Pirita' | 'Malaquita' | 'Estéril';
  category: ResourceCategory;
  // Deviation
  deviation_pct: number; // ((cu_bayesian - cu_base) / cu_base) * 100
  nearest_drillhole_m: number;
}

export interface DrillholeSample {
  from_m: number;
  to_m: number;
  length_m: number;
  cu_pct: number;
  au_gpt: number;
  lithology: string;
  alteration: string;
  recovery_pct: number;
  rqd_pct: number;
}

export interface Drillhole {
  hole_id: string;
  type: 'DIAMOND_DDH' | 'REVERSE_CIRCULATION_RC' | 'BLASTHOLE_TRICONO';
  x: number;
  y: number;
  z: number;
  total_depth_m: number;
  azimuth: number;
  dip: number;
  date_drilled: string;
  samples: DrillholeSample[];
  trace?: [number, number, number][];
  trace_start_depth_m?: number;
}

export interface HyperspectralPoint {
  id: string;
  x: number;
  y: number;
  z: number;
  bench: number;
  spectral_signature: { wavelength_nm: number; reflectance: number }[];
  al_oh_depth_2200nm: number;
  fe_oxide_ratio: number;
  chlorite_index: number;
  classified_mineral: string;
  confidence: number;
}

export interface ProcessControlPoint {
  id: string;
  blast_id: string;
  timestamp: string;
  bench: number;
  tonnage: number;
  plant_feed_grade: number;     // Real mill / blast sample
  predicted_base_krig: number;  // Initial Ordinary Kriging
  predicted_bayesian: number;   // Bayesian Digital Twin
  predicted_active_model?: number | null;
  residual_base: number;
  residual_bayesian: number;
  residual_active?: number | null;
  cusum_high: number;
  cusum_low: number;
  ewma_grade: number;
  ucl: number;
  lcl: number;
  target_grade: number;
}

export interface TrainingLossHistory {
  epoch: number;
  elbo_loss: number;
  kl_divergence: number;
  reconstruction_loss: number;
  val_rmse: number;
  ece_score: number; // Expected Calibration Error
}

export interface CalibrationBin {
  confidence_bin: number;
  empirical_accuracy: number;
  count: number;
}

export interface ShapFeatureAttribution {
  feature_name: string;
  feature_val: string | number;
  shap_value: number;
  color: string;
}

export interface MiningAlert {
  id: string;
  type: 'HIGH_UNCERTAINTY' | 'GRADE_DEVIATION' | 'DILUTION_RISK' | 'ORE_LOSS_RISK' | 'CALIBRATION_DRIFT' | 'MODEL_ACTIVATED';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  bench: number;
  block_id: string;
  title: string;
  description: string;
  current_val: string;
  threshold_val: string;
  timestamp: string;
  acknowledged: boolean;
  assignedRole: UserRole;
  action_recommended: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  userRole: UserRole;
  action: string;
  module: string;
  details: string;
  ip_address: string;
  status: 'SUCCESS' | 'WARNING' | 'BLOCKED';
}

export type DrillholeAssay = Drillhole;

export interface ActiveModelData {
  bench: number;
  model_name: string;
  composite_score: number | null;
  rmse: number | null;
  r2: number | null;
  mae: number | null;
  mape: number | null;
  bias: number | null;
  activated_at: string | null;
}

export interface HyperspectralSignature {
  mineral: string;
  code: string;
  color: string;
  spectrum: { wavelength: number; reflectance: number }[];
}

