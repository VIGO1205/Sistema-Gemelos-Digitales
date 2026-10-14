import { 
  MiningProject, 
  BlockModelItem, 
  Drillhole, 
  HyperspectralPoint, 
  ProcessControlPoint, 
  TrainingLossHistory, 
  CalibrationBin, 
  ShapFeatureAttribution, 
  MiningAlert, 
  AuditLogEntry 
} from '../types';

export const MOCK_PROJECTS: MiningProject[] = [
  {
    id: 'proj-m6-esperanza',
    name: 'Mina Esperanza Sur - Rajo Principal',
    mineSite: 'Distrito Minero Centinela-Caracoles',
    country: 'Chile (Región de Antofagasta)',
    epsgCode: 'EPSG:32719 (WGS 84 / UTM Zone 19S)',
    primaryCommodity: 'Cu',
    secondaryCommodity: 'Au',
    cutOffGrade: 0.35,
    highGradeThreshold: 0.80,
    densityT_m3: 2.72,
    totalBlocks: 14500,
    activeBench: 3170,
    lastModelRun: '2026-08-29 08:30 UTC'
  },
  {
    id: 'proj-m6-norte',
    name: 'Rajo Centinela Norte - Fase 4B',
    mineSite: 'Complejo Minero Calama',
    country: 'Chile (Región de Antofagasta)',
    epsgCode: 'EPSG:32719 (WGS 84 / UTM Zone 19S)',
    primaryCommodity: 'Cu',
    secondaryCommodity: 'Mo',
    cutOffGrade: 0.40,
    highGradeThreshold: 0.95,
    densityT_m3: 2.68,
    totalBlocks: 9800,
    activeBench: 3140,
    lastModelRun: '2026-08-28 14:15 UTC'
  },
  {
    id: 'proj-m6-penon',
    name: 'Proyecto Quebrada Blanca - Rajo Este',
    mineSite: 'Distrito Collahuasi-Pica',
    country: 'Chile (Región de Tarapacá)',
    epsgCode: 'EPSG:32719 (WGS 84 / UTM Zone 19S)',
    primaryCommodity: 'Cu',
    secondaryCommodity: 'Ag',
    cutOffGrade: 0.30,
    highGradeThreshold: 0.75,
    densityT_m3: 2.75,
    totalBlocks: 12200,
    activeBench: 3185,
    lastModelRun: '2026-08-29 02:00 UTC'
  }
];

export const MOCK_PROJECT: MiningProject = MOCK_PROJECTS[0];

// Helper to generate 3D block model for an open-pit bench volume
export function generateBlockModel(): BlockModelItem[] {
  const blocks: BlockModelItem[] = [];
  const benches = [3200, 3185, 3170, 3155, 3140, 3125, 3110, 3095, 3080, 3065];
  const gridX = 12; // 12 columns
  const gridY = 12; // 12 rows
  const originX = 512400;
  const originY = 7416200;
  const blockSize = 15; // 15m x 15m x 15m bench block

  benches.forEach((benchZ, bIdx) => {
    for (let ix = 0; ix < gridX; ix++) {
      for (let iy = 0; iy < gridY; iy++) {
        const x = originX + ix * blockSize;
        const y = originY + iy * blockSize;
        const distFromCenter = Math.hypot(ix - 5.5, iy - 5.5);
        
        // Open pit conical footprint shape filter
        const pitRadiusLimit = 5.8 + (3200 - benchZ) / 30;
        if (distFromCenter > pitRadiusLimit) continue;

        // Mineralized core simulation (Porphyry Cu-Au core with hydrothermal halo)
        const coreDist = Math.hypot(ix - 5.0, iy - 6.0) + (3200 - benchZ) / 40;
        const baseGradeRaw = Math.max(0.08, 1.45 * Math.exp(-coreDist * 0.38) + (Math.sin(ix * 0.7) * Math.cos(iy * 0.8) * 0.18));
        const cu_base = Number(baseGradeRaw.toFixed(3));

        // Epistemic uncertainty is high where drillholes are sparse (periphery)
        const nearest_drillhole_m = Math.max(8, Number((coreDist * 9.5 + Math.abs(ix - iy) * 4.2).toFixed(1)));
        const epistemic_unc = Number((0.04 + (nearest_drillhole_m / 100) * 0.22 + (bIdx * 0.02)).toFixed(3));
        const aleatoric_unc = Number((0.03 + 0.04 * Math.random()).toFixed(3));
        const total_unc = Number(Math.hypot(epistemic_unc, aleatoric_unc).toFixed(3));

        // Multimodal Bayesian correction incorporates simulated drillhole + hyperspectral signature
        const correctionFactor = (Math.cos((ix + iy + bIdx) * 1.1) * 0.12) + (nearest_drillhole_m < 25 ? 0.08 : -0.05);
        const cu_bayesian = Number(Math.max(0.05, cu_base + correctionFactor).toFixed(3));
        const deviation_pct = Number((((cu_bayesian - cu_base) / cu_base) * 100).toFixed(1));

        // Percentiles
        const p10 = Number(Math.max(0.02, cu_bayesian - 1.28 * total_unc).toFixed(3));
        const p50 = cu_bayesian;
        const p90 = Number((cu_bayesian + 1.28 * total_unc).toFixed(3));
        const cv = total_unc / cu_bayesian;
        const confidence_pct = Number(Math.min(99.5, Math.max(45, (1 - Math.min(1, cv * 0.7)) * 100)).toFixed(1));

        // Lithology and Alteration determination
        let lithology: BlockModelItem['lithology'] = 'Pórfido Cuprífero';
        let alteration: BlockModelItem['alteration'] = 'Potásica';
        let dominant_mineral: BlockModelItem['dominant_mineral'] = 'Calcopirita';
        let hyperMineral = 'Illita + Calcopirita';

        if (coreDist < 2.5) {
          lithology = 'Brecha Hidrotermal';
          alteration = 'Potásica';
          dominant_mineral = 'Bornita';
          hyperMineral = 'Biotita Hidrotermal + Bornita (SWIR 2200nm)';
        } else if (coreDist < 4.5) {
          lithology = 'Pórfido Cuprífero';
          alteration = 'Fílica';
          dominant_mineral = 'Calcopirita';
          hyperMineral = 'Sericita / Illita Fílica (2206nm)';
        } else if (benchZ >= 3185 && iy > 7) {
          lithology = 'Skarn Mineralizado';
          alteration = 'Supérgena';
          dominant_mineral = 'Crisocola';
          hyperMineral = 'Crisocola + Malaquita (VNIR 680-850nm)';
        } else if (coreDist > 6.0) {
          lithology = 'Andesita Huinquintipa';
          alteration = 'Propilítica';
          dominant_mineral = 'Pirita';
          hyperMineral = 'Clorita + Epidota (2250nm/2330nm)';
        }

        // JORC Resource classification based on confidence and drillhole spacing
        let category: BlockModelItem['category'] = 'Inferred';
        if (nearest_drillhole_m <= 25 && epistemic_unc < 0.08) {
          category = 'Measured';
        } else if (nearest_drillhole_m <= 50 && epistemic_unc < 0.16) {
          category = 'Indicated';
        } else if (nearest_drillhole_m <= 90) {
          category = 'Inferred';
        } else {
          category = 'Unclassified';
        }

        const tonnage = Math.round(blockSize * blockSize * blockSize * 2.72); // ~9,180 tonnes per block
        const au_base = Number((cu_base * 0.28 + (Math.random() * 0.05)).toFixed(3));
        const au_bayesian = Number((cu_bayesian * 0.29 + (Math.random() * 0.04)).toFixed(3));

        blocks.push({
          id: `BLK-${benchZ}-${ix}-${iy}`,
          x,
          y,
          z: benchZ,
          bench: benchZ,
          dx: blockSize,
          dy: blockSize,
          dz: blockSize,
          cu_base,
          cu_bayesian,
          cu_variance: Number((total_unc * total_unc).toFixed(4)),
          au_base,
          au_bayesian,
          epistemic_unc,
          aleatoric_unc,
          total_unc,
          p10,
          p50,
          p90,
          confidence_pct,
          tonnage,
          density: 2.72,
          lithology,
          alteration,
          hyperspectral_mineral: hyperMineral,
          dominant_mineral,
          category,
          deviation_pct,
          nearest_drillhole_m
        });
      }
    }
  });

  return blocks;
}

export const MOCK_BLOCKS = generateBlockModel();
export const MOCK_BLOCK_MODEL = MOCK_BLOCKS;

export const MOCK_DRILLHOLES: Drillhole[] = [
  {
    hole_id: 'DDH-2026-081',
    type: 'DIAMOND_DDH',
    x: 512460,
    y: 7416260,
    z: 3205,
    total_depth_m: 140,
    azimuth: 180,
    dip: -75,
    date_drilled: '2026-08-12',
    samples: [
      { from_m: 0, to_m: 15, length_m: 15, cu_pct: 0.42, au_gpt: 0.12, lithology: 'Andesita Huinquintipa', alteration: 'Propilítica', recovery_pct: 98.5, rqd_pct: 82 },
      { from_m: 15, to_m: 45, length_m: 30, cu_pct: 0.98, au_gpt: 0.31, lithology: 'Pórfido Cuprífero', alteration: 'Fílica', recovery_pct: 99.1, rqd_pct: 88 },
      { from_m: 45, to_m: 90, length_m: 45, cu_pct: 1.45, au_gpt: 0.48, lithology: 'Brecha Hidrotermal', alteration: 'Potásica', recovery_pct: 99.4, rqd_pct: 92 },
      { from_m: 90, to_m: 140, length_m: 50, cu_pct: 1.15, au_gpt: 0.36, lithology: 'Pórfido Cuprífero', alteration: 'Potásica', recovery_pct: 98.0, rqd_pct: 85 }
    ]
  },
  {
    hole_id: 'DDH-2026-082',
    type: 'DIAMOND_DDH',
    x: 512500,
    y: 7416300,
    z: 3202,
    total_depth_m: 120,
    azimuth: 210,
    dip: -80,
    date_drilled: '2026-08-15',
    samples: [
      { from_m: 0, to_m: 20, length_m: 20, cu_pct: 0.35, au_gpt: 0.09, lithology: 'Andesita Huinquintipa', alteration: 'Propilítica', recovery_pct: 97.2, rqd_pct: 78 },
      { from_m: 20, to_m: 60, length_m: 40, cu_pct: 0.72, au_gpt: 0.22, lithology: 'Pórfido Cuprífero', alteration: 'Fílica', recovery_pct: 98.7, rqd_pct: 84 },
      { from_m: 60, to_m: 120, length_m: 60, cu_pct: 1.28, au_gpt: 0.39, lithology: 'Brecha Hidrotermal', alteration: 'Potásica', recovery_pct: 99.0, rqd_pct: 90 }
    ]
  },
  {
    hole_id: 'RC-2026-114',
    type: 'REVERSE_CIRCULATION_RC',
    x: 512420,
    y: 7416210,
    z: 3185,
    total_depth_m: 80,
    azimuth: 0,
    dip: -90,
    date_drilled: '2026-08-20',
    samples: [
      { from_m: 0, to_m: 25, length_m: 25, cu_pct: 1.12, au_gpt: 0.34, lithology: 'Brecha Hidrotermal', alteration: 'Potásica', recovery_pct: 95.0, rqd_pct: 75 },
      { from_m: 25, to_m: 80, length_m: 55, cu_pct: 1.34, au_gpt: 0.42, lithology: 'Brecha Hidrotermal', alteration: 'Potásica', recovery_pct: 96.2, rqd_pct: 80 }
    ]
  },
  {
    hole_id: 'BLAST-3170-A12',
    type: 'BLASTHOLE_TRICONO',
    x: 512475,
    y: 7416245,
    z: 3170,
    total_depth_m: 16.5,
    azimuth: 0,
    dip: -90,
    date_drilled: '2026-08-28',
    samples: [
      { from_m: 0, to_m: 16.5, length_m: 16.5, cu_pct: 1.22, au_gpt: 0.38, lithology: 'Brecha Hidrotermal', alteration: 'Potásica', recovery_pct: 99.5, rqd_pct: 91 }
    ]
  }
];

// Hyperspectral Spectral Signatures (400nm - 2500nm VNIR / SWIR)
export const HYPERSPECTRAL_SIGNATURES: { mineral: string; code: string; color: string; spectrum: { wavelength: number; reflectance: number }[] }[] = [
  {
    mineral: 'Illita / Sericita (Alteración Fílica)',
    code: 'ILL-F',
    color: '#38bdf8',
    spectrum: [
      { wavelength: 450, reflectance: 0.18 },
      { wavelength: 650, reflectance: 0.28 },
      { wavelength: 850, reflectance: 0.38 },
      { wavelength: 1050, reflectance: 0.44 },
      { wavelength: 1400, reflectance: 0.22 }, // H2O/OH absorption
      { wavelength: 1600, reflectance: 0.52 },
      { wavelength: 1900, reflectance: 0.19 }, // H2O absorption
      { wavelength: 2160, reflectance: 0.48 },
      { wavelength: 2206, reflectance: 0.12 }, // Distinctive Al-OH Sericite dip
      { wavelength: 2250, reflectance: 0.46 },
      { wavelength: 2350, reflectance: 0.35 },
      { wavelength: 2500, reflectance: 0.24 }
    ]
  },
  {
    mineral: 'Biotita Hidrotermal / Potásica',
    code: 'BIO-POT',
    color: '#f59e0b',
    spectrum: [
      { wavelength: 450, reflectance: 0.10 },
      { wavelength: 650, reflectance: 0.18 },
      { wavelength: 850, reflectance: 0.25 },
      { wavelength: 1050, reflectance: 0.31 },
      { wavelength: 1400, reflectance: 0.20 },
      { wavelength: 1600, reflectance: 0.36 },
      { wavelength: 1900, reflectance: 0.28 },
      { wavelength: 2160, reflectance: 0.38 },
      { wavelength: 2250, reflectance: 0.22 }, // Mg-OH / Fe-OH absorption
      { wavelength: 2325, reflectance: 0.14 }, // Biotite characteristic dip
      { wavelength: 2385, reflectance: 0.18 },
      { wavelength: 2500, reflectance: 0.15 }
    ]
  },
  {
    mineral: 'Clorita + Epidota (Propilítica)',
    code: 'CHL-EP',
    color: '#10b981',
    spectrum: [
      { wavelength: 450, reflectance: 0.12 },
      { wavelength: 650, reflectance: 0.22 },
      { wavelength: 850, reflectance: 0.19 }, // Fe2+ absorption in chlorite
      { wavelength: 1050, reflectance: 0.33 },
      { wavelength: 1400, reflectance: 0.25 },
      { wavelength: 1600, reflectance: 0.44 },
      { wavelength: 1900, reflectance: 0.30 },
      { wavelength: 2250, reflectance: 0.15 }, // Fe-OH / Chlorite absorption
      { wavelength: 2335, reflectance: 0.11 }, // Epidote / Chlorite peak
      { wavelength: 2450, reflectance: 0.26 },
      { wavelength: 2500, reflectance: 0.20 }
    ]
  },
  {
    mineral: 'Crisocola + Malaquita (Óxidos Supérgenos)',
    code: 'OX-CU',
    color: '#06b6d4',
    spectrum: [
      { wavelength: 450, reflectance: 0.22 },
      { wavelength: 650, reflectance: 0.45 },
      { wavelength: 850, reflectance: 0.14 }, // Strong Cu2+ absorption band ~800-900nm
      { wavelength: 1050, reflectance: 0.28 },
      { wavelength: 1400, reflectance: 0.15 },
      { wavelength: 1600, reflectance: 0.38 },
      { wavelength: 1900, reflectance: 0.12 },
      { wavelength: 2160, reflectance: 0.34 },
      { wavelength: 2270, reflectance: 0.18 },
      { wavelength: 2380, reflectance: 0.32 },
      { wavelength: 2500, reflectance: 0.25 }
    ]
  }
];

export const MOCK_SPECTRAL_SIGNATURES = HYPERSPECTRAL_SIGNATURES;

// CUSUM & EWMA Statistical Process Control (Reconciliation: Kriging Base vs Bayesian Twin vs Real Mill Feed)
export const MOCK_PROCESS_CONTROL: ProcessControlPoint[] = [
  { id: 'BL-01', blast_id: 'TR-3170-01', timestamp: '2026-08-01', bench: 3170, tonnage: 45200, plant_feed_grade: 1.18, predicted_base_krig: 0.95, predicted_bayesian: 1.15, residual_base: 0.23, residual_bayesian: 0.03, cusum_high: 0.18, cusum_low: 0.00, ewma_grade: 1.16, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-02', blast_id: 'TR-3170-02', timestamp: '2026-08-03', bench: 3170, tonnage: 48100, plant_feed_grade: 1.24, predicted_base_krig: 0.98, predicted_bayesian: 1.21, residual_base: 0.26, residual_bayesian: 0.03, cusum_high: 0.35, cusum_low: 0.00, ewma_grade: 1.19, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-03', blast_id: 'TR-3170-03', timestamp: '2026-08-06', bench: 3170, tonnage: 51200, plant_feed_grade: 1.05, predicted_base_krig: 0.88, predicted_bayesian: 1.02, residual_base: 0.17, residual_bayesian: 0.03, cusum_high: 0.30, cusum_low: 0.00, ewma_grade: 1.14, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-04', blast_id: 'TR-3170-04', timestamp: '2026-08-09', bench: 3170, tonnage: 47900, plant_feed_grade: 0.92, predicted_base_krig: 0.74, predicted_bayesian: 0.90, residual_base: 0.18, residual_bayesian: 0.02, cusum_high: 0.15, cusum_low: 0.00, ewma_grade: 1.06, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-05', blast_id: 'TR-3170-05', timestamp: '2026-08-12', bench: 3170, tonnage: 49800, plant_feed_grade: 1.35, predicted_base_krig: 1.02, predicted_bayesian: 1.31, residual_base: 0.33, residual_bayesian: 0.04, cusum_high: 0.42, cusum_low: 0.00, ewma_grade: 1.15, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-06', blast_id: 'TR-3170-06', timestamp: '2026-08-15', bench: 3170, tonnage: 52400, plant_feed_grade: 1.40, predicted_base_krig: 1.10, predicted_bayesian: 1.38, residual_base: 0.30, residual_bayesian: 0.02, cusum_high: 0.71, cusum_low: 0.00, ewma_grade: 1.23, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-07', blast_id: 'TR-3170-07', timestamp: '2026-08-18', bench: 3170, tonnage: 46700, plant_feed_grade: 1.28, predicted_base_krig: 1.05, predicted_bayesian: 1.26, residual_base: 0.23, residual_bayesian: 0.02, cusum_high: 0.88, cusum_low: 0.00, ewma_grade: 1.25, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-08', blast_id: 'TR-3170-08', timestamp: '2026-08-21', bench: 3170, tonnage: 50100, plant_feed_grade: 1.12, predicted_base_krig: 0.94, predicted_bayesian: 1.10, residual_base: 0.18, residual_bayesian: 0.02, cusum_high: 0.85, cusum_low: 0.00, ewma_grade: 1.20, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-09', blast_id: 'TR-3170-09', timestamp: '2026-08-24', bench: 3170, tonnage: 48900, plant_feed_grade: 1.08, predicted_base_krig: 0.91, predicted_bayesian: 1.06, residual_base: 0.17, residual_bayesian: 0.02, cusum_high: 0.79, cusum_low: 0.00, ewma_grade: 1.16, ucl: 1.30, lcl: 0.85, target_grade: 1.10 },
  { id: 'BL-10', blast_id: 'TR-3170-10', timestamp: '2026-08-27', bench: 3170, tonnage: 53100, plant_feed_grade: 1.19, predicted_base_krig: 0.97, predicted_bayesian: 1.18, residual_base: 0.22, residual_bayesian: 0.01, cusum_high: 0.86, cusum_low: 0.00, ewma_grade: 1.17, ucl: 1.30, lcl: 0.85, target_grade: 1.10 }
];

// ELBO Loss & Training Convergence
export const MOCK_TRAINING_HISTORY: TrainingLossHistory[] = [
  { epoch: 10, elbo_loss: 4.82, kl_divergence: 1.95, reconstruction_loss: 2.87, val_rmse: 0.38, ece_score: 0.142 },
  { epoch: 20, elbo_loss: 3.45, kl_divergence: 1.48, reconstruction_loss: 1.97, val_rmse: 0.29, ece_score: 0.098 },
  { epoch: 30, elbo_loss: 2.61, kl_divergence: 1.15, reconstruction_loss: 1.46, val_rmse: 0.22, ece_score: 0.071 },
  { epoch: 40, elbo_loss: 1.98, kl_divergence: 0.89, reconstruction_loss: 1.09, val_rmse: 0.17, ece_score: 0.052 },
  { epoch: 50, elbo_loss: 1.54, kl_divergence: 0.72, reconstruction_loss: 0.82, val_rmse: 0.13, ece_score: 0.041 },
  { epoch: 60, elbo_loss: 1.22, kl_divergence: 0.61, reconstruction_loss: 0.61, val_rmse: 0.10, ece_score: 0.034 },
  { epoch: 70, elbo_loss: 1.05, kl_divergence: 0.54, reconstruction_loss: 0.51, val_rmse: 0.08, ece_score: 0.028 },
  { epoch: 80, elbo_loss: 0.94, kl_divergence: 0.49, reconstruction_loss: 0.45, val_rmse: 0.07, ece_score: 0.024 },
  { epoch: 90, elbo_loss: 0.87, kl_divergence: 0.46, reconstruction_loss: 0.41, val_rmse: 0.06, ece_score: 0.021 },
  { epoch: 100, elbo_loss: 0.82, kl_divergence: 0.44, reconstruction_loss: 0.38, val_rmse: 0.05, ece_score: 0.018 }
];

// Calibration Reliability Bins (Expected Calibration Error = 0.018)
export const MOCK_CALIBRATION_BINS: CalibrationBin[] = [
  { confidence_bin: 0.1, empirical_accuracy: 0.11, count: 120 },
  { confidence_bin: 0.2, empirical_accuracy: 0.21, count: 240 },
  { confidence_bin: 0.3, empirical_accuracy: 0.30, count: 390 },
  { confidence_bin: 0.4, empirical_accuracy: 0.39, count: 580 },
  { confidence_bin: 0.5, empirical_accuracy: 0.51, count: 850 },
  { confidence_bin: 0.6, empirical_accuracy: 0.60, count: 1120 },
  { confidence_bin: 0.7, empirical_accuracy: 0.69, count: 1640 },
  { confidence_bin: 0.8, empirical_accuracy: 0.79, count: 2400 },
  { confidence_bin: 0.9, empirical_accuracy: 0.89, count: 3850 },
  { confidence_bin: 1.0, empirical_accuracy: 0.98, count: 3310 }
];

// XAI SHAP Values for Model Explainability
export const MOCK_SHAP_EXPLANATION: ShapFeatureAttribution[] = [
  { feature_name: 'Distancia a Sondaje DDH (m)', feature_val: '18.4 m', shap_value: +0.28, color: '#10b981' },
  { feature_name: 'Firma SWIR Al-OH (2206nm Dept)', feature_val: '0.68 Index', shap_value: +0.21, color: '#10b981' },
  { feature_name: 'Litología Brecha Hidrotermal', feature_val: 'BX_HYDR', shap_value: +0.18, color: '#10b981' },
  { feature_name: 'Kriging Ordinario Base Cu', feature_val: '0.95 %', shap_value: +0.12, color: '#10b981' },
  { feature_name: 'Profundidad de Banco (Z)', feature_val: '3170 m', shap_value: +0.06, color: '#10b981' },
  { feature_name: 'Alteración Propilítica Distal', feature_val: 'PROP_DIS', shap_value: -0.14, color: '#ef4444' },
  { feature_name: 'Anisotropía Variograma N45E', feature_val: '145 m Range', shap_value: -0.05, color: '#ef4444' }
];

// Mining Alerts
export const MOCK_ALERTS: MiningAlert[] = [
  {
    id: 'ALT-1049',
    type: 'HIGH_UNCERTAINTY',
    severity: 'CRITICAL',
    bench: 3155,
    block_id: 'BLK-3155-10-09',
    title: 'Zona de Alta Incertidumbre Epistémica (CV > 32%)',
    description: 'Bloque con espaciamiento de sondajes > 75m en el flanco Este. Requiere 2 pozos infill de control antes de voladura programada para el 04-Sep.',
    current_val: '34.2% CV (σ = 0.28% Cu)',
    threshold_val: 'Max 20.0% CV',
    timestamp: '2026-08-29 07:15 UTC',
    acknowledged: false,
    assignedRole: 'SENIOR_GEOLOGIST',
    action_recommended: 'Programar sondaje RC infill de 25m en coordenadas 512520E, 7416340N.'
  },
  {
    id: 'ALT-1048',
    type: 'GRADE_DEVIATION',
    severity: 'WARNING',
    bench: 3170,
    block_id: 'BLK-3170-04-05',
    title: 'Desviación Positiva de Ley (> +24% vs Kriging Base)',
    description: 'El modelo multimodal bayesiano detecta enriquecimiento supérgeno no capturado por el modelo de largo plazo debido a respuesta espectral de crisocola.',
    current_val: '1.24% Cu (Base: 0.98% Cu)',
    threshold_val: 'Delta > ±15%',
    timestamp: '2026-08-29 05:40 UTC',
    acknowledged: true,
    assignedRole: 'PLANNING_ENGINEER',
    action_recommended: 'Reclasificar bloque de Stock Baja Ley a Alimentación Directa Planta Concentradora.'
  },
  {
    id: 'ALT-1047',
    type: 'DILUTION_RISK',
    severity: 'WARNING',
    bench: 3185,
    block_id: 'BLK-3185-02-08',
    title: 'Riesgo de Dilución en Contacto Litológico',
    description: 'Contacto abrupto entre Skarn mineralizado y Andesita Huinquintipa estéril. Intervalo P10-P90 amplio [0.22% - 0.78% Cu].',
    current_val: 'P10 = 0.22% Cu (Sub-económico)',
    threshold_val: 'Cut-off = 0.35% Cu',
    timestamp: '2026-08-28 19:20 UTC',
    acknowledged: false,
    assignedRole: 'MINE_SUPERVISOR',
    action_recommended: 'Ajustar línea de marcación de pala (dig line) con buffer de seguridad de 3.5m.'
  }
];

// Audit Trail Logs
export const MOCK_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 'LOG-9921',
    timestamp: '2026-08-29 08:30:14',
    userId: 'usr-geo-01',
    userName: 'Dra. Elena Vasquez',
    userRole: 'SENIOR_GEOLOGIST',
    action: 'RUN_BAYESIAN_INFERENCE',
    module: 'Motor Bayesiano MFM v3.2',
    details: 'Ejecutó inferencia variacional MFM en Banco 3170 (124 bloques, 200 muestras MC). Tiempo: 1.42s.',
    ip_address: '10.24.112.45',
    status: 'SUCCESS'
  },
  {
    id: 'LOG-9920',
    timestamp: '2026-08-29 07:45:02',
    userId: 'usr-plan-04',
    userName: 'Ing. Carlos Mendoza',
    userRole: 'PLANNING_ENGINEER',
    action: 'EXPORT_REPORT_JORC',
    module: 'Generador de Reportes',
    details: 'Exportó Reporte Técnico PDF Compliance JORC 2012 para Fase 4B.',
    ip_address: '10.24.112.89',
    status: 'SUCCESS'
  },
  {
    id: 'LOG-9919',
    timestamp: '2026-08-29 06:12:33',
    userId: 'usr-sup-02',
    userName: 'Marco Arismendi',
    userRole: 'MINE_SUPERVISOR',
    action: 'ACKNOWLEDGE_ALERT',
    module: 'Alertas y Despacho',
    details: 'Confirmó lectura de Alerta ALT-1048 (Desviación Positiva de Ley en Banco 3170).',
    ip_address: '10.24.118.12',
    status: 'SUCCESS'
  },
  {
    id: 'LOG-9918',
    timestamp: '2026-08-28 22:10:19',
    userId: 'usr-geo-03',
    userName: 'Sofia Alarcon',
    userRole: 'JUNIOR_GEOLOGIST',
    action: 'UPLOAD_DRILLHOLE_ASSAY',
    module: 'Gestión Geoespacial',
    details: 'Cargó 48 intervalos de leyes para sondeo RC-2026-114.',
    ip_address: '10.24.112.50',
    status: 'SUCCESS'
  }
];
