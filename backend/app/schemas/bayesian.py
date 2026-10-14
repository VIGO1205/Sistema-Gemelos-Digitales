from pydantic import BaseModel
from typing import List


class BayesianInferenceParams(BaseModel):
    mc_samples: int = 200
    prior_variance: float = 1.0
    kl_weight: float = 0.15
    spatial_matern_lengthscale: float = 45.0
    epistemic_weight: float = 1.0
    aleatoric_base_noise: float = 0.04


class SimulationResult(BaseModel):
    mean_grade: float
    epistemic_uncertainty: float
    aleatoric_uncertainty: float
    total_uncertainty: float
    p10: float
    p50: float
    p90: float
    cv_pct: float
    mc_draws: List[float]
    dilution_risk_pct: float
    economic_tonnage: float
    fine_cu_tonnes: float


class BlockInferenceRequest(BaseModel):
    block_id: str
    params: BayesianInferenceParams


class BenchReconciliation(BaseModel):
    total_blocks: int
    total_tonnage: int
    base_ore_tonnage: int
    bayesian_ore_tonnage: int
    base_mean_grade: float
    bayesian_mean_grade: float
    base_fine_cu: int
    bayesian_fine_cu: int
    metal_gain_tonnes: int
    misclassified_blocks_saved: int
    ore_loss_avoided_tonnes: int
    dilution_avoided_tonnes: int
    categories: dict
