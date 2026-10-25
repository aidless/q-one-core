"""Auditable small-data transition learning, not a pretrained life/world model.

Normal-inverse-gamma regression with context/action interactions; exact Bayesian
updates and Student-t marginal predictions. Personal observations are selected
by event AND knowledge time. No online action exploration is performed.
"""
from copy import deepcopy
from datetime import timedelta
from itertools import combinations
import math

from .model import ModelError, fingerprint, instant, number
from .scenario import ScenarioKernel
from .state import check_condition, goal_states


def learning_dependencies():
    try:
        import numpy as np
        from scipy.stats import t
    except ImportError as exc:
        raise ModelError('自适应预测需要安装 q-one-core[adaptive]') from exc
    return np, t


class BayesianTransition:
    """Online conjugate regression; y is a normalized fixed-horizon delta."""
    def __init__(self, dimensions, *, precision=1.0, alpha=2.0, beta=1.0):
        self.np, self.t = learning_dependencies()
        if type(dimensions) is not int or not 1 <= dimensions <= 64:
            raise ModelError('预测特征数应为1到64')
        if any(number(v) <= 0 for v in (precision, alpha, beta)) or alpha <= 1:
            raise ModelError('先验precision/beta应为正，alpha应大于1')
        self.cov = self.np.eye(dimensions) / precision
        self.mean = self.np.zeros(dimensions)
        self.alpha, self.beta, self.n = alpha, beta, 0

    def _x(self, value):
        x = self.np.asarray(value, dtype=float)
        if x.shape != self.mean.shape or not self.np.isfinite(x).all():
            raise ModelError('预测特征形状或数值无效')
        return x

    def update(self, features, target):
        x, y = self._x(features), number(target)
        v = self.cov @ x
        denominator = 1.0 + float(x @ v)
        residual = y - float(x @ self.mean)
        self.mean += v * (residual / denominator)
        self.cov -= self.np.outer(v, v) / denominator
        self.cov = (self.cov + self.cov.T) / 2
        self.beta += 0.5 * residual ** 2 / denominator
        self.alpha += 0.5
        self.n += 1

    def predict(self, features, *, mass=0.90):
        x = self._x(features)
        if not 0 < number(mass) < 1:
            raise ModelError('预测质量mass应在0与1之间')
        leverage = max(0.0, float(x @ self.cov @ x))
        noise = self.beta / (self.alpha - 1)
        scale = math.sqrt(self.beta / self.alpha * (1 + leverage))
        loc, df = float(x @ self.mean), 2 * self.alpha
        q = float(self.t.ppf((1 + mass) / 2, df))
        return {'mean':loc, 'lower':loc-q*scale, 'upper':loc+q*scale,
                'df':df, 'scale':scale, 'mass':mass, 'n':self.n,
                'noise_variance':noise, 'parameter_variance':noise*leverage,
                'distribution':'student_t', 'coverage_guarantee':False}


class AdaptiveKernel(ScenarioKernel):
    """A fixed-horizon learned predictor plugged into the constrained planner.

    Episodes reference immutable observation IDs. An episode is trainable only
    after all its outcome evidence was recorded. Unseen action portfolios and
    contexts outside observed ranges cause abstention rather than extrapolation.
    """
    def __init__(self, model):
        super().__init__(model)
        self.config = self.model.get('learning')
        if not isinstance(self.config, dict):
            raise ModelError('缺少learning预测定义')
        c = self.config
        horizon = c.get('horizon_days')
        if type(horizon) is not int or not 1 <= horizon <= 90:
            raise ModelError('学习窗口应为1到90天')
        self.horizon = horizon
        self.features = c.get('context_features', [])
        self.targets = c.get('targets', [])
        self.action_ids = c.get('action_ids', [])
        if not isinstance(self.features, list) or not 1 <= len(self.features) <= 8:
            raise ModelError('需要1到8个有单位和缩放定义的上下文测量')
        if not isinstance(self.targets,list) or not 1 <= len(self.targets) <= 8:
            raise ModelError('需要1到8个结果测量')
        if (not isinstance(self.action_ids,list) or not 1 <= len(self.action_ids)<=6
                or any(a not in self.index['actions'] for a in self.action_ids)
                or len(set(self.action_ids))!=len(self.action_ids)):
            raise ModelError('学习行动范围应为1到6个已有且不重复的行动')
        if set(self.action_ids)!=set(self.index['actions']):
            raise ModelError('当前学习模型需覆盖完整的当前行动范围；新增行动应先收集记录')
        for definitions in (self.features,self.targets):
            seen = set()
            for d in definitions:
                if not isinstance(d,dict) or d.get('measure_id') not in self.index['measures']:
                    raise ModelError('学习定义需关联已有测量')
                m = self.index['measures'][d['measure_id']]
                if d['measure_id'] in seen or m['scale'] not in {'ratio','interval'} or d.get('unit')!=m['unit'] or number(d.get('scale'))<=0:
                    raise ModelError('学习只接受单位匹配的数量量表和正的显式缩放')
                seen.add(d['measure_id'])
                number(d.get('center',0))
        self.feature_names = ['bias']+[f"state:{f['measure_id']}" for f in self.features]
        self.feature_names += ['action:'+a for a in self.action_ids]
        self.feature_names += [f"state:{f['measure_id']}*action:{a}" for a in self.action_ids for f in self.features]
        self.feature_names += ['action:'+a+'*action:'+b for a,b in combinations(self.action_ids,2)]
        if len(self.feature_names)>64:
            raise ModelError('上下文与行动交互特征超过64个，请缩小决策范围')
        for key, default in [('min_samples',20),('min_portfolio_samples',3)]:
            v = c.get(key,default)
            if type(v) is not int or not 2 <= v <= 4096:
                raise ModelError('样本门槛应为2到4096的整数；门槛不是统计质量保证')
        if not 0 < number(c.get('predictive_mass',0.9)) < 1:
            raise ModelError('predictive_mass应在0与1之间')
        self.episodes = self.model.get('episodes',[])
        if not isinstance(self.episodes,list) or len(self.episodes)>4096:
            raise ModelError('学习记录最多4096条')
        self._cache = {}
        seen = set()
        for e in self.episodes:
            try:
                if not isinstance(e,dict) or not isinstance(e.get('id'),str) or not e['id'] or e['id'] in seen:
                    raise ModelError('学习记录ID无效或重复')
                seen.add(e['id'])
                start,end,recorded = (instant(e[k]) for k in ('started_at','ended_at','recorded_at'))
                if end-start!=timedelta(days=self.horizon) or recorded<end:
                    raise ModelError('学习记录须匹配固定结果窗口，不能事前填报结果')
                self._actions(e['action_ids'])
                expected=fingerprint([self.index['actions'][aid] for aid in sorted(e['action_ids'])])
                if e.get('action_definition_sha256')!=expected:
                    raise ModelError('历史记录必须绑定执行时的行动定义；改变投入或含义后应使用新的行动版本')
                if not isinstance(e.get('source'),str) or not e['source'].strip():
                    raise ModelError('行动执行记录需要来源说明')
                for field, definitions in [('before',self.features+self.targets),('after',self.targets)]:
                    refs = e[field]
                    for d in definitions:
                        o = self.index['observations'][refs[d['measure_id']]]
                        if o['measure_id']!=d['measure_id']:
                            raise ModelError('学习记录引用了其他测量的观察')
                        if instant(o['recorded_at'])>recorded:
                            raise ModelError('学习记录早于其引用的结果证据')
                        if field=='before':
                            if instant(o['observed_at'])>start or instant(o['recorded_at'])>start:
                                raise ModelError('事前上下文不能引用未来或事后补录的信息')
                            freshness=self.index['measures'][d['measure_id']]['freshness_days']
                            if start-instant(o['observed_at'])>timedelta(days=freshness):
                                raise ModelError('学习记录的事前观察已过期')
                        elif instant(o['observed_at'])!=end:
                            raise ModelError('结果观察时点须与固定学习窗口一致')
                        self._point(o['value'])
            except (KeyError,TypeError) as exc:
                raise ModelError('学习记录字段不完整') from exc

    @staticmethod
    def _point(value):
        if isinstance(value,dict):
            if set(value)!={'lower','upper'} or value['lower']!=value['upper']:
                raise ModelError('当前预测器只接受精确点观察，不把区间中点伪装成事实')
            value=value['lower']
        return number(value)

    def _actions(self, actions):
        if not isinstance(actions,list) or any(a not in self.action_ids for a in actions) or len(set(actions))!=len(actions):
            raise ModelError('学习行动组合无效')
        return sorted(actions)

    def vector(self, values, actions):
        actions=set(self._actions(actions))
        context=[(number(values[f['measure_id']])-f.get('center',0))/f['scale'] for f in self.features]
        flags=[int(a in actions) for a in self.action_ids]
        return [1.0]+context+flags+[v*flag for flag in flags for v in context]+[int(a in actions and b in actions) for a,b in combinations(self.action_ids,2)]

    def fitted(self, as_of):
        cutoff=instant(as_of)
        key=cutoff.isoformat()
        if key in self._cache:
            return self._cache[key]
        # A correction invalidates episodes that still reference the old value.
        superseded={o['supersedes'] for o in self.model['observations'] if o.get('supersedes') and instant(o['recorded_at'])<=cutoff}
        episodes=[]
        for e in self.episodes:
            refs=set(e['before'].values())|set(e['after'].values())
            if instant(e['recorded_at'])<=cutoff and not refs & superseded:
                episodes.append(e)
        episodes.sort(key=lambda e:(instant(e['recorded_at']),e['id']))
        models={d['measure_id']:BayesianTransition(len(self.feature_names), **{k:self.config[k] for k in ('precision','alpha','beta') if k in self.config}) for d in self.targets}
        portfolios, contexts={},[]
        for e in episodes:
            values={d['measure_id']:self._point(self.index['observations'][e['before'][d['measure_id']]]['value']) for d in self.features}
            x=self.vector(values,e['action_ids']); contexts.append(values)
            signature=tuple(sorted(e['action_ids'])); portfolios[signature]=portfolios.get(signature,0)+1
            for d in self.targets:
                before=self._point(self.index['observations'][e['before'][d['measure_id']]]['value'])
                after=self._point(self.index['observations'][e['after'][d['measure_id']]]['value'])
                models[d['measure_id']].update(x,(after-before)/d['scale'])
        result={'models':models,'episodes':episodes,'portfolios':portfolios,'contexts':contexts}
        if len(self._cache)>=16: self._cache.clear()
        self._cache[key]=result
        return result

    def forecast(self, actions, as_of):
        self._actions(actions)
        fit=self.fitted(as_of); state=self.snapshot(as_of); values={}; issues=[]
        for f in self.features:
            row=state['measures'][f['measure_id']]
            if row['status']!='known':
                issues.append({'code':'context_unknown','measure_id':f['measure_id']}); continue
            try: values[f['measure_id']]=self._point(row['value'])
            except ModelError: issues.append({'code':'context_interval_unsupported','measure_id':f['measure_id']})
        for d in self.targets:
            if state['measures'][d['measure_id']]['status']!='known':
                issues.append({'code':'target_baseline_unknown','measure_id':d['measure_id']})
        n=len(fit['episodes']); signature=tuple(sorted(actions))
        if n<self.config.get('min_samples',20): issues.append({'code':'insufficient_history','n':n})
        support=fit['portfolios'].get(signature,0)
        if support<self.config.get('min_portfolio_samples',3): issues.append({'code':'portfolio_unsupported','n':support})
        for mid,v in values.items():
            observed=[c[mid] for c in fit['contexts']]
            if observed and not min(observed)<=v<=max(observed):
                issues.append({'code':'context_outside_observed_range','measure_id':mid})
        predictions={}
        if len(values)==len(self.features):
            x=self.vector(values,actions)
            for d in self.targets:
                p=fit['models'][d['measure_id']].predict(x,mass=self.config.get('predictive_mass',0.9))
                for k in ('mean','lower','upper','scale'): p[k]*=d['scale']
                for k in ('noise_variance','parameter_variance'): p[k]*=d['scale']**2
                p['unit']=d['unit']; predictions[d['measure_id']]=p
        return {'status':'supported_prediction' if not issues else 'abstain','issues':issues,'predictions':predictions,
                'training_episode_ids':[e['id'] for e in fit['episodes']], 'training_n':n,'portfolio_support':support,
                'model_sha256':self.model_sha256,'feature_names':self.feature_names,
                'causality_established':False,'joint_coverage_guarantee':False,
                'interpretation':'给定回归与先验假设的边际后验预测；非因果效应，非共形覆盖保证'}

    def simulate(self, action_ids, as_of, *, horizon_days=None, **kwargs):
        horizon_days=self.horizon if horizon_days is None else horizon_days
        if horizon_days!=self.horizon:
            raise ModelError('预测时域必须与训练窗口一致；不外推其他时域')
        targets={d['measure_id'] for d in self.targets}
        # A learned delta replaces hand-written effects on the same measure.
        model=deepcopy(self.model)
        for a in model['actions']: a['effects']=[e for e in a.get('effects',[]) if e['measure_id'] not in targets]
        base=ScenarioKernel(model)
        row=base.simulate(action_ids,as_of,horizon_days=horizon_days,**kwargs)
        row['model_sha256'],row['definition_sha256']=self.model_sha256,self.definition_sha256
        forecast=self.forecast(action_ids,as_of); row['forecast']=forecast
        row['issues']=[i for i in row['issues'] if i.get('code') not in {'guardrail_unknown','guardrail_violated'} or i.get('day')!=horizon_days]
        states=row['trajectory'][-1]['states']; current=self.snapshot(as_of)['measures']
        for mid in targets:
            p=forecast['predictions'].get(mid); initial=current[mid]
            if p and initial['status']=='known':
                states[mid]['value']={'lower':initial['value']['lower']+p['lower'],'upper':initial['value']['upper']+p['upper']}
                states[mid]['status']='known'; states[mid]['basis']='bayesian_transition_prediction'
                m=self.index['measures'][mid]; bounds=m.get('bounds')
                v=states[mid]['value']
                if (m['scale']=='ratio' and v['lower']<0) or (bounds and (v['lower']<bounds['lower'] or v['upper']>bounds['upper'])):
                    row['issues'].append({'code':'projection_outside_measure_domain','measure_id':mid,'day':horizon_days})
            else:
                states[mid]['status'],states[mid]['value']='unmodeled_future',None
        row['issues']+=forecast['issues']
        final=row['trajectory'][-1]; final['goals']=goal_states(self.model,states,self.index['measures']); final['guardrails']=[]
        for g in self.model['guardrails']:
            status=check_condition(g['condition'],states,self.index['measures'])
            final['guardrails'].append({'id':g['id'],'label':g['label'],'status':status})
            if status!='met': row['issues'].append({'code':'guardrail_violated' if status=='not_met' else 'guardrail_unknown','guardrail_id':g['id'],'day':horizon_days})
            if g['condition']['measure_id'] in targets:
                row['issues'].append({'code':'intermediate_guardrail_unmodeled','guardrail_id':g['id']})
        blocked={'prerequisite_missing','resource_exceeded','guardrail_violated','projection_outside_measure_domain'}
        row['status']='blocked' if any(i['code'] in blocked for i in row['issues']) else 'needs_information' if row['issues'] else 'conditional'
        row['interpretation']='固定时域的学习预测；连续过程未建模，不自动推断因果关系或多维联合覆盖'
        return row

    def replay(self):
        """Predict each historical outcome using only earlier available evidence."""
        rows=[]
        for e in sorted(self.episodes,key=lambda e:(instant(e['started_at']),e['id'])):
            fit=self.fitted(e['started_at'])
            values={f['measure_id']:self._point(self.index['observations'][e['before'][f['measure_id']]]['value']) for f in self.features}
            x=self.vector(values,e['action_ids'])
            for d in self.targets:
                mid=d['measure_id']; before=self._point(self.index['observations'][e['before'][mid]]['value']); after=self._point(self.index['observations'][e['after'][mid]]['value'])
                actual=after-before; reg=fit['models'][mid]; p=reg.predict(x,mass=self.config.get('predictive_mass',0.9))
                target=actual/d['scale']
                nll=float(-reg.t.logpdf(target,df=p['df'],loc=p['mean'],scale=p['scale'])+math.log(d['scale']))
                rows.append({'episode_id':e['id'],'measure_id':mid,'unit':d['unit'],'training_n':len(fit['episodes']),
                    'actual_delta':actual,'predicted_delta':p['mean']*d['scale'],
                    'absolute_error':abs(actual-p['mean']*d['scale']),'no_change_absolute_error':abs(actual),
                    'negative_log_predictive_density':nll,'interval_contains_observation':p['lower']<=target<=p['upper'],
                    'predictive_width':(p['upper']-p['lower'])*d['scale']})
        summary={}
        for d in self.targets:
            rs=[r for r in rows if r['measure_id']==d['measure_id'] and r['training_n']>=self.config.get('min_samples',20)]
            summary[d['measure_id']]={'n':len(rs),'unit':d['unit']}
            if rs:
                for out,field in [('mae','absolute_error'),('no_change_mae','no_change_absolute_error'),('mean_nlpd','negative_log_predictive_density'),('observed_coverage','interval_contains_observation'),('mean_width','predictive_width')]:
                    summary[d['measure_id']][out]=sum(r[field] for r in rs)/len(rs)
        return {'rows':rows,'summary':summary,'protocol':'predict_at_episode_start_using_only_recorded_outcomes',
                'model_sha256':self.model_sha256,'policy_value_estimated':False,'causal_effect_estimated':False}
