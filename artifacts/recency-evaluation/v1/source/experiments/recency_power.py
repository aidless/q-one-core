"""Research-only event-time power likelihood; never imported by the runtime package.

An independent conjugate derivation, not River's fixed-noise EMA or ReBayes EKF.
A weighted likelihood is a modelling choice, not an ordinary posterior under
exchangeable observations or a calibrated coverage guarantee.
"""
import math

from qone_core.life.adaptive import AdaptiveKernel, BayesianTransition
from qone_core.life.model import ModelError, instant, number


def event_weight(ended_at, as_of, half_life_days):
    half_life_days = number(half_life_days)
    if half_life_days <= 0:
        raise ModelError('half_life_days must be positive')
    age_days = (instant(as_of) - instant(ended_at)).total_seconds() / 86400
    if age_days < 0:
        raise ModelError('outcome event is in the future')
    return 2.0 ** (-age_days / half_life_days)


def information(weights):
    weights = list(weights)
    mass = math.fsum(weights)
    square_sum = math.fsum(w * w for w in weights)
    return {'raw_n': len(weights), 'weight_mass': mass,
            'weight_concentration_ess': mass * mass / square_sum if square_sum else 0.0}


class PowerTransition(BayesianTransition):
    """Normal-inverse-gamma update for product_i likelihood_i ** weight_i."""
    def update(self, features, target, *, weight=1.0):
        x, y, w = self._x(features), number(target), number(weight)
        if not 0 <= w <= 1:
            raise ModelError('recency weights must be in [0,1]')
        v = self.cov @ x
        denominator = 1.0 + w * float(x @ v)
        residual = y - float(x @ self.mean)
        # This form remains well-defined when an old event's weight underflows.
        self.mean += v * (w * residual / denominator)
        self.cov -= self.np.outer(v, v) * (w / denominator)
        self.cov = (self.cov + self.cov.T) / 2
        self.beta += 0.5 * w * residual ** 2 / denominator
        self.alpha += 0.5 * w
        self.n += 1  # Raw eligible observations, not information mass or ESS.


class RecencyKernel(AdaptiveKernel):
    """Isolated challenger. Outcome age uses ended_at, eligibility recorded_at.

    Keep the original prior fixed, rebuild as-of, and retain the base context,
    action-version, correction and support checks. Historical contexts still
    define the same coarse coordinate-wise OOD box; no joint drift claim.
    """
    def __init__(self, model, *, half_life_days):
        super().__init__(model)
        self.half_life_days = number(half_life_days)
        if self.half_life_days <= 0:
            raise ModelError('half_life_days must be positive')
        if self.calibration_config is not None:
            raise ModelError('isolate the point-model experiment from interval calibration')
        self._recency_cache = {}

    def fitted(self, as_of):
        key = instant(as_of).isoformat()
        if key in self._recency_cache:
            return self._recency_cache[key]
        base = super().fitted(as_of)
        models = {d['measure_id']: PowerTransition(len(self.feature_names), **{
            k: self.config[k] for k in ('precision', 'alpha', 'beta') if k in self.config
        }) for d in self.targets}
        weights, portfolio_weights = [], {}
        for e in base['episodes']:
            w = event_weight(e['ended_at'], as_of, self.half_life_days)
            weights.append(w)
            portfolio_weights.setdefault(tuple(sorted(e['action_ids'])), []).append(w)
            values = {d['measure_id']: self._point(self.index['observations'][
                e['before'][d['measure_id']]]['value']) for d in self.features}
            x = self.vector(values, e['action_ids'])
            for d in self.targets:
                before = self._point(self.index['observations'][e['before'][d['measure_id']]]['value'])
                after = self._point(self.index['observations'][e['after'][d['measure_id']]]['value'])
                models[d['measure_id']].update(x, (after - before) / d['scale'], weight=w)
        result = {**base, 'models': models, 'information': information(weights),
                  'portfolio_information': {k: information(v) for k, v in portfolio_weights.items()}}
        if len(self._recency_cache) >= 16:
            self._recency_cache.clear()
        self._recency_cache[key] = result
        return result

    def forecast(self, actions, as_of):
        row = super().forecast(actions, as_of)
        fit = self.fitted(as_of)
        support = fit['portfolio_information'].get(tuple(sorted(actions)), information([]))
        row['information'] = fit['information']
        row['portfolio_information'] = support
        row['recency'] = {'half_life_days': self.half_life_days,
                         'age_basis': 'ended_at', 'eligibility_basis': 'recorded_at',
                         'deployment': 'research_only'}
        if fit['information']['weight_mass'] < self.config.get('min_samples', 20):
            row['issues'].append({'code': 'insufficient_recent_information'})
        if support['weight_mass'] < self.config.get('min_portfolio_samples', 3):
            row['issues'].append({'code': 'insufficient_recent_portfolio_information'})
        row['status'] = 'abstain' if row['issues'] else 'supported_prediction'
        row['interpretation'] = 'Research-only power-likelihood predictive distribution; no coverage or causal guarantee'
        return row
