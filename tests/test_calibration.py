from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import runpy
import pytest
from qone_core.life import AdaptiveKernel,ModelError
from qone_core.life.calibration import DelayedACI,calibration_config
from qone_core.life.model import fingerprint,instant

fixture=runpy.run_path(str(Path(__file__).parents[1]/'examples/generate_adaptive_fixture.py'))['fixture']
AT='2026-10-25T00:00:00Z'


def at(day):return (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=day)).isoformat()


def calibrated(count=96):
    model=fixture(count=count)
    model['learning']['calibration']={'method':'prequential_aci','min_samples':10,'window':64,'step_size':0.01}
    return model


def warm(cal):
    for i in range(5):
        cal.issue(str(i),at(2*i),mean=0,scale=1)
        cal.observe(str(i),at(2*i+1),i+1)


def test_finite_rank_warmup_and_pending_labels():
    c=DelayedACI(target_alpha=0.2,min_samples=5,window=5); warm(c)
    p=c.issue('pending',at(11),mean=10,scale=2)
    assert p['radius']==5 and p['calibration_n']==5
    assert 'pending' not in c.interval()['score_ids']
    assert c.interval()['adjusted_alpha']==pytest.approx(0.2)
    with pytest.raises(ModelError):c.observe('pending',at(10),12)
    assert c.observe('pending',at(12),12)['error'] is False
    with pytest.raises(ModelError):c.observe('pending',at(13),12)


def test_delayed_feedback_checks_original_interval_not_current_quantile():
    c=DelayedACI(target_alpha=0.2,step_size=0,min_samples=5,window=5);warm(c)
    c.issue('delayed',at(11),mean=0,scale=1)
    for i in range(5):
        c.issue('new'+str(i),at(12+2*i),mean=0,scale=1)
        c.observe('new'+str(i),at(13+2*i),0.1)
    assert c.interval()['radius']==0.1
    assert c.observe('delayed',at(30),4)['error'] is False


def test_unbounded_and_empty_states_are_abstentions_and_recover():
    c=DelayedACI(target_alpha=0.1,step_size=0.2,min_samples=5,window=5);warm(c)
    assert c.interval()['status']=='unbounded'
    for i in range(30):
        p=c.issue('u'+str(i),at(11+2*i),mean=0,scale=1)
        c.observe('u'+str(i),at(12+2*i),0)
    assert c.interval()['status']=='ready'
    # Mathematical extreme is preserved explicitly, never clipped into false certainty.
    c.alpha=1.1
    assert c.interval()['status']=='empty'
    assert c.interval()['radius'] is None
    json.dumps(c.interval(),allow_nan=False)


def test_validation_rejects_invalid_config_and_failed_events_do_not_mutate_time():
    for value in [{'method':'unknown'},{'method':'prequential_aci','window':4},{'method':'prequential_aci','step_size':True},{'method':'prequential_aci','surprise':1}]:
        with pytest.raises(ModelError):calibration_config(value)
    c=DelayedACI(target_alpha=0.1)
    with pytest.raises(ModelError):c.observe('missing',at(200),1)
    assert c.issue('valid',at(0),mean=0,scale=1)['status']=='insufficient_calibration'


def test_future_outcomes_and_delayed_labels_do_not_change_current_forecast():
    model=calibrated(); cutoff=model['episodes'][80]['started_at']
    original=AdaptiveKernel(model).forecast(['study'],cutoff)
    changed=deepcopy(model)
    for e in changed['episodes'][81:]:
        for oid in e['after'].values():
            next(o for o in changed['observations'] if o['id']==oid)['value']+=200
    actual=AdaptiveKernel(changed).forecast(['study'],cutoff)
    assert original['predictions']==actual['predictions']
    for p in original['predictions'].values():
        assert instant(p['calibration']['last_score_recorded_at'])<=instant(cutoff)
    changed=deepcopy(model);changed['episodes'][40]['recorded_at']=at(250)
    past=AdaptiveKernel(changed).calibration_history(cutoff)
    token=fingerprint({'episode_id':'e40','measure_id':'practice'})
    assert token not in past['issued']


def test_insufficient_shadow_calibration_never_changes_authoritative_bounds():
    model=calibrated(count=32); original=deepcopy(model);original['learning'].pop('calibration')
    result=AdaptiveKernel(model).forecast(['study'],AT)
    baseline=AdaptiveKernel(original).forecast(['study'],AT)
    assert result['status']==baseline['status']
    for mid,p in result['predictions'].items():
        assert p['calibration']['status']=='insufficient_calibration'
        assert p['candidate_interval'] is None
        assert p['lower']==baseline['predictions'][mid]['lower']
        assert p['upper']==baseline['predictions'][mid]['upper']
    json.dumps(AdaptiveKernel(model).simulate(['study'],AT),allow_nan=False)


def test_calibration_uses_matched_portfolios_and_respects_corrections():
    model=calibrated();k=AdaptiveKernel(model);result=k.forecast(['study'],AT)
    assert result['status']=='supported_prediction'
    ids=result['predictions']['practice']['calibration']['score_ids']
    wanted={fingerprint({'episode_id':e['id'],'measure_id':'practice'}) for e in model['episodes'] if e['action_ids']==['study']}
    assert set(ids)<=wanted
    e=model['episodes'][25]; old=next(o for o in model['observations'] if o['id']==e['after']['practice'])
    model['observations'].append(old|{'id':'corrected-result','value':old['value']+1,'recorded_at':AT,'supersedes':old['id']})
    ids=AdaptiveKernel(model).forecast(['study'],AT)['predictions']['practice']['calibration']['score_ids']
    assert fingerprint({'episode_id':e['id'],'measure_id':'practice'}) not in ids


def test_unit_conversion_preserves_normalized_calibration_and_point_model():
    model=calibrated();original=AdaptiveKernel(model).forecast(['study'],AT)['predictions']['practice']
    for o in model['observations']:
        if o['measure_id']=='practice':o['value']*=10
    next(m for m in model['measures'] if m['id']=='practice')['unit']='十分之一条'
    d=model['learning']['targets'][0];d['scale']*=10;d['unit']='十分之一条'
    changed=AdaptiveKernel(model).forecast(['study'],AT)['predictions']['practice']
    for key in ['mean','scale','lower','upper']:
        assert changed[key]==pytest.approx(original[key]*10)
    assert changed['calibration']['radius']==pytest.approx(original['calibration']['radius'])


def test_disabled_calibration_matches_frozen_03_predictions():
    old=json.loads((Path(__file__).parents[1]/'artifacts/adaptive-replay/v2/adaptive-synthetic.json').read_text())['runs'][0]
    new=AdaptiveKernel(fixture()).replay()
    for a,b in zip(old['rows'],new['rows']):
        for key in ['predicted_delta','absolute_error','negative_log_predictive_density','predictive_width']:
            assert a[key]==pytest.approx(b[key],abs=1e-12)
    assert new['coverage_guarantee'] is False


def test_shadow_intervals_cannot_change_recommendation_ranking():
    model=calibrated(); baseline=deepcopy(model);baseline['learning'].pop('calibration')
    candidate=AdaptiveKernel(model); original=AdaptiveKernel(baseline)
    left=candidate.propose(AT,horizon_days=1); right=original.propose(AT,horizon_days=1)
    assert left['preferred_id']==right['preferred_id']
    for a,b in zip(left['scenarios'],right['scenarios']):
        assert a['goal_gaps']==b['goal_gaps']
        for mid,p in a['forecast']['predictions'].items():
            q=b['forecast']['predictions'][mid]
            assert [p[k] for k in ('mean','lower','upper')]==[q[k] for k in ('mean','lower','upper')]
            assert p['calibration']['deployment']=='shadow_only'
    assert candidate.replay()['used_for_recommendations'] is False
