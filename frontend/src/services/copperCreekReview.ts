import type { BlockModelItem } from '../types';

export type ReviewKind = 'SUPPORT' | 'DISAGREEMENT' | 'VARIATION';

export interface ReviewSignal {
  id: string;
  bench: number;
  kind: ReviewKind;
  title: string;
  count: number;
  representative: BlockModelItem;
  observed: number;
  threshold: number;
  explanation: string;
  action: string;
}

export function percentile(values: number[], fraction: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * fraction))];
}

export function buildReviewSignals(blocks: BlockModelItem[], validationRmse: number): ReviewSignal[] {
  const benches = [...new Set(blocks.map(block => block.bench))].sort((a, b) => b - a);
  const variationP90 = percentile(blocks.map(block => block.epistemic_unc ?? 0), 0.9);
  const signals: ReviewSignal[] = [];
  for (const bench of benches) {
    const subset = blocks.filter(block => block.bench === bench);
    const support = subset.filter(block => block.support_holes === 3);
    if (support.length) {
      const representative = support.reduce((best, block) =>
        (block.nearest_drillhole_m ?? 0) > (best.nearest_drillhole_m ?? 0) ? block : best);
      signals.push({
        id: `SUPPORT-${bench}`, bench, kind: 'SUPPORT', title: 'Soporte mínimo de sondajes',
        count: support.length, representative, observed: 3, threshold: 3,
        explanation: 'Estos cubos cumplen justo el mínimo de tres sondajes independientes dentro de 120 m. La ley es exploratoria y requiere revisión de cobertura.',
        action: 'Revisar la ubicación y continuidad de los sondajes alrededor de estos cubos.',
      });
    }
    const disagreement = subset.filter(block =>
      Math.abs(block.cu_bayesian - (block.cu_idw3 ?? block.cu_base)) > validationRmse);
    if (disagreement.length) {
      const representative = disagreement.reduce((best, block) =>
        Math.abs(block.cu_bayesian - (block.cu_idw3 ?? block.cu_base)) >
        Math.abs(best.cu_bayesian - (best.cu_idw3 ?? best.cu_base)) ? block : best);
      signals.push({
        id: `DISAGREEMENT-${bench}`, bench, kind: 'DISAGREEMENT', title: 'Desacuerdo entre estimadores',
        count: disagreement.length, representative,
        observed: Math.abs(representative.cu_bayesian - (representative.cu_idw3 ?? representative.cu_base)),
        threshold: validationRmse,
        explanation: 'La diferencia entre el modelo seleccionado e IDW3 supera el RMSE de validación. Esto es una señal de revisión, no un error medido del cubo.',
        action: 'Comparar la geometría, los ensayos vecinos y la continuidad geológica antes de interpretar la ley.',
      });
    }
    const variation = subset.filter(block => (block.epistemic_unc ?? 0) >= variationP90);
    if (variation.length && variationP90 > 0) {
      const representative = variation.reduce((best, block) =>
        (block.epistemic_unc ?? 0) > (best.epistemic_unc ?? 0) ? block : best);
      signals.push({
        id: `VARIATION-${bench}`, bench, kind: 'VARIATION', title: 'Variación alta entre sondajes vecinos',
        count: variation.length, representative,
        observed: representative.epistemic_unc ?? 0, threshold: variationP90,
        explanation: 'La dispersión de ensayos vecinos está en el 10 % superior de la escena. No es una incertidumbre predictiva calibrada.',
        action: 'Contrastar los ensayos y considerar más información local antes de usar este sector en una decisión.',
      });
    }
  }
  return signals.sort((a, b) => b.count - a.count || b.bench - a.bench);
}
