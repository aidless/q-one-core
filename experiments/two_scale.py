"""Research-only static action structure plus a calendar-time OU offset.

Conditionally on one unknown common variance, all transitions/observations are
linear Gaussian. Integrating that variance yields Student-t predictions. The
latent offset is a statistical component, not a measured psychological state.
"""
from datetime import timedelta

from qone_core.life.adaptive import AdaptiveKernel, BayesianTransition
from qone_core.life.model import ModelError, instant, number


class TwoScaleTransition(BayesianTransition):
    def __init__(self, dimensions, *, half_life_days, transient_variance,
                 precision=1.0, alpha=2.0, beta=1.0):
        super().__init__(dimensions, precision=precision, alpha=alpha, beta=beta)
        self.feature_count = dimensions
        self.half_life_days = number(half_life_days)
        self.transient_variance = number(transient_variance)
        if self.half_life_days <= 0 or self.transient_variance < 0:
            raise ModelError('positive half life and nonnegative transient variance required')
        self.mean = self.np.r_[self.mean, 0.0]
        self.cov = self.np.pad(self.cov, ((0, 1), (0, 1)))
        self.cov[-1, -1] = self.transient_variance
        self.time = None

    def _augmented(self, features):
        x = self.np.asarray(features, dtype=float)
        if x.shape != (self.feature_count,) or not self.np.isfinite(x).all():
            raise ModelError('invalid static features')
        return self.np.r_[x, 1.0]

    def advance(self, at):
        target = instant(at)
        if self.time is not None:
            days = (target - self.time).total_seconds() / 86400
            if days < 0:
                raise ModelError('filter events must be in physical-time order')
            rho = 2.0 ** (-days / self.half_life_days)
            self.mean[-1] *= rho
            # Retain the cross covariance between static and transient states.
            self.cov[-1, :] *= rho
            self.cov[:, -1] *= rho
            self.cov[-1, -1] += self.transient_variance * (1 - rho * rho)
        self.time = target

    def update_at(self, features, target, at):
        x, y = self._augmented(features), number(target)
        self.advance(at)
        # Independent conjugate Gaussian conditioning; common variance retained.
        super().update(x, y)

    def predict(self, features, *, mass=0.90):
        x = self._augmented(features)
        p = super().predict(x, mass=mass)
        p['structural_mean_normalized'] = float(x[:-1] @ self.mean[:-1])
        p['transient_mean_normalized'] = float(self.mean[-1])
        return p


class TwoScaleKernel(AdaptiveKernel):
    """As-of filtering only; late labels are inserted at their outcome event time.

    At every knowledge cutoff, rebuild from eligible, correction-valid episodes
    sorted by ended_at. Forecast to as_of + fixed outcome horizon. Never smooth
    using labels that had not arrived at issue time, or use label-arrival time as
    the latent state time. Raw-history support checks remain unchanged.
    """
    def __init__(self, model, *, half_life_days, transient_variance):
        super().__init__(model)
        self.half_life_days = number(half_life_days)
        self.transient_variance = number(transient_variance)
        if self.half_life_days <= 0 or self.transient_variance < 0:
            raise ModelError('invalid two-scale parameters')
        if self.calibration_config is not None:
            raise ModelError('isolate dynamics from interval calibration')
        self._two_scale_cache = {}

    def fitted(self, as_of):
        cutoff = instant(as_of)
        key = cutoff.isoformat()
        if key in self._two_scale_cache:
            return self._two_scale_cache[key]
        base = super().fitted(as_of)
        models = {d['measure_id']: TwoScaleTransition(
            len(self.feature_names), half_life_days=self.half_life_days,
            transient_variance=self.transient_variance, **{
                k: self.config[k] for k in ('precision', 'alpha', 'beta') if k in self.config
            }) for d in self.targets}
        ordered = sorted(base['episodes'], key=lambda e: (instant(e['ended_at']), e['id']))
        for e in ordered:
            values = {f['measure_id']: self._point(self.index['observations'][
                e['before'][f['measure_id']]]['value']) for f in self.features}
            x = self.vector(values, e['action_ids'])
            for d in self.targets:
                mid = d['measure_id']
                before = self._point(self.index['observations'][e['before'][mid]]['value'])
                after = self._point(self.index['observations'][e['after'][mid]]['value'])
                models[mid].update_at(x, (after - before) / d['scale'], e['ended_at'])
        query_end = cutoff + timedelta(days=self.horizon)
        for reg in models.values():
            reg.advance(query_end)
        result = {**base, 'models': models, 'state_at': query_end.isoformat(),
                  'filter_episode_ids': [e['id'] for e in ordered]}
        if len(self._two_scale_cache) >= 16:
            self._two_scale_cache.clear()
        self._two_scale_cache[key] = result
        return result

    def forecast(self, actions, as_of):
        row = super().forecast(actions, as_of)
        fit = self.fitted(as_of)
        row['dynamics'] = {'deployment': 'research_only', 'state_at': fit['state_at'],
                           'half_life_days': self.half_life_days,
                           'transient_variance_relative_to_noise': self.transient_variance,
                           'filter_episode_ids': fit['filter_episode_ids'],
                           'eligibility_time': 'recorded_at', 'state_time': 'ended_at',
                           'separate_noise_drift_model': False}
        for d in self.targets:
            p = row['predictions'].get(d['measure_id'])
            if p:
                p['components'] = {
                    'structural_mean': p.pop('structural_mean_normalized') * d['scale'],
                    'transient_mean': p.pop('transient_mean_normalized') * d['scale'],
                    'unit': d['unit'], 'latent_state_identified': False}
        row['interpretation'] = 'Research-only common-scale static-plus-OU Student-t prediction; no causal or coverage guarantee'
        return row
