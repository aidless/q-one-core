"""Cross-check dynamic filtering against dense joint Gaussian conditioning."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
import sys

import numpy as np
import pytest

from qone_core.life import AdaptiveKernel, ModelError
from qone_core.life.adaptive import BayesianTransition

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments'))
from two_scale import TwoScaleKernel, TwoScaleTransition

fixture = runpy.run_path(str(ROOT / 'examples/generate_adaptive_fixture.py'))['fixture']


def at(days):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=days)).isoformat()


def test_filter_equals_independent_dense_gp_posterior_for_irregular_times():
    x = np.array([[1., 2.], [1, -3], [1, 4], [1, 0]])
    y = np.array([2., -4, 1, 3])
    times = np.array([0., 2, 9, 21])
    precision, half, variance, alpha, beta = 1.3, 16, 0.7, 2.2, 0.8
    reg = TwoScaleTransition(2, half_life_days=half, transient_variance=variance,
                             precision=precision, alpha=alpha, beta=beta)
    for i in range(4):
        reg.update_at(x[i], float(y[i]), at(float(times[i])))
    # Batch reference marginalizes static coefficients and all OU states jointly.
    covariance = x @ x.T / precision + variance * 2 ** (-abs(times[:, None] - times) / half) + np.eye(4)
    inv_y = np.linalg.solve(covariance, y)
    expected_beta = beta + 0.5 * y @ inv_y
    for query_time in [21, 40, 200]:
        query = np.array([1., 0.4])
        reg.advance(at(query_time))
        p = reg.predict(query)
        cross = x @ query / precision + variance * 2 ** (-(query_time - times) / half)
        expected_mean = cross @ inv_y
        latent_variance = query @ query / precision + variance - cross @ np.linalg.solve(covariance, cross)
        expected_scale = np.sqrt(expected_beta / (alpha + 2) * (1 + latent_variance))
        assert p['mean'] == pytest.approx(expected_mean, abs=1e-12)
        assert p['scale'] == pytest.approx(expected_scale, abs=1e-12)
        assert reg.beta == pytest.approx(expected_beta, abs=1e-12)
        assert p['mean'] == pytest.approx(p['structural_mean_normalized'] + p['transient_mean_normalized'])


def test_zero_transient_variance_reduces_to_static_baseline():
    static = BayesianTransition(2)
    dynamic = TwoScaleTransition(2, half_life_days=16, transient_variance=0)
    for i in range(15):
        x, y = [1, i / 10], i % 3
        static.update(x, y)
        dynamic.update_at(x, y, at(i * 3))
    dynamic.advance(at(300))
    for key, expected in static.predict([1, 0.2]).items():
        if isinstance(expected, float):
            assert dynamic.predict([1, 0.2])[key] == pytest.approx(expected, abs=1e-12)


def test_elapsed_time_grows_transient_uncertainty_without_forgetting_static_structure():
    reg = TwoScaleTransition(2, half_life_days=16, transient_variance=1)
    for i in range(20):
        reg.update_at([1, i % 2], i % 3, at(i * 2))
    structural_mean, structural_cov = reg.mean[:-1].copy(), reg.cov[:-1, :-1].copy()
    transient_mean, transient_cov = reg.mean[-1], reg.cov[-1, -1]
    reg.advance(at(70))
    np.testing.assert_equal(reg.mean[:-1], structural_mean)
    np.testing.assert_equal(reg.cov[:-1, :-1], structural_cov)
    assert abs(reg.mean[-1]) < abs(transient_mean)
    assert transient_cov < reg.cov[-1, -1] < 1


def test_invalid_event_cannot_advance_state_and_time_cannot_run_backwards():
    reg = TwoScaleTransition(2, half_life_days=16, transient_variance=1)
    reg.update_at([1, 1], 3, at(2))
    before = reg.mean.copy(), reg.cov.copy(), reg.alpha, reg.beta, reg.time
    for x, y, t in [([1], 3, at(10)), ([1, 1], True, at(10)), ([1, 1], 2, at(1))]:
        with pytest.raises(ModelError):
            reg.update_at(x, y, t)
    np.testing.assert_equal(before[0], reg.mean)
    np.testing.assert_equal(before[1], reg.cov)
    assert before[2:] == (reg.alpha, reg.beta, reg.time)


def test_late_labels_use_event_time_not_arrival_order_and_are_unavailable_before_arrival():
    model = fixture()
    model['episodes'][40]['recorded_at'] = model['episodes'][70]['started_at']
    k = TwoScaleKernel(model, half_life_days=16, transient_variance=1)
    early = k.fitted(model['episodes'][60]['started_at'])
    assert 'e40' not in early['filter_episode_ids']
    late = k.fitted(model['episodes'][80]['started_at'])
    assert late['filter_episode_ids'].index('e40') == 40
    reference = TwoScaleKernel(fixture(), half_life_days=16, transient_variance=1).forecast(
        ['study'], model['episodes'][80]['started_at'])
    actual = k.forecast(['study'], model['episodes'][80]['started_at'])
    assert actual['predictions'] == reference['predictions']


def test_unreleased_future_labels_cannot_change_prediction_but_content_hash_changes():
    model = fixture()
    cutoff = model['episodes'][60]['started_at']
    original = TwoScaleKernel(model, half_life_days=16, transient_variance=1).forecast(['study'], cutoff)
    changed = deepcopy(model)
    obs = {o['id']: o for o in changed['observations']}
    for e in changed['episodes'][60:]:
        for oid in e['after'].values():
            obs[oid]['value'] += 200
    candidate = TwoScaleKernel(changed, half_life_days=16, transient_variance=1).forecast(['study'], cutoff)
    assert original['model_sha256'] != candidate['model_sha256']
    assert {k: v for k, v in original.items() if k != 'model_sha256'} == {
        k: v for k, v in candidate.items() if k != 'model_sha256'}


def test_old_labels_preserve_raw_support_and_query_state_aligns_to_outcome_end():
    model = fixture()
    k = TwoScaleKernel(model, half_life_days=16, transient_variance=1)
    result = k.forecast(['study'], at(297))
    assert result['status'] == AdaptiveKernel(model).forecast(['study'], at(297))['status']
    assert result['training_n'] == 96
    assert result['dynamics']['state_at'] == at(298)
    for p in result['predictions'].values():
        assert p['mean'] == pytest.approx(p['components']['structural_mean'] + p['components']['transient_mean'])
    assert k.forecast(['study'], at(0))['status'] == 'abstain'
    model['learning']['calibration'] = {'method': 'prequential_aci'}
    with pytest.raises(ModelError):
        TwoScaleKernel(model, half_life_days=16, transient_variance=1)


def test_measurement_and_executed_action_semantics_still_block_invalid_models():
    model = fixture()
    model['learning']['targets'][0]['unit'] = 'arbitrary_points'
    with pytest.raises(ModelError):
        TwoScaleKernel(model, half_life_days=16, transient_variance=1)
    model = fixture()
    model['actions'][0]['minutes'] += 30
    with pytest.raises(ModelError):
        TwoScaleKernel(model, half_life_days=16, transient_variance=1)
    model = fixture()
    correction = deepcopy(next(o for o in model['observations'] if o['id'] == 'e50-after-practice'))
    correction.update(id='correction', supersedes=correction['id'], recorded_at=at(297))
    model['observations'].append(correction)
    result = TwoScaleKernel(model, half_life_days=16, transient_variance=1).forecast(['study'], at(297))
    assert 'e50' not in result['training_episode_ids']
