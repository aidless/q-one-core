from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
from qone_core.life import LifeKernel, ScenarioKernel, ModelError
from qone_core.life.adaptive import AdaptiveKernel, BayesianTransition
from qone_core.life.state import check_condition, resource_key

spec=importlib.util.spec_from_file_location('fixture',Path(__file__).parents[1]/'examples/generate_adaptive_fixture.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
AT='2026-10-25T00:00:00+00:00'


@pytest.fixture
def model():
    return module.fixture(count=40)


def test_measurement_scales_and_unknown(model):
    k=LifeKernel(model); state=k.snapshot(AT)
    assert state['life_score'] is None
    assert state['measures']['support']['value']=='需预约'
    assert check_condition({'measure_id':'support','op':'gte','target':'可及时获得'},state['measures'],k.index['measures'])=='not_met'
    assert state['measures']['meaning']['value'].startswith('想把时间')
    model['actions'][0]['effects']=[{'measure_id':'support','hypothesis_id':'h','mode':'delta','unit':'类别','amount':1}]
    model['hypotheses']=[{'id':'h','statement':'invalid ordinal arithmetic','origin':'user','source':'test','status':'unverified'}]
    with pytest.raises(ModelError): LifeKernel(model)


def test_between_order_and_straddling(model):
    k=LifeKernel(model); states=k.snapshot(AT)['measures']
    c={'measure_id':'practice','op':'between','target':{'upper':55,'lower':45}}
    assert check_condition(c,states,k.index['measures'])=='met'
    states['practice']['value']={'lower':50,'upper':60}
    assert check_condition(c,states,k.index['measures'])=='unknown'


def test_bitemporal_correction_conflict_and_staleness(model):
    obs=next(o for o in model['observations'] if o['id']=='current-practice')
    corrected=obs|{'id':'correction','value':100,'recorded_at':'2026-10-26T00:00:00Z','supersedes':obs['id']}
    model['observations'].append(corrected); k=LifeKernel(model)
    assert k.snapshot(AT)['measures']['practice']['value']['lower']==50
    assert k.snapshot(AT,known_at=corrected['recorded_at'])['measures']['practice']['value']['lower']==100
    assert k.snapshot('2026-11-05T00:00:00Z')['measures']['practice']['status']=='stale'
    model['observations'].append(obs|{'id':'conflict','value':3})
    assert LifeKernel(model).snapshot(AT)['measures']['practice']['status']=='conflict'


def test_reject_cycles_units_future_facts_and_malformed(model):
    for mutate in [lambda m:m['dimensions'][0].update(parent_id='physical'),
                   lambda m:m['actions'][0]['costs'][0].update(unit='小时'),
                   lambda m:m['observations'][0].update(recorded_at='2025-01-01T00:00:00Z'),
                   lambda m:m['observations'][0].pop('observed_at'),
                   lambda m:m['values'][0].update(declared_by='model')]:
        m=deepcopy(model); mutate(m)
        with pytest.raises(ModelError): LifeKernel(m)


def test_resources_never_truncate_an_action(model):
    k=ScenarioKernel(model)
    row=k.simulate(['build'],AT,horizon_days=0)
    assert row['status']=='blocked'
    assert row['costs']['time']['upper']==90
    commitment={'resource_key':resource_key(model['resources'][0]),'amount':30}
    row=k.simulate(['study'],AT,horizon_days=0,commitments=[commitment])
    assert any(i['code']=='resource_exceeded' for i in row['issues'])
    with pytest.raises(ModelError): k.snapshot(AT,commitments=[commitment|{'amount':-1}])


def test_delayed_guardrail_and_projection_review(model):
    model['hypotheses']=[{'id':'h','statement':'合成影响假设','source':'test','origin':'user','status':'unverified'}]
    model['actions'][0]['effects']=[{'measure_id':'energy','hypothesis_id':'h','mode':'delta','unit':'分钟','amount':-20,'lag_days':0}]
    model['actions'][1]['effects']=[{'measure_id':'energy','hypothesis_id':'h','mode':'delta','unit':'分钟','amount':30,'lag_days':1}]
    model['resources'][0]['budget']=200
    model['guardrails']=[{'id':'g','label':'保留精力','condition':{'measure_id':'energy','op':'gte','target':50}}]
    k=ScenarioKernel(model); row=k.simulate(['study','build'],AT,horizon_days=1)
    assert row['status']=='blocked'
    assert any(i.get('day')==0 and i['code']=='guardrail_violated' for i in row['issues'])
    model['observations'].append({'id':'later','measure_id':'energy','value':70,'observed_at':'2026-10-26T00:00:00Z','recorded_at':'2026-10-26T00:00:00Z','source_kind':'user_report','source':'test'})
    review=ScenarioKernel(model).review_projection(row,reviewed_at='2026-10-26T00:00:00Z')
    assert review['hypotheses_automatically_verified'] is False
    assert next(r for r in review['rows'] if r['measure_id']=='energy')['aligned']


def test_bayesian_updates_equal_batch_posterior():
    np=pytest.importorskip('numpy')
    rng=np.random.default_rng(5); X=rng.normal(size=(80,5)); y=X@np.array([1,2,0,-1,0.5])+rng.normal(size=80)*0.2
    r=BayesianTransition(5)
    for x,v in zip(X,y): r.update(x,float(v))
    precision=np.eye(5)+X.T@X; mean=np.linalg.solve(precision,X.T@y)
    assert np.allclose(r.mean,mean,atol=1e-10)
    assert np.allclose(r.cov,np.linalg.inv(precision),atol=1e-10)
    assert r.beta==pytest.approx(1+0.5*(y@y-mean@(X.T@y)))
    p=r.predict(X[0]); assert p['lower']<p['mean']<p['upper'] and p['coverage_guarantee'] is False


def test_learning_forecast_and_abstention(model):
    k=AdaptiveKernel(model); p=k.forecast(['study'],AT)
    assert p['status']=='supported_prediction'
    assert p['training_n']==40
    assert 9<p['predictions']['practice']['mean']<14
    model['observations'][-5]['value']=1000  # energy at query time, outside the training range
    assert any(i['code']=='context_outside_observed_range' for i in AdaptiveKernel(model).forecast(['study'],AT)['issues'])
    assert AdaptiveKernel(module.fixture(count=4)).forecast(['study'],AT)['status']=='abstain'


def test_learning_gates_unseen_portfolio_future_and_units(model):
    model['episodes']=[e for e in model['episodes'] if e['action_ids']!=['study','build']]
    assert any(i['code']=='portfolio_unsupported' for i in AdaptiveKernel(model).forecast(['study','build'],AT)['issues'])
    m=deepcopy(model); m['episodes'][0]['before']['energy']='current-energy'
    with pytest.raises(ModelError): AdaptiveKernel(m)
    m=deepcopy(model); m['learning']['targets'][0]['unit']='分'
    with pytest.raises(ModelError): AdaptiveKernel(m)
    m=deepcopy(model); m['episodes'][0]['ended_at']='2026-01-05T00:00:00Z'
    with pytest.raises(ModelError): AdaptiveKernel(m)
    m=deepcopy(model); m['observations'][0]['value']={'lower':10,'upper':20}
    with pytest.raises(ModelError): AdaptiveKernel(m)


def test_replay_uses_only_available_results_and_ignores_delayed_labels(model):
    # Outcome of e0 is deliberately unavailable until after e1 starts.
    model['episodes'][0]['recorded_at']='2026-01-04T00:00:00Z'
    k=AdaptiveKernel(model); replay=k.replay(); rows=replay['rows']
    assert rows[0]['training_n']==0
    assert next(r for r in rows if r['episode_id']=='e1')['training_n']==0
    assert replay['policy_value_estimated'] is False
    for result in replay['summary'].values():
        assert result['mae'] < result['no_change_mae']


def test_adaptive_ranking_changes_with_user_preference(model):
    model=module.fixture(count=96)
    model['resources'][0]['budget']=100
    k=AdaptiveKernel(model); result=k.propose(AT,max_actions=1,horizon_days=1)
    selected=next(r for r in result['scenarios'] if r['id']==result['preferred_id'])
    assert selected['action_ids']==['study']
    model['goal_order']=['deliver','learn']; result=AdaptiveKernel(model).propose(AT,max_actions=1,horizon_days=1)
    selected=next(r for r in result['scenarios'] if r['id']==result['preferred_id'])
    assert selected['action_ids']==['build']


def test_learning_never_overrides_resources_or_continuous_safety(model):
    k=AdaptiveKernel(model); row=k.simulate(['build'],AT)
    assert row['status']=='blocked'
    model['guardrails']=[{'id':'g','label':'不可假装连续约束已验证','condition':{'measure_id':'practice','op':'gte','target':1}}]
    row=AdaptiveKernel(model).simulate(['study'],AT)
    assert any(i['code']=='intermediate_guardrail_unmodeled' for i in row['issues'])
    assert row['status']!='conditional'


def test_no_declared_preference_no_invented_winner(model):
    model['goal_order']=[]
    result=AdaptiveKernel(model).propose(AT,max_actions=1,horizon_days=1)
    assert result['preferred_id'] is None
    assert result['choice_status']=='needs_preference'


def test_hierarchical_goals_use_child_conditions(model):
    model['goals'].append({'id':'parent','title':'能力与产出','dimension_id':'learning','success_criterion':'完成两个子目标','conditions':[]})
    for g in model['goals'][:2]: g['parent_id']='parent'
    model['goal_order']=['parent','learn','deliver']
    result=AdaptiveKernel(model).propose(AT,max_actions=1,horizon_days=1)
    for row in result['scenarios']:
        assert all(v is not None for v in row['goal_gaps']['parent'].values())


def test_overlapping_predictions_abstain_instead_of_forcing_preference(model):
    model['resources'][0]['budget']=100; model['goal_order']=['deliver','learn']
    result=AdaptiveKernel(model).propose(AT,max_actions=1,horizon_days=1)
    assert result['choice_status']=='needs_preference' and result['preferred_id'] is None


def test_action_exposure_revision_cannot_reuse_old_outcomes(model):
    model['actions'][0]['minutes']=5
    with pytest.raises(ModelError,match='行动定义'): AdaptiveKernel(model)
