"""Research challenger invariants; no claim of measured personal benefit."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import runpy
import sys

import numpy as np
import pytest

from qone_core.life import AdaptiveKernel, ModelError
from qone_core.life.adaptive import BayesianTransition

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments'))
from recency_power import PowerTransition, RecencyKernel, event_weight, information

fixture = runpy.run_path(str(ROOT / 'examples/generate_adaptive_fixture.py'))['fixture']
spec = spec_from_file_location('recency_evaluator', ROOT / 'scripts/evaluate_recency.py')
evaluator = module_from_spec(spec)
spec.loader.exec_module(evaluator)


def test_weighted_updates_equal_independent_batch_posterior_and_permutation():
    x = np.array([[1., 2], [1, -3], [1, 4], [1, 0]])
    y = np.array([2., -4, 1, 10])
    w = np.array([1., 0.2, 0.5, 0])
    precision, alpha, beta = 1.3, 2.2, 0.7
    a = precision * np.eye(2) + x.T @ (w[:, None] * x)
    expected_mean = np.linalg.solve(a, x.T @ (w * y))
    expected_cov = np.linalg.inv(a)
    expected_beta = beta + 0.5 * (sum(w * y * y) - expected_mean @ a @ expected_mean)
    for order in [range(4), reversed(range(4))]:
        reg = PowerTransition(2, precision=precision, alpha=alpha, beta=beta)
        for i in order:
            reg.update(x[i], float(y[i]), weight=float(w[i]))
        np.testing.assert_allclose(reg.mean, expected_mean, atol=1e-12)
        np.testing.assert_allclose(reg.cov, expected_cov, atol=1e-12)
        assert reg.beta == pytest.approx(expected_beta, abs=1e-12)
        assert reg.alpha == pytest.approx(alpha + sum(w) / 2)
        assert reg.n == 4


def test_unit_weights_match_lifetime_model_and_zero_weight_keeps_prior():
    old, new = BayesianTransition(2), PowerTransition(2)
    for i in range(15):
        x, y = [1, i / 10], i % 3
        old.update(x, y)
        new.update(x, y)
    for k, v in old.predict([1, 0.3]).items():
        if isinstance(v, float):
            assert new.predict([1, 0.3])[k] == pytest.approx(v, abs=1e-12)
    zero = PowerTransition(2)
    zero.update([1, 2], 100, weight=0)
    assert zero.beta == 1 and zero.alpha == 2
    np.testing.assert_equal(zero.cov, np.eye(2))
    np.testing.assert_equal(zero.mean, np.zeros(2))


def test_invalid_weight_does_not_mutate_model_and_ess_is_not_information_mass():
    reg = PowerTransition(2)
    for w in [-1, 1.01, True, float('nan')]:
        with pytest.raises(ModelError):
            reg.update([1, 1], 3, weight=w)
    assert reg.n == 0 and reg.beta == 1 and reg.alpha == 2
    stats = information([1e-9] * 100)
    assert stats['weight_concentration_ess'] == pytest.approx(100)
    assert stats['weight_mass'] == pytest.approx(1e-7)


def test_event_age_is_calendar_time_not_late_label_arrival():
    assert event_weight('2026-01-01T00:00:00Z', '2026-02-02T00:00:00Z', 32) == 0.5
    assert event_weight('2026-01-01T00:00:00Z', '2026-02-02T00:00:00Z', 16) == 0.25
    with pytest.raises(ModelError):
        event_weight('2026-02-02T00:00:00Z', '2026-01-01T00:00:00Z', 32)
    model = fixture()
    model['episodes'][0]['recorded_at'] = model['episodes'][80]['started_at']
    k = RecencyKernel(model, half_life_days=32)
    cutoff = model['episodes'][80]['started_at']
    fit = k.fitted(cutoff)
    weights = [event_weight(e['ended_at'], cutoff, 32) for e in fit['episodes']]
    assert fit['information']['weight_mass'] == pytest.approx(sum(weights))
    assert event_weight(model['episodes'][0]['ended_at'], cutoff, 32) < 0.04


def test_future_and_delayed_outcomes_cannot_change_current_prediction():
    model = fixture()
    cutoff = model['episodes'][80]['started_at']
    model['episodes'][30]['recorded_at'] = model['episodes'][90]['started_at']
    before = RecencyKernel(model, half_life_days=32).forecast(['study'], cutoff)
    mutated = deepcopy(model)
    observations = {o['id']: o for o in mutated['observations']}
    for e in [mutated['episodes'][30], *mutated['episodes'][80:]]:
        for oid in e['after'].values():
            observations[oid]['value'] += 200
    after = RecencyKernel(mutated, half_life_days=32).forecast(['study'], cutoff)
    assert before['model_sha256'] != after['model_sha256']
    assert {k: v for k, v in before.items() if k != 'model_sha256'} == {
        k: v for k, v in after.items() if k != 'model_sha256'}
    assert 'e30' not in before['training_episode_ids']
    baseline_before = AdaptiveKernel(model).forecast(['study'], cutoff)
    AdaptiveKernel(mutated).forecast(['study'], cutoff)
    assert baseline_before == AdaptiveKernel(model).forecast(['study'], cutoff)


def test_old_history_abstains_and_corrections_remove_superseded_evidence():
    model = fixture()
    at = '2026-10-25T00:00:00Z'
    old = AdaptiveKernel(model).forecast(['study'], at)
    candidate = RecencyKernel(model, half_life_days=32).forecast(['study'], at)
    assert old['status'] == 'supported_prediction'
    assert candidate['status'] == 'abstain'
    assert candidate['training_n'] == 96
    assert candidate['information']['weight_mass'] < 20
    assert candidate['information']['weight_concentration_ess'] > 20
    assert {'insufficient_recent_information', 'insufficient_recent_portfolio_information'} <= {
        i['code'] for i in candidate['issues']}
    o = deepcopy(next(o for o in model['observations'] if o['id'] == 'e50-after-practice'))
    o.update(id='correction', supersedes=o['id'], recorded_at=at)
    model['observations'].append(o)
    assert 'e50' not in RecencyKernel(model, half_life_days=32).forecast(['study'], at)['training_episode_ids']


def test_gate_rejects_injected_miss_and_reports_abstention():
    base = {'episode_id': 'e0', 'supported': True, 'covered': True,
            'absolute_error': 1, 'width': 2, 'interval_score': 2}
    gate = {'finite_rate_at_least': 0.9, 'coverage_at_least': 0.85,
            'paired_rate_at_least': 0.9, 'paired_mae_ratio_at_most': 1.05,
            'paired_interval_score_ratio_at_most': 1.05}
    assert evaluator.summarize([base], {'e0': base}, gate)['passes']
    missed = {**base, 'covered': False, 'absolute_error': 100, 'interval_score': 1000}
    assert not evaluator.summarize([missed], {'e0': base}, gate)['passes']
    rejected = evaluator.summarize([{**base, 'supported': False}], {'e0': base}, gate)
    assert not rejected['passes'] and rejected['coverage'] is None and rejected['paired_n'] == 0


def test_irregular_delayed_scenario_is_valid_and_challenger_is_not_calibration():
    model = evaluator.scenario(1, 'irregular_delayed_mean_shift', 70, 64)
    k = RecencyKernel(model, half_life_days=32)
    at = model['episodes'][64]['started_at']
    assert k.forecast([], at)['status'] == 'abstain'
    assert model['episodes'][65]['recorded_at'] > model['episodes'][65]['ended_at']
    model['learning']['calibration'] = {'method': 'prequential_aci'}
    with pytest.raises(ModelError):
        RecencyKernel(model, half_life_days=32)
