import { BlockModelItem } from '../types';

export interface BayesianInferenceParams {
  mcSamples: number;          // T = 50 to 500
  priorVariance: number;      // Prior weight sigma_0^2
  klWeight: number;           // beta for ELBO loss
  spatialMaternLengthscale: number; // ell (spatial kernel bandwidth)
  epistemicWeight: number;
  aleatoricBaseNoise: number;
}

export interface SimulationResult {
  meanGrade: number;
  epistemicUncertainty: number;
  aleatoricUncertainty: number;
  totalUncertainty: number;
  p10: number;
  p50: number;
  p90: number;
  cvPct: number;
  mcDraws: number[];
  dilutionRiskPct: number;
  economicTonnage: number;
  fineCuTonnes: number;
}

/**
 * Calculates Matern 5/2 Spatial Covariance Kernel
 */
export function matern52Kernel(distance: number, lengthscale: number, variance: number = 1.0): number {
  if (distance === 0) return variance;
  const scaledDist = (Math.sqrt(5) * distance) / lengthscale;
  const val = variance * (1.0 + scaledDist + (5.0 * distance * distance) / (3.0 * lengthscale * lengthscale)) * Math.exp(-scaledDist);
  return Math.max(0, val);
}

/**
 * Executes a simulated Monte Carlo Variational Inference pass on a single mining block
 */
export function runMonteCarloBlockInference(
  block: BlockModelItem,
  params: BayesianInferenceParams
): SimulationResult {
  const { mcSamples, spatialMaternLengthscale, epistemicWeight, aleatoricBaseNoise } = params;
  const draws: number[] = [];
  const aleatoricVariances: number[] = [];

  // Nearest drillhole influence modulated by Matern 5/2 spatial correlation
  const spatialCorrelation = matern52Kernel(block.nearest_drillhole_m, spatialMaternLengthscale, 1.0);
  
  // Base mean adjusted by spatial correlation to nearest assay
  const adjustedMean = block.cu_base + (spatialCorrelation * (block.cu_bayesian - block.cu_base));
  
  // Dynamic epistemic std dev based on distance and geological complexity
  const blockEpistemicStd = (block.epistemic_unc * epistemicWeight) / (0.3 + 0.7 * spatialCorrelation);
  const blockAleatoricStd = Math.max(0.02, aleatoricBaseNoise + block.aleatoric_unc * 0.5);

  for (let t = 0; t < mcSamples; t++) {
    // Box-Muller transform for standard Gaussian sampling
    const u1 = Math.max(1e-7, Math.random());
    const u2 = Math.random();
    const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    
    // Sample epistemic weight draw
    const y_hat_t = adjustedMean + z0 * blockEpistemicStd;
    draws.push(Math.max(0.01, y_hat_t));
    aleatoricVariances.push(blockAleatoricStd * blockAleatoricStd);
  }

  // Calculate Empirical Mean
  const meanGrade = draws.reduce((acc, v) => acc + v, 0) / mcSamples;

  // Epistemic Variance = 1/T * sum((y_hat_t - mean)^2)
  const epistemicVar = draws.reduce((acc, v) => acc + Math.pow(v - meanGrade, 2), 0) / mcSamples;
  const epistemicUncertainty = Math.sqrt(epistemicVar);

  // Aleatoric Variance = 1/T * sum(sigma_t^2)
  const aleatoricVar = aleatoricVariances.reduce((acc, v) => acc + v, 0) / mcSamples;
  const aleatoricUncertainty = Math.sqrt(aleatoricVar);

  // Total Predictive Uncertainty
  const totalVar = epistemicVar + aleatoricVar;
  const totalUncertainty = Math.sqrt(totalVar);

  // Sort draws for empirical percentiles
  const sortedDraws = [...draws].sort((a, b) => a - b);
  const p10Idx = Math.floor(mcSamples * 0.1);
  const p50Idx = Math.floor(mcSamples * 0.5);
  const p90Idx = Math.floor(mcSamples * 0.9);

  const p10 = sortedDraws[p10Idx] ?? (meanGrade - 1.28 * totalUncertainty);
  const p50 = sortedDraws[p50Idx] ?? meanGrade;
  const p90 = sortedDraws[p90Idx] ?? (meanGrade + 1.28 * totalUncertainty);

  const cvPct = (totalUncertainty / meanGrade) * 100;
  
  // Probability of grade being below economic cut-off (0.35% Cu)
  const subEconomicDraws = draws.filter(d => d < 0.35).length;
  const dilutionRiskPct = (subEconomicDraws / mcSamples) * 100;

  const isEconomic = meanGrade >= 0.35;
  const economicTonnage = isEconomic ? block.tonnage : 0;
  const fineCuTonnes = isEconomic ? (block.tonnage * meanGrade) / 100 : 0;

  return {
    meanGrade: Number(meanGrade.toFixed(3)),
    epistemicUncertainty: Number(epistemicUncertainty.toFixed(3)),
    aleatoricUncertainty: Number(aleatoricUncertainty.toFixed(3)),
    totalUncertainty: Number(totalUncertainty.toFixed(3)),
    p10: Number(p10.toFixed(3)),
    p50: Number(p50.toFixed(3)),
    p90: Number(p90.toFixed(3)),
    cvPct: Number(cvPct.toFixed(1)),
    mcDraws: draws.slice(0, 50),
    dilutionRiskPct: Number(dilutionRiskPct.toFixed(1)),
    economicTonnage,
    fineCuTonnes: Number(fineCuTonnes.toFixed(1))
  };
}

/**
 * Evaluates a hypothetical comparison over the example block model.
 */
export function computeBenchReconciliation(blocks: BlockModelItem[], cutOffGrade = 0.35) {
  const totalBlocks = blocks.length;
  let totalTonnage = 0;
  let baseOreTonnage = 0;
  let bayesianOreTonnage = 0;
  let baseFineCu = 0;
  let bayesianFineCu = 0;
  let measuredCount = 0;
  let indicatedCount = 0;
  let inferredCount = 0;
  let unclassifiedCount = 0;

  blocks.forEach(b => {
    totalTonnage += b.tonnage;
    if (b.cu_base >= cutOffGrade) {
      baseOreTonnage += b.tonnage;
      baseFineCu += (b.tonnage * b.cu_base) / 100;
    }
    if (b.cu_bayesian >= cutOffGrade) {
      bayesianOreTonnage += b.tonnage;
      bayesianFineCu += (b.tonnage * b.cu_bayesian) / 100;
    }

    if (b.category === 'Measured') measuredCount++;
    else if (b.category === 'Indicated') indicatedCount++;
    else if (b.category === 'Inferred') inferredCount++;
    else unclassifiedCount++;
  });

  const baseMeanGrade = baseOreTonnage > 0 ? (baseFineCu / baseOreTonnage) * 100 : 0;
  const bayesianMeanGrade = bayesianOreTonnage > 0 ? (bayesianFineCu / bayesianOreTonnage) * 100 : 0;

  // Reduced Dilution & Misclassification Gain calculation
  const misclassifiedBlocksSaved = blocks.filter(b => (b.cu_base < cutOffGrade && b.cu_bayesian >= cutOffGrade) || (b.cu_base >= cutOffGrade && b.cu_bayesian < cutOffGrade)).length;
  const oreLossAvoidedTonnes = blocks.filter(b => b.cu_base < cutOffGrade && b.cu_bayesian >= cutOffGrade).reduce((acc, b) => acc + b.tonnage, 0);
  const dilutionAvoidedTonnes = blocks.filter(b => b.cu_base >= cutOffGrade && b.cu_bayesian < cutOffGrade).reduce((acc, b) => acc + b.tonnage, 0);
  const denominator = totalBlocks || 1;

  return {
    totalBlocks,
    totalTonnage,
    baseOreTonnage,
    bayesianOreTonnage,
    baseMeanGrade: Number(baseMeanGrade.toFixed(3)),
    bayesianMeanGrade: Number(bayesianMeanGrade.toFixed(3)),
    baseFineCu: Math.round(baseFineCu),
    bayesianFineCu: Math.round(bayesianFineCu),
    metalGainTonnes: Math.round(bayesianFineCu - baseFineCu),
    misclassifiedBlocksSaved,
    oreLossAvoidedTonnes,
    dilutionAvoidedTonnes,
    categories: {
      measuredPct: Number(((measuredCount / denominator) * 100).toFixed(1)),
      indicatedPct: Number(((indicatedCount / denominator) * 100).toFixed(1)),
      inferredPct: Number(((inferredCount / denominator) * 100).toFixed(1)),
      unclassifiedPct: Number(((unclassifiedCount / denominator) * 100).toFixed(1))
    }
  };
}
