"""Regression tests for grouped uncertainty and immutable NN inference."""
import sys
from pathlib import Path
import unittest
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.nn_bayesian import DeepNN, NNBayesianKriging
from evaluation.statistical_tests import bootstrap_indices, paired_rmse_bootstrap
from evaluation.diagnostics import stability_curve


class ConstantKriging:
    def predict(self, X):
        return np.full(len(X), .2)
    def predict_with_uncertainty(self, X):
        pred = self.predict(X)
        return pred, pred * .1, pred - .1, pred + .1


class EvaluationIntegrity(unittest.TestCase):
    def test_group_bootstrap_never_splits_a_hole(self):
        groups = np.array([10, 10, 20, 20, 20, 30])
        rng = np.random.default_rng(42)
        for _ in range(50):
            indices = bootstrap_indices(len(groups), rng, groups)
            counts = np.bincount(indices, minlength=len(groups))
            for hole in np.unique(groups):
                self.assertEqual(len(set(counts[groups == hole])), 1)
            self.assertEqual(sum(counts[np.flatnonzero(groups == h)[0]] for h in np.unique(groups)), 3)

    def test_paired_bootstrap_identical_models_and_alignment(self):
        y = np.arange(12, dtype=float)
        b = paired_rmse_bootstrap(y, y + .5, y + .5, groups=np.repeat([1, 2, 3], 4), n_boot=50)
        self.assertEqual((b['diff_mean'], b['ci_lower'], b['ci_upper']), (0, 0, 0))
        self.assertEqual(b['unit'], 'sondaje')
        with self.assertRaises(ValueError):
            paired_rmse_bootstrap(y, y, y, groups=[1, 2])

    def test_mc_dropout_cannot_mutate_batchnorm_or_predictions(self):
        torch.manual_seed(7)
        model = NNBayesianKriging(hidden_dims=[8, 4], spatial_dims=3)
        model.device = torch.device('cpu')
        model.nn_model = DeepNN(3, [8, 4], .2)
        model.kriging_model = ConstantKriging()
        X = np.random.default_rng(5).normal(size=(20, 3))
        model.scaler.fit(X)
        before = model.predict(X)
        state = {k:v.clone() for k,v in model.nn_model.state_dict().items()}
        rng_before = torch.random.get_rng_state().clone()
        first = model.predict_with_uncertainty(X)
        second = model.predict_with_uncertainty(X)
        model.predict_with_uncertainty(X[:1])
        for k,v in model.nn_model.state_dict().items():
            self.assertTrue(torch.equal(v, state[k]), k)
        self.assertTrue(torch.equal(rng_before, torch.random.get_rng_state()))
        np.testing.assert_allclose(before, first[0])
        np.testing.assert_allclose(before, model.predict(X))
        np.testing.assert_allclose(first[1], second[1])
        self.assertTrue(np.any(first[1] > 0))

    def test_stability_zero_is_original_rmse_and_rejects_drift(self):
        model = ConstantKriging()
        X = np.zeros((12, 3))
        y = np.ones(12)
        result = stability_curve(model, X, y, model.predict(X), [0, .1])
        self.assertAlmostEqual(result['rmse'][0], .8)
        with self.assertRaises(ValueError):
            stability_curve(model, X, y, np.ones(12), [0, .1])


if __name__ == '__main__':
    unittest.main()
