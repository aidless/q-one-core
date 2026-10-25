"""Frozen as-of challenger comparison. No runtime recommendation policy changes."""
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'experiments')]
from qone_core.life import AdaptiveKernel
from qone_core.life.model import fingerprint, instant
from recency_power import RecencyKernel

ART = ROOT / 'artifacts/recency-evaluation/v1'


def scenario(seed, mode, count, shift_at):
    fixture = runpy.run_path(str(ROOT / 'examples/generate_adaptive_fixture.py'))['fixture']
    model = fixture(seed=seed, count=count)
    obs = {o['id']: o for o in model['observations']}
    rng = random.Random(seed + 30000)
    offset_days = 0
    for i, e in enumerate(model['episodes']):
        if mode == 'irregular_delayed_mean_shift':
            if i:
                offset_days += [2, 3, 5, 2, 4][(i - 1) % 5]
            if i == shift_at:
                offset_days += 40
            start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=offset_days)
            end = start + timedelta(days=1)
            e['started_at'], e['ended_at'] = start.isoformat(), end.isoformat()
            for oid in set(e['before'].values()):
                obs[oid]['observed_at'] = obs[oid]['recorded_at'] = start.isoformat()
            for oid in e['after'].values():
                obs[oid]['observed_at'] = end.isoformat()
        end = instant(e['ended_at'])
        delay = 7 if 'delayed' in mode and i % 5 == 0 else 0
        e['recorded_at'] = (end + timedelta(days=delay)).isoformat()
        for oid in e['after'].values():
            obs[oid]['recorded_at'] = e['recorded_at']
        for mid, oid in e['after'].items():
            magnitude = 6 if mid == 'practice' else -4
            if i < shift_at:
                continue
            if mode in {'mean_shift', 'delayed_mean_shift', 'irregular_delayed_mean_shift'}:
                obs[oid]['value'] += magnitude
            elif mode == 'return_shift' and i < shift_at + 32:
                obs[oid]['value'] += magnitude
            elif mode == 'gradual_shift':
                obs[oid]['value'] += magnitude * min(1, (i - shift_at + 1) / 32)
            elif mode == 'noise_shift':
                obs[oid]['value'] += rng.gauss(0, 4)
    # Keep non-episode example observations out of every prediction cutoff.
    after_last = (instant(model['episodes'][-1]['recorded_at']) + timedelta(days=10)).isoformat()
    for o in model['observations']:
        if o['id'].startswith('current-'):
            o['observed_at'] = o['recorded_at'] = after_last
    return model


def score_interval(y, lower, upper, mass):
    alpha = 1 - mass
    return upper - lower + 2 / alpha * max(lower - y, 0) + 2 / alpha * max(y - upper, 0)


def mean(rows, key):
    return sum(r[key] for r in rows) / len(rows) if rows else None


def summarize(rows, baseline, gate):
    finite = [r for r in rows if r['supported']]
    paired = [r for r in finite if baseline[r['episode_id']]['supported']]
    reference = [baseline[r['episode_id']] for r in paired]
    out = {'n': len(rows), 'finite_n': len(finite), 'finite_rate': len(finite) / len(rows),
           'paired_n': len(paired), 'coverage': mean(finite, 'covered'),
           'mean_absolute_error': mean(finite, 'absolute_error'),
           'mean_width': mean(finite, 'width'), 'mean_interval_score': mean(finite, 'interval_score'),
           'paired_mae': mean(paired, 'absolute_error'),
           'paired_baseline_mae': mean(reference, 'absolute_error'),
           'paired_interval_score': mean(paired, 'interval_score'),
           'paired_baseline_interval_score': mean(reference, 'interval_score'),
           'paired_coverage': mean(paired, 'covered'),
           'paired_baseline_coverage': mean(reference, 'covered')}
    out['gate'] = {
        'finite': out['finite_rate'] >= gate['finite_rate_at_least'],
        'coverage': bool(finite) and out['coverage'] >= gate['coverage_at_least'],
        'paired': len(paired) / len(rows) >= gate['paired_rate_at_least'],
        'mae': bool(paired) and out['paired_mae'] <= gate['paired_mae_ratio_at_most'] * out['paired_baseline_mae'],
        'interval_score': bool(paired) and out['paired_interval_score'] <= gate['paired_interval_score_ratio_at_most'] * out['paired_baseline_interval_score']}
    out['passes'] = all(out['gate'].values())
    return out


def main():
    parser = ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Use a new empty directory, never overwrite a frozen result')
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('output directory must be empty')
    protocol_bytes = (ART / 'protocol.json').read_bytes()
    protocol = json.loads(protocol_bytes)
    for path, digest in protocol['source_sha256'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise SystemExit('frozen source mismatch: ' + path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries, inputs, rows_out = [], [], []
    for seed in protocol['seeds']:
        for mode in protocol['scenarios']:
            model = scenario(seed, mode, protocol['episodes'], protocol['shift_at_episode'])
            inputs.append({'seed': seed, 'scenario': mode, 'model_sha256': fingerprint(model)})
            obs = {o['id']: o for o in model['observations']}
            kernels = {'lifetime': AdaptiveKernel(model),
                       'recency': RecencyKernel(model, half_life_days=protocol['half_life_days'])}
            grouped = {}
            for e in model['episodes'][protocol['evaluation_start_episode']:]:
                for name, k in kernels.items():
                    p = k.forecast(e['action_ids'], e['started_at'])
                    for d in k.targets:
                        mid = d['measure_id']
                        pred = p['predictions'][mid]
                        actual = obs[e['after'][mid]]['value'] - obs[e['before'][mid]]['value']
                        supported = p['status'] == 'supported_prediction'
                        lo, hi = (pred['lower'], pred['upper']) if supported else (None, None)
                        r = {'seed': seed, 'scenario': mode, 'method': name, 'episode_id': e['id'],
                             'measure_id': mid, 'unit': d['unit'], 'started_at': e['started_at'],
                             'outcome_recorded_at': e['recorded_at'], 'training_n': p['training_n'],
                             'supported': supported, 'issues': [i['code'] for i in p['issues']],
                             'information': p.get('information'), 'portfolio_information': p.get('portfolio_information'),
                             'actual_delta': actual, 'predicted_delta': pred['mean'] if supported else None,
                             'lower': lo, 'upper': hi,
                             'absolute_error': abs(actual - pred['mean']) if supported else None,
                             'width': hi - lo if supported else None,
                             'covered': lo <= actual <= hi if supported else None,
                             'interval_score': score_interval(actual, lo, hi, pred['mass']) if supported else None}
                        grouped.setdefault((name, mid), []).append(r)
                        rows_out.append(r)
            for (name, mid), rows in grouped.items():
                baseline = {r['episode_id']: r for r in grouped[('lifetime', mid)]}
                summaries.append({'seed': seed, 'scenario': mode, 'method': name, 'measure_id': mid,
                                  **summarize(rows, baseline, protocol['cell_gate'])})
    candidates = [r for r in summaries if r['method'] == 'recency']
    shift = [r for r in candidates if r['scenario'] in protocol['gain_scenarios']]
    paired_shift = [r for r in shift if r['paired_n']]
    denominator = sum(r['paired_baseline_mae'] * r['paired_n'] for r in paired_shift)
    shift_ratio = sum(r['paired_mae'] * r['paired_n'] for r in paired_shift) / denominator if denominator else None
    eligible = (all(r['passes'] for r in candidates) and shift_ratio is not None
                and shift_ratio <= protocol['aggregate_shift_mae_ratio_at_most'])
    import numpy, scipy
    report = {'schema_version': 1, 'synthetic': True, 'protocol_sha256': sha256(protocol_bytes).hexdigest(),
              'results': summaries, 'inputs': inputs, 'aggregate_shift_mae_ratio': shift_ratio,
              'benchmark_eligible': eligible, 'default_changed': False,
              'default_adoption_requires': 'All benchmark gates plus future data outside this synthetic family',
              'runtime': {'python': platform.python_version(), 'numpy': numpy.__version__, 'scipy': scipy.__version__},
              'claims_excluded': ['real_person_benefit', 'policy_value', 'causality', 'coverage_guarantee', 'SOTA']}
    (args.output_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    (args.output_dir / 'predictions.jsonl').write_text(''.join(json.dumps(
        r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for r in rows_out))
    print(json.dumps({'benchmark_eligible': eligible, 'cells': len(summaries), 'rows': len(rows_out),
                      'aggregate_shift_mae_ratio': shift_ratio}))


if __name__ == '__main__':
    main()
