"""Delayed-label prequential interval calibration, inspired by ACI.

Independently implemented from the update equation in Gibbs & Candes (2021).
Rolling normalized scores and delayed feedback differ from the paper setting;
no distribution-free, conditional, joint or delayed-feedback guarantee is made.
"""
from collections import deque
from math import ceil

from .model import ModelError, instant, number


def calibration_config(value):
    if value is None:
        return None
    if not isinstance(value,dict) or value.get('method')!='prequential_aci':
        raise ModelError('校准方法需为prequential_aci，或不设置calibration')
    if set(value)-{'method','step_size','window','min_samples'}:
        raise ModelError('校准配置包含未知字段')
    result={'method':'prequential_aci','step_size':0.01,'window':64,'min_samples':10}|value
    if not 0 <= number(result['step_size']) <= 0.2:
        raise ModelError('校准步长应为0到0.2；0表示固定分位数对照')
    if (type(result['window']) is not int or type(result['min_samples']) is not int
            or not 5 <= result['min_samples'] <= result['window'] <= 512):
        raise ModelError('校准样本门槛需满足5<=min_samples<=window<=512')
    return result


class DelayedACI:
    """One measure / one executed-action portfolio, updated in knowledge time."""
    def __init__(self, *, target_alpha, step_size=0.01, window=64, min_samples=10):
        self.config=calibration_config({'method':'prequential_aci','step_size':step_size,'window':window,'min_samples':min_samples})
        if not 0 < number(target_alpha) < 1:
            raise ModelError('目标误覆盖率需在0与1之间')
        self.target_alpha=self.alpha=target_alpha
        self.scores=deque(maxlen=window)
        self.pending={}; self.seen=set(); self.time=None

    def _advance(self, at):
        at=instant(at)
        if self.time is not None and at<self.time:
            raise ModelError('校准事件必须按已知时间排序；不能回写过去')
        self.time=at
        return at

    def interval(self):
        n=len(self.scores)
        result={'method':'prequential_aci','calibration_n':n,'adjusted_alpha':self.alpha,
                'target_alpha':self.target_alpha,'score_ids':[r['id'] for r in self.scores],
                'coverage_guarantee':False,'radius':None,
                'last_score_recorded_at':self.scores[-1]['recorded_at'] if self.scores else None}
        if n<self.config['min_samples']:
            return result|{'status':'insufficient_calibration'}
        rank=ceil((n+1)*(1-self.alpha))
        if rank>n:
            return result|{'status':'unbounded'}
        if rank<=0:
            return result|{'status':'empty'}
        return result|{'status':'ready','radius':sorted(r['score'] for r in self.scores)[rank-1]}

    def issue(self, token, at, *, mean, scale):
        if not isinstance(token,str) or not token or token in self.seen:
            raise ModelError('预测凭据ID缺失或重复')
        if number(scale)<=0:
            raise ModelError('预测尺度应为正')
        mean=number(mean)
        at=self._advance(at)
        receipt=self.interval()|{'id':token,'issued_at':at.isoformat(),'mean':mean,'scale':scale}
        self.pending[token]=receipt; self.seen.add(token)
        return dict(receipt)

    def observe(self, token, recorded_at, actual):
        if token not in self.pending:
            raise ModelError('结果必须关联尚未更新的预测凭据')
        actual=number(actual); receipt=self.pending[token]
        at=self._advance(recorded_at)
        if at<instant(receipt['issued_at']):
            raise ModelError('不能在发出预测前更新结果')
        score=abs(actual-receipt['mean'])/receipt['scale']
        status=receipt['status']
        # Feedback uses the interval ISSUED then, not a recomputed interval now.
        error=(score>receipt['radius']) if status=='ready' else False if status=='unbounded' else True if status=='empty' else None
        if error is not None:
            self.alpha+=self.config['step_size']*(self.target_alpha-int(error))
        self.scores.append({'id':token,'score':score,'recorded_at':at.isoformat()})
        del self.pending[token]
        return {'id':token,'score':score,'error':error,'adjusted_alpha':self.alpha}
