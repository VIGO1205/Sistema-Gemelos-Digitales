import math
from typing import List


def matern52_kernel(distance: float, lengthscale: float, variance: float = 1.0) -> float:
    if distance == 0:
        return variance
    scaled_dist = (math.sqrt(5) * distance) / lengthscale
    val = variance * (
        1.0 + scaled_dist + (5.0 * distance * distance) / (3.0 * lengthscale * lengthscale)
    ) * math.exp(-scaled_dist)
    return max(0, val)


def run_monte_carlo_block_inference(
    cu_base: float,
    cu_bayesian: float,
    epistemic_unc: float,
    aleatoric_unc: float,
    nearest_drillhole_m: float,
    tonnage: int,
    mc_samples: int = 200,
    spatial_matern_lengthscale: float = 45.0,
    epistemic_weight: float = 1.0,
    aleatoric_base_noise: float = 0.04,
) -> dict:
    draws: List[float] = []
    aleatoric_variances: List[float] = []

    spatial_correlation = matern52_kernel(nearest_drillhole_m, spatial_matern_lengthscale, 1.0)
    adjusted_mean = cu_base + (spatial_correlation * (cu_bayesian - cu_base))
    block_epistemic_std = (epistemic_unc * epistemic_weight) / (0.3 + 0.7 * spatial_correlation)
    block_aleatoric_std = max(0.02, aleatoric_base_noise + aleatoric_unc * 0.5)

    for _ in range(mc_samples):
        u1 = max(1e-7, __import__("random").random())
        u2 = __import__("random").random()
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        y_hat_t = adjusted_mean + z0 * block_epistemic_std
        draws.append(max(0.01, y_hat_t))
        aleatoric_variances.append(block_aleatoric_std * block_aleatoric_std)

    mean_grade = sum(draws) / mc_samples
    epistemic_var = sum((v - mean_grade) ** 2 for v in draws) / mc_samples
    epistemic_uncertainty = math.sqrt(epistemic_var)
    aleatoric_var = sum(aleatoric_variances) / mc_samples
    aleatoric_uncertainty = math.sqrt(aleatoric_var)
    total_var = epistemic_var + aleatoric_var
    total_uncertainty = math.sqrt(total_var)

    sorted_draws = sorted(draws)
    p10_idx = int(mc_samples * 0.1)
    p50_idx = int(mc_samples * 0.5)
    p90_idx = int(mc_samples * 0.9)

    p10 = sorted_draws[p10_idx] if p10_idx < len(sorted_draws) else (mean_grade - 1.28 * total_uncertainty)
    p50 = sorted_draws[p50_idx] if p50_idx < len(sorted_draws) else mean_grade
    p90 = sorted_draws[p90_idx] if p90_idx < len(sorted_draws) else (mean_grade + 1.28 * total_uncertainty)

    cv_pct = (total_uncertainty / mean_grade) * 100 if mean_grade > 0 else 0
    sub_economic = sum(1 for d in draws if d < 0.35)
    dilution_risk_pct = (sub_economic / mc_samples) * 100

    is_economic = mean_grade >= 0.35
    economic_tonnage = tonnage if is_economic else 0
    fine_cu_tonnes = (tonnage * mean_grade) / 100 if is_economic else 0

    return {
        "mean_grade": round(mean_grade, 3),
        "epistemic_uncertainty": round(epistemic_uncertainty, 3),
        "aleatoric_uncertainty": round(aleatoric_uncertainty, 3),
        "total_uncertainty": round(total_uncertainty, 3),
        "p10": round(p10, 3),
        "p50": round(p50, 3),
        "p90": round(p90, 3),
        "cv_pct": round(cv_pct, 1),
        "mc_draws": draws[:50],
        "dilution_risk_pct": round(dilution_risk_pct, 1),
        "economic_tonnage": economic_tonnage,
        "fine_cu_tonnes": round(fine_cu_tonnes, 1),
    }


def compute_bench_reconciliation(blocks_data: List[dict]) -> dict:
    total_blocks = len(blocks_data)
    total_tonnage = 0
    base_ore_tonnage = 0
    bayesian_ore_tonnage = 0
    base_fine_cu = 0.0
    bayesian_fine_cu = 0.0
    measured_count = 0
    indicated_count = 0
    inferred_count = 0

    for b in blocks_data:
        total_tonnage += b.get("tonnage", 0)
        if b.get("cu_base", 0) >= 0.35:
            base_ore_tonnage += b.get("tonnage", 0)
            base_fine_cu += (b.get("tonnage", 0) * b.get("cu_base", 0)) / 100
        if b.get("cu_bayesian", 0) >= 0.35:
            bayesian_ore_tonnage += b.get("tonnage", 0)
            bayesian_fine_cu += (b.get("tonnage", 0) * b.get("cu_bayesian", 0)) / 100

        cat = b.get("category", "")
        if cat == "Measured":
            measured_count += 1
        elif cat == "Indicated":
            indicated_count += 1
        else:
            inferred_count += 1

    base_mean_grade = (base_fine_cu / base_ore_tonnage) * 100 if base_ore_tonnage > 0 else 0
    bayesian_mean_grade = (bayesian_fine_cu / bayesian_ore_tonnage) * 100 if bayesian_ore_tonnage > 0 else 0

    misclassified = sum(
        1 for b in blocks_data
        if (b.get("cu_base", 0) < 0.35 and b.get("cu_bayesian", 0) >= 0.35)
        or (b.get("cu_base", 0) >= 0.35 and b.get("cu_bayesian", 0) < 0.35)
    )
    ore_loss = sum(
        b.get("tonnage", 0) for b in blocks_data
        if b.get("cu_base", 0) < 0.35 and b.get("cu_bayesian", 0) >= 0.35
    )
    dilution = sum(
        b.get("tonnage", 0) for b in blocks_data
        if b.get("cu_base", 0) >= 0.35 and b.get("cu_bayesian", 0) < 0.35
    )

    return {
        "total_blocks": total_blocks,
        "total_tonnage": total_tonnage,
        "base_ore_tonnage": base_ore_tonnage,
        "bayesian_ore_tonnage": bayesian_ore_tonnage,
        "base_mean_grade": round(base_mean_grade, 3),
        "bayesian_mean_grade": round(bayesian_mean_grade, 3),
        "base_fine_cu": round(base_fine_cu),
        "bayesian_fine_cu": round(bayesian_fine_cu),
        "metal_gain_tonnes": round(bayesian_fine_cu - base_fine_cu),
        "misclassified_blocks_saved": misclassified,
        "ore_loss_avoided_tonnes": ore_loss,
        "dilution_avoided_tonnes": dilution,
        "categories": {
            "measured_pct": round((measured_count / total_blocks) * 100, 1) if total_blocks else 0,
            "indicated_pct": round((indicated_count / total_blocks) * 100, 1) if total_blocks else 0,
            "inferred_pct": round((inferred_count / total_blocks) * 100, 1) if total_blocks else 0,
        },
    }
