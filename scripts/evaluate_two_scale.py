"""Frozen predictive comparison of a static-plus-OU challenger, research only."""
from argparse import ArgumentParser
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'experiments')]
from qone_core.life import AdaptiveKernel
from qone_core.life.model import fingerprint, instant
from two_scale import TwoScaleKernel

REFERENCE = runpy.run_path(str(ROOT / 'scripts/evaluate_recency.py'))
ART = ROOT / 'artifacts/two-scale-evaluation/v1'


def scenario(seed, mode, count, shift_at):
    model = REFERENCE['scenario'](seed, 'stationary' if mode == 'action_effect_shift' else mode, count, shift_at)
    if mode == 'action_effect_shift':
        obs = {o['id']: o for o in model['observations']}
        for e in model['episodes'][shift_at:]:
            if 'study' in e['action_ids']:
                obs[e['after']['practice']]['value'] += 6
            if 'build' in e['action_ids']:
                obs[e['after']['work']]['value'] -= 4
    return model


def main():
    parser = ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('output directory must be empty; do not overwrite frozen evidence')
    data = (ART / 'protocol.json').read_bytes()
    protocol = json.loads(data)
    for path, digest in protocol['source_sha256'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise SystemExit('frozen source mismatch: ' + path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records, summaries, inputs = [], [], []
    for seed in protocol['seeds']:
        for mode in protocol['scenarios']:
            model = scenario(seed, mode, protocol['episodes'], protocol['shift_at_episode'])
            inputs.append({'seed': seed, 'scenario': mode, 'model_sha256': fingerprint(model)})
            obs = {o['id']: o for o in model['observations']}
            episodes = {e['id']: e for e in model['episodes']}
            kernels = {'lifetime': AdaptiveKernel(model), 'two_scale': TwoScaleKernel(
                model, **protocol['candidate_parameters'])}
            grouped = {}
            for e in model['episodes'][protocol['evaluation_start_episode']:]:
                for name, k in kernels.items():
                    forecast = k.forecast(e['action_ids'], e['started_at'])
                    mature = [instant(episodes[eid]['recorded_at']) for eid in forecast['training_episode_ids']]
                    latest = max(mature).isoformat() if mature else None
                    assert latest is None or instant(latest) <= instant(e['started_at'])
                    for d in k.targets:
                        mid = d['measure_id']; p = forecast['predictions'][mid]
                        actual = obs[e['after'][mid]]['value'] - obs[e['before'][mid]]['value']
                        supported = forecast['status'] == 'supported_prediction'
                        lo, hi = (p['lower'], p['upper']) if supported else (None, None)
                        reg = k.fitted(e['started_at'])['models'][mid]
                        nlpd = float(-reg.t.logpdf(actual / d['scale'], df=p['df'],
                            loc=p['mean'] / d['scale'], scale=p['scale'] / d['scale']) + math.log(d['scale'])) if supported else None
                        row = {'seed': seed, 'scenario': mode, 'method': name, 'episode_id': e['id'],
                               'measure_id': mid, 'unit': d['unit'], 'started_at': e['started_at'],
                               'outcome_recorded_at': e['recorded_at'], 'latest_training_recorded_at': latest,
                               'training_n': forecast['training_n'], 'supported': supported,
                               'issues': [i['code'] for i in forecast['issues']],
                               'components': p.get('components') if supported else None,
                               'state_at': forecast.get('dynamics', {}).get('state_at'),
                               'actual_delta': actual, 'predicted_delta': p['mean'] if supported else None,
                               'lower': lo, 'upper': hi, 'negative_log_predictive_density': nlpd,
                               'absolute_error': abs(actual - p['mean']) if supported else None,
                               'width': hi - lo if supported else None,
                               'covered': lo <= actual <= hi if supported else None,
                               'interval_score': REFERENCE['score_interval'](actual, lo, hi, p['mass']) if supported else None}
                        grouped.setdefault((name, mid), []).append(row)
                        records.append(row)
            for (name, mid), rows in grouped.items():
                base = {r['episode_id']: r for r in grouped[('lifetime', mid)]}
                summary = REFERENCE['summarize'](rows, base, protocol['cell_gate'])
                finite = [r for r in rows if r['supported']]
                summary['mean_negative_log_predictive_density'] = REFERENCE['mean'](finite, 'negative_log_predictive_density')
                summaries.append({'seed': seed, 'scenario': mode, 'method': name, 'measure_id': mid, **summary})
    candidate = [r for r in summaries if r['method'] == 'two_scale']
    shift = [r for r in candidate if r['scenario'] in protocol['gain_scenarios'] and r['paired_n']]
    denominator = sum(r['paired_baseline_mae'] * r['paired_n'] for r in shift)
    ratio = sum(r['paired_mae'] * r['paired_n'] for r in shift) / denominator if denominator else None
    eligible = (all(r['passes'] for r in candidate) and ratio is not None
                and ratio <= protocol['aggregate_shift_mae_ratio_at_most'])
    import numpy, scipy
    report = {'schema_version': 1, 'synthetic': True, 'protocol_sha256': sha256(data).hexdigest(),
              'results': summaries, 'inputs': inputs, 'aggregate_shift_mae_ratio': ratio,
              'benchmark_eligible': eligible, 'default_changed': False,
              'default_adoption_requires': 'All predictive gates plus independent/future-data validation; this research module is never deployed automatically',
              'runtime': {'python': platform.python_version(), 'numpy': numpy.__version__, 'scipy': scipy.__version__},
              'claims_excluded': ['personal_benefit', 'identified_latent_state', 'causality', 'policy_value', 'coverage_guarantee', 'SOTA']}
    (args.output_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    (args.output_dir / 'predictions.jsonl').write_text(''.join(json.dumps(
        r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for r in records))
    print(json.dumps({'benchmark_eligible': eligible, 'cells': len(summaries), 'prediction_opportunities': len(records),
                      'aggregate_shift_mae_ratio': ratio}))


if __name__ == '__main__':
    main()
