"""Regression gates for evidence ambiguity; all data is synthetic."""
from copy import deepcopy
from datetime import timedelta
import gzip
import importlib.util
import json
from pathlib import Path

import pytest
from qone_core.life import AdaptiveKernel
from qone_core.life.model import fingerprint, instant

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('evidence_fixture',ROOT/'examples/generate_adaptive_fixture.py')
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)
AT='2026-10-26T00:00:00Z'
PAST='2026-10-25T00:00:00Z'

def frozen(name):
    return json.loads(gzip.decompress((ROOT/'artifacts/evidence-gate/v1/inputs'/(name+'.json.gz')).read_bytes()))

@pytest.mark.parametrize('name,code',[
    ('late_outcome_conflict','observation_conflict'),
    ('late_before_conflict','observation_conflict'),
    ('known_before_conflict','before_state_conflict'),
    ('older_before_reference','before_reference_not_current'),
    ('superseded_outcome','observation_superseded'),
])
def test_invalid_evidence_is_excluded_from_fit_and_replay_with_denominators(name,code):
    kernel=AdaptiveKernel(frozen(name)); fit=kernel.fitted(AT); replay=kernel.replay(as_of=AT)
    assert fit['evidence_summary']=={'available_n':40,'trainable_n':39,'excluded_n':1}
    assert [e['episode_id'] for e in fit['excluded_episodes']]==['e25']
    assert code in {i['code'] for i in fit['excluded_episodes'][0]['issues']}
    assert 'e25' not in {e['id'] for e in fit['episodes']}
    assert 'e25' not in {r['episode_id'] for r in replay['rows']}
    assert len(replay['rows'])==78
    assert replay['evidence_summary']==fit['evidence_summary']
    assert kernel.forecast(['study'],AT)['training_evidence']['excluded_episodes']==fit['excluded_episodes']
    json.dumps(replay,allow_nan=False)

@pytest.mark.parametrize('name',['late_outcome_conflict','late_before_conflict','superseded_outcome','future_conflict'])
def test_late_evidence_does_not_change_past_issued_predictions(name):
    clean=AdaptiveKernel(frozen('clean.seed17')); changed=AdaptiveKernel(frozen(name))
    for at in [PAST,'2026-02-22T00:00:00Z']:
        a,b=clean.forecast(['study'],at),changed.forecast(['study'],at)
        assert a['predictions']==b['predictions']
        assert a['training_evidence']==b['training_evidence']
        assert a['training_episode_ids']==b['training_episode_ids']
    if name=='future_conflict':
        assert 'e25' in {e['id'] for e in changed.fitted(AT)['episodes']}

@pytest.mark.parametrize('name',['equal_duplicate','unrelated_conflict','future_conflict'])
def test_duplicates_unrelated_and_not_yet_known_conflicts_do_not_drop_evidence(name):
    k=AdaptiveKernel(frozen(name)); base=AdaptiveKernel(frozen('clean.seed17'))
    assert k.fitted(AT)['evidence_summary']=={'available_n':40,'trainable_n':40,'excluded_n':0}
    assert k.forecast(['study'],AT)['predictions']==base.forecast(['study'],AT)['predictions']


def test_explicit_correction_can_resolve_competing_report_without_replacing_reference():
    model=frozen('late_outcome_conflict'); conflicting=model['observations'][-1]
    original=next(o for o in model['observations'] if o['id']==model['episodes'][25]['after']['practice'])
    model['observations'].append(conflicting|{'id':'resolved-report','value':original['value'],
        'recorded_at':'2026-10-27T00:00:00Z','supersedes':conflicting['id']})
    k=AdaptiveKernel(model)
    assert len(k.fitted(AT)['episodes'])==39
    assert len(k.fitted('2026-10-27T00:00:00Z')['episodes'])==40
    assert len(k.fitted(PAST)['episodes'])==40


def test_replay_uses_latest_observation_knowledge_and_explicit_cutoff():
    k=AdaptiveKernel(frozen('future_conflict'))
    assert k.replay()['evidence_summary']['excluded_n']==1
    assert k.replay(as_of=AT)['evidence_summary']['excluded_n']==0
    old=k.replay(as_of='2026-01-01T00:00:00Z')
    assert old['rows']==[]
    assert old['evidence_summary']=={'available_n':0,'trainable_n':0,'excluded_n':0}
    assert old['excluded_episodes']==[]


def test_qualification_below_raw_support_threshold_abstains():
    model=fixture_module.fixture(count=20); old=model['observations'][3]
    model['observations'].append(old|{'id':'disputed-result','value':old['value']+2,'recorded_at':AT})
    result=AdaptiveKernel(model).forecast(['study'],AT)
    assert result['training_n']==19 and result['status']=='abstain'
    assert {'code':'insufficient_history','n':19} in result['issues']


def test_ambiguous_episode_is_not_shadow_calibration_evidence():
    model=frozen('late_outcome_conflict')
    model['learning']['calibration']={'method':'prequential_aci','step_size':0.01,'window':64,'min_samples':10}
    kernel=AdaptiveKernel(model)
    token=fingerprint({'episode_id':'e25','measure_id':'practice'})
    history=kernel.calibration_history(AT)
    assert token not in history['issued']
    assert token not in {s for cal in history['calibrators'].values() for s in cal.interval().get('score_ids',[])}


def test_newer_measurements_after_action_start_do_not_rewrite_historical_features():
    model=frozen('clean.seed17'); e=model['episodes'][25]
    original=next(o for o in model['observations'] if o['id']==e['before']['energy'])
    later=instant(e['started_at'])+timedelta(hours=1)
    model['observations'].append(original|{'id':'later-within-action','value':original['value']+2,
        'observed_at':later.isoformat(),'recorded_at':later.isoformat()})
    assert len(AdaptiveKernel(model).fitted(AT)['episodes'])==40
    # The immutable input is copied during validation, so caller edits cannot
    # turn cached qualification into a different observation silently.
    k=AdaptiveKernel(model); model['observations'][-1]['value']=999
    assert k.forecast(['study'],AT)['predictions']==AdaptiveKernel(deepcopy(k.model)).forecast(['study'],AT)['predictions']


def test_equivalent_numeric_json_representations_do_not_drop_evidence():
    model=frozen('clean.seed17'); episode=model['episodes'][25]
    old=next(o for o in model['observations'] if o['id']==episode['after']['practice'])
    old['value']=int(old['value'])
    model['observations'].append(old|{'id':'float-duplicate','value':float(old['value']),
                                      'recorded_at':AT,'source':'SYNTHETIC numeric duplicate'})
    fit=AdaptiveKernel(model).fitted(AT)
    assert fit['evidence_summary']=={'available_n':40,'trainable_n':40,'excluded_n':0}
    assert 'e25' in {e['id'] for e in fit['episodes']}
