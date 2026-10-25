"""As-of state and three-valued goal evaluation; no global life score."""
from datetime import timedelta
from .model import COLLECTIONS, ModelError, fingerprint, instant, interval, measured_value, number, validate_model


def resource_key(resource):
    return fingerprint({k: resource[k] for k in ('id', 'unit', 'valid_from', 'valid_until')})


def check_condition(c, states, measures):
    row = states[c['measure_id']]
    if row['status'] != 'known' or measures[c['measure_id']]['scale'] == 'unclassified':
        return 'unknown'
    m, value, target, op = measures[c['measure_id']], row['value'], c['target'], c['op']
    if m['scale'] == 'ordinal':
        lo = hi = m['categories'].index(value)
        target = m['categories'].index(target)
    elif m['scale'] in {'ratio', 'interval'}:
        lo, hi = value['lower'], value['upper']
    else:
        return 'met' if value == target else 'not_met'
    if op == 'gte':
        return 'met' if lo >= target else 'not_met' if hi < target else 'unknown'
    if op == 'lte':
        return 'met' if hi <= target else 'not_met' if lo > target else 'unknown'
    if op == 'eq':
        return 'met' if lo == hi == target else 'not_met' if target < lo or target > hi else 'unknown'
    bounds = interval(target)
    lower, upper = bounds['lower'], bounds['upper']
    return 'met' if lo >= lower and hi <= upper else 'not_met' if hi < lower or lo > upper else 'unknown'


def goal_states(model, states, measures):
    goals = {g['id']: g for g in model['goals']}
    result = {}
    def evaluate(key):
        if key in result:
            return result[key]['status']
        g = goals[key]
        children = [x['id'] for x in goals.values() if x.get('parent_id') == key and x.get('active',True)]
        local = [check_condition(c, states, measures) for c in g.get('conditions', [])]
        parts = local + [evaluate(child) for child in children]
        status = 'not_met' if 'not_met' in parts else 'met' if parts and all(p == 'met' for p in parts) else 'unknown'
        if not g.get('active', True):
            status = 'inactive'
        result[key] = {'id': key, 'title': g['title'], 'status': status, 'condition_statuses': local,
                       'children': children, 'reason': 'qualitative_review_required' if not parts else None}
        return status
    for key in goals:
        evaluate(key)
    return result


class LifeKernel:
    def __init__(self, model):
        self.model = validate_model(model)
        self.index = {name: {r['id']: r for r in self.model[name]} for name in COLLECTIONS}
        self.model_sha256 = fingerprint(self.model)
        self.definition_sha256 = fingerprint({k:v for k,v in self.model.items() if k not in {'observations', 'episodes'}})

    def snapshot(self, as_of, *, known_at=None, commitments=()):
        at, knowledge = instant(as_of), instant(known_at or as_of)
        for c in commitments:
            if not isinstance(c, dict) or not isinstance(c.get('resource_key'), str) or number(c.get('amount')) < 0:
                raise ModelError('资源承诺需要有效账户键和非负数值')
        visible = [o for o in self.model['observations'] if instant(o['recorded_at']) <= knowledge
                   and instant(o['observed_at']) <= at]
        superseded = {o['supersedes'] for o in visible if o.get('supersedes')}
        rows = [o for o in visible if o['id'] not in superseded]
        states = {}
        for m in self.model['measures']:
            options = [o for o in rows if o['measure_id'] == m['id']]
            base = {'measure_id': m['id'], 'name': m['name'], 'dimension_id': m['dimension_id'],
                    'unit': m['unit'], 'scale': m['scale'], 'value': None, 'observation_ids': []}
            if not options:
                states[m['id']] = base | {'status': 'missing'}
                continue
            latest_time = max(instant(o['observed_at']) for o in options)
            latest = [o for o in options if instant(o['observed_at']) == latest_time]
            o = max(latest, key=lambda o: (instant(o['recorded_at']), o['id']))
            value = measured_value(o['value'], m)
            status = 'known'
            if len({fingerprint(measured_value(x['value'], m)) for x in latest}) > 1:
                status = 'conflict'
            elif at - latest_time > timedelta(days=m['freshness_days']):
                status = 'stale'
            states[m['id']] = base | {'status': status, 'value': value if status == 'known' else None,
                'last_value': value, 'observed_at': latest_time.isoformat(), 'source_kind': o['source_kind'],
                'source': o['source'], 'observation_ids': [x['id'] for x in latest], 'basis': 'reported_observation'}
        resources = {}
        for r in self.model['resources']:
            key = resource_key(r)
            spent = sum(c['amount'] for c in commitments if c['resource_key'] == key)
            available = r.get('budget') - spent if r.get('budget') is not None else None
            status = 'known' if instant(r['valid_from']) <= at < instant(r['valid_until']) and available is not None else 'unknown'
            resources[r['id']] = {'id': r['id'], 'name': r['name'], 'unit': r['unit'], 'resource_key': key,
                'budget': r.get('budget'), 'committed': spent, 'available': available if status == 'known' else None,
                'status': status}
        return {'as_of': at.isoformat(), 'known_at': knowledge.isoformat(), 'model_sha256': self.model_sha256,
                'measures': states, 'resources': resources, 'goals': goal_states(self.model, states, self.index['measures']),
                'life_score': None, 'interpretation': '维度是不同测量的集合，不合成为人的总分'}

    def graph(self):
        nodes, edges = [], []
        for kind in ('dimensions','values','measures','resources','goals','hypotheses','actions'):
            for r in self.model[kind]:
                node = kind + ':' + r['id']
                nodes.append({'id': node, 'kind': kind, 'label': r.get('name', r.get('title', r.get('statement')))})
                def link(target_kind, target, relation):
                    if target:
                        edges.append({'from': node, 'to': target_kind + ':' + target, 'relation': relation})
                if kind in {'goals', 'measures'}:
                    link('dimensions', r['dimension_id'], 'belongs_to')
                if kind in {'goals','dimensions'}:
                    link(kind, r.get('parent_id'), 'part_of')
                if kind == 'goals':
                    for v in r.get('value_ids', []): link('values', v, 'serves_declared_value')
                    for c in r.get('conditions', []): link('measures', c['measure_id'], 'checked_by')
                if kind == 'actions':
                    for g in r.get('goal_ids', []): link('goals', g, 'intends_to_advance')
                    for c in r.get('costs', []): link('resources', c['resource_id'], 'consumes')
                    for e in r.get('effects', []):
                        link('measures', e['measure_id'], 'hypothesized_effect')
                        link('hypotheses', e['hypothesis_id'], 'effect_assumption')
                    for a in r.get('depends_on', []): link('actions', a, 'requires')
        return {'nodes': nodes, 'edges': edges, 'causality_established': False}
