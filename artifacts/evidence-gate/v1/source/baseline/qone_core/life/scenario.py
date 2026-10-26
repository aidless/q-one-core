"""Finite what-if analysis under declared assumptions, not a learned world model."""
from copy import deepcopy
from datetime import timedelta
from itertools import combinations
from .model import ModelError, fingerprint, instant, interval, measured_value
from .state import LifeKernel, check_condition, goal_states


def goal_gaps(kernel, states, goal_id):
    result = {}
    g = kernel.index['goals'][goal_id]
    for i, c in enumerate(g.get('conditions', [])):
        m, row = kernel.index['measures'][c['measure_id']], states[c['measure_id']]
        key = goal_id + ':' + str(i)
        if row['status'] != 'known' or m['scale'] in {'qualitative','unclassified'}:
            result[key] = None
            continue
        if m['scale'] == 'nominal':
            gap = 0 if row['value'] == c['target'] else 1
            result[key] = interval(gap)
            continue
        if m['scale'] == 'ordinal':
            # Only satisfaction is comparable; rank distances have no metric meaning.
            status = check_condition(c,states,kernel.index['measures'])
            result[key] = interval(0 if status=='met' else 1) if status!='unknown' else None
            continue
        lo, hi = row['value']['lower'], row['value']['upper']
        target = c['target']
        if c['op'] == 'gte': lower, upper = max(0, target - hi), max(0, target - lo)
        elif c['op'] == 'lte': lower, upper = max(0, lo - target), max(0, hi - target)
        else:
            t = interval(target) if c['op'] == 'between' else interval(target)
            a, b = t['lower'], t['upper']
            lower = max(0, a-hi, lo-b)
            upper = max(0, a-lo, hi-b)
        result[key] = {'lower': lower, 'upper': upper}
    for child in kernel.model['goals']:
        if child.get('parent_id')==goal_id and child.get('active',True):
            result.update({goal_id+':'+key:value for key,value in goal_gaps(kernel,states,child['id']).items()})
    if not result:
        result[goal_id + ':qualitative'] = None
    return result


def dominates(left, right):
    """Conservative interval dominance. Unknown components prevent a claim."""
    if set(left) != set(right) or not left:
        return False
    if any(left[k] is None or right[k] is None for k in left):
        return False
    return all(left[k]['upper'] <= right[k]['lower'] for k in left) and any(
        left[k]['upper'] < right[k]['lower'] for k in left)


class ScenarioKernel(LifeKernel):
    def simulate(self, action_ids, as_of, *, horizon_days=7, commitments=(), completed_action_ids=()):
        if type(horizon_days) is not int or not 0 <= horizon_days <= 3660:
            raise ModelError('情景范围应为0到3660天的整数')
        if not isinstance(action_ids, list) or len(set(action_ids)) != len(action_ids) or any(a not in self.index['actions'] for a in action_ids):
            raise ModelError('情景含重复或不存在的行动')
        state = self.snapshot(as_of, commitments=commitments)
        chosen = set(action_ids)
        ordered=[]
        def arrange(aid):
            if aid in ordered: return
            for dep in self.index['actions'][aid].get('depends_on',[]):
                if dep in chosen: arrange(dep)
            ordered.append(aid)
        for aid in sorted(chosen): arrange(aid)
        actions = [self.index['actions'][a] for a in ordered]
        issues, costs, assumptions = [], {}, []
        for a in actions:
            missing = set(a.get('depends_on', [])) - chosen - set(completed_action_ids)
            if missing: issues.append({'code':'prerequisite_missing', 'action_id':a['id'], 'missing':sorted(missing)})
            for c in a.get('costs', []):
                amount = interval(c['amount']); key = c['resource_id']
                total = costs.setdefault(key, {'lower':0,'upper':0})
                total['lower'] += amount['lower']; total['upper'] += amount['upper']
            for e in a.get('effects', []):
                h = self.index['hypotheses'][e['hypothesis_id']]
                assumptions.append(deepcopy(h))
                if h['status'] == 'refuted': issues.append({'code':'refuted_hypothesis', 'hypothesis_id':h['id'], 'action_id':a['id']})
        for key, amount in costs.items():
            r = state['resources'][key]
            if r['status'] != 'known': issues.append({'code':'resource_unknown','resource_id':key})
            elif amount['upper'] > r['available']: issues.append({'code':'resource_exceeded','resource_id':key,'available':r['available'],'required_upper':amount['upper']})
        moments = sorted({0,horizon_days} | {e.get('lag_days',0) for a in actions for e in a.get('effects',[]) if e.get('lag_days',0)<=horizon_days})
        trajectory = []
        for day in moments:
            projected = deepcopy(state['measures'])
            for key, row in projected.items():
                m = self.index['measures'][key]
                if day and row['status'] == 'known':
                    if m.get('persistence','unknown') == 'hold':
                        assumptions.append({'id':'hold:'+key,'statement':'情景假设无其他变化，保留基线状态','origin':'user','status':'unverified','source':'measurement persistence declaration'})
                        row['basis'] = 'scenario_hold_assumption'
                    else:
                        row['status'], row['value'] = 'unmodeled_future', None
            by_measure = {}
            for a in actions:
                for e in a.get('effects', []):
                    if e.get('lag_days',0)<=day and self.index['hypotheses'][e['hypothesis_id']]['status']!='refuted':
                        by_measure.setdefault(e['measure_id'], []).append(e)
            for key, effects in by_measure.items():
                m, row = self.index['measures'][key], projected[key]
                sets = [e for e in effects if e['mode']=='set']
                if len({fingerprint(e['value']) for e in sets}) > 1:
                    row['status'],row['value'] = 'conflicting_assumptions',None
                    issues.append({'code':'conflicting_effects','measure_id':key,'day':day})
                    continue
                if sets:
                    row['value'],row['status'] = measured_value(sets[0]['value'],m),'known'
                if row['status'] == 'known':
                    deltas = [interval(e['amount']) for e in effects if e['mode']=='delta']
                    if deltas:
                        row['value'] = {'lower':row['value']['lower']+sum(v['lower'] for v in deltas),
                                        'upper':row['value']['upper']+sum(v['upper'] for v in deltas)}
                    row['basis'] = 'scenario_effect_assumption'
                    if m['scale'] in {'ratio','interval'}:
                        bounds = interval(m['bounds']) if m.get('bounds') else None
                        v = row['value']
                        if (m['scale']=='ratio' and v['lower']<0) or (bounds and (v['lower']<bounds['lower'] or v['upper']>bounds['upper'])):
                            issues.append({'code':'projection_outside_measure_domain','measure_id':key,'day':day})
            guardrails = []
            for guard in self.model['guardrails']:
                status = check_condition(guard['condition'], projected, self.index['measures'])
                guardrails.append({'id':guard['id'],'label':guard['label'],'status':status})
                if status!='met': issues.append({'code':'guardrail_violated' if status=='not_met' else 'guardrail_unknown','guardrail_id':guard['id'],'day':day})
            trajectory.append({'day':day,'states':projected,'guardrails':guardrails,
                               'goals':goal_states(self.model,projected,self.index['measures'])})
        blocked = {'prerequisite_missing','resource_exceeded','guardrail_violated','projection_outside_measure_domain'}
        status = 'blocked' if any(i['code'] in blocked for i in issues) else 'needs_information' if issues else 'conditional'
        return {'id':'scenario-'+fingerprint(sorted(action_ids))[:16], 'action_ids':ordered, 'status':status,
                'as_of':state['as_of'], 'projected_for':(instant(as_of)+timedelta(days=horizon_days)).isoformat(),
                'horizon_days':horizon_days,'costs':costs,'resources':state['resources'],'issues':issues,
                'assumptions':list({h['id']:h for h in assumptions}.values()),'trajectory':trajectory,
                'model_sha256':self.model_sha256,'definition_sha256':self.definition_sha256,'interpretation':'给定假设下的情景推演；区间不是置信区间，未建立因果关系'}

    def compare(self, portfolios, as_of, **kwargs):
        if not isinstance(portfolios,list) or not 1 <= len(portfolios)<=512:
            raise ModelError('单轮最多比较512个明确方案')
        rows = [self.simulate(ids,as_of,**kwargs) for ids in portfolios]
        if len({r['id'] for r in rows})!=len(rows):
            raise ModelError('比较方案不能重复')
        goal_ids = [g['id'] for g in self.model['goals'] if g.get('active',True)]
        objectives, goal_objectives = {}, {}
        for row in rows:
            by_goal = {g:goal_gaps(self,row['trajectory'][-1]['states'],g) for g in goal_ids}
            goal_objectives[row['id']] = by_goal
            obj = {k:v for values in by_goal.values() for k,v in values.items()}
            for key in self.index['resources']:
                obj['cost:'+key] = row['costs'].get(key,interval(0))
            objectives[row['id']] = obj
            row['goal_gaps'] = by_goal
        feasible = [r for r in rows if r['status']=='conditional']
        frontier = [r for r in feasible if not any(dominates(objectives[o['id']],objectives[r['id']]) for o in feasible if o is not r)]
        remaining = list(frontier)
        order = self.model['goal_order']
        reason = 'needs_preference'
        if not feasible:
            reason = 'no_feasible_plan'
        elif not goal_ids:
            reason = 'needs_goal_definition'
        elif set(order)==set(goal_ids):
            for g in order:
                remaining = [r for r in remaining if not any(dominates(goal_objectives[o['id']][g],goal_objectives[r['id']][g]) for o in remaining if o is not r)]
                signatures = {fingerprint(goal_objectives[r['id']][g]) for r in remaining}
                if len(signatures)>1:
                    break  # Do not let a lower-priority goal conceal an unresolved higher-priority tradeoff.
            if len(remaining)==1:
                reason = 'conditional_preference'
            elif remaining and all(objectives[r['id']]==objectives[remaining[0]['id']] for r in remaining):
                reason = 'equivalent_plans'
        return {'scenarios':rows,'frontier_ids':[r['id'] for r in frontier],
                'preferred_id':remaining[0]['id'] if reason=='conditional_preference' else None,
                'choice_status':reason, 'goal_order':order, 'life_score':None,
                'policy':'conservative_pareto_then_user_goal_order_v1'}

    def propose(self, as_of, *, max_actions=3, completed_action_ids=(), excluded_action_ids=(), **kwargs):
        if type(max_actions) is not int or not 1 <= max_actions <= 3:
            raise ModelError('单轮支持1到3个行动')
        actions = [a['id'] for a in self.model['actions'] if a['id'] not in set(excluded_action_ids)]
        if len(actions)>12:
            raise ModelError('精确方案比较最多支持12个当前行动，请明确当前决策范围')
        portfolios = [[]]+[list(ids) for n in range(1,min(max_actions,len(actions))+1) for ids in combinations(actions,n)]
        return self.compare(portfolios,as_of,completed_action_ids=completed_action_ids,**kwargs)

    def review_projection(self, receipt, *, reviewed_at):
        if receipt.get('definition_sha256')!=self.definition_sha256:
            raise ModelError('复盘可增加观察，但不能改变预测时的模型定义')
        if instant(reviewed_at)<instant(receipt['projected_for']):
            raise ModelError('尚未到情景观察时点')
        observed = self.snapshot(reviewed_at)
        rows = []
        for key, projected in receipt['trajectory'][-1]['states'].items():
            actual = observed['measures'][key]
            aligned = actual['status']=='known' and instant(actual['observed_at'])>=instant(receipt['projected_for'])
            inside = None
            if aligned and projected['status']=='known' and self.index['measures'][key]['scale'] in {'ratio','interval'}:
                a,p = actual['value'],projected['value']
                inside = p['lower']<=a['lower']<=a['upper']<=p['upper']
            rows.append({'measure_id':key,'aligned':aligned,'observation_ids':actual['observation_ids'],
                         'interval_contains_observation':inside})
        return {'rows':rows,'hypotheses_automatically_verified':False,
                'interpretation':'仅比较后续观察与假设区间；不证明行动导致变化，也不报告覆盖率保证'}
