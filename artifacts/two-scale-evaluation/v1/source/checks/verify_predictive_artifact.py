"""Independent receipt audit for recency/two-scale synthetic predictive artifacts.

Recomputes row errors, interval scores, pairing, cell gates and adoption verdict.
Checks archived bytes and input fingerprints. This audits evidence consistency;
it cannot establish real-world usefulness or independently validate assumptions.
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def at(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def close(actual, expected, reason):
    if expected is None or isinstance(expected, bool):
        require(actual == expected, reason)
    else:
        require(actual is not None and math.isfinite(actual)
                and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-10), reason)


def avg(rows, key):
    return sum(r[key] for r in rows) / len(rows) if rows else None


def verify(directory, *, check_manifest=True):
    directory = Path(directory)
    manifest = json.loads((directory / 'artifact.json').read_text())
    if check_manifest:
        actual_paths = {str(p.relative_to(directory)) for p in directory.rglob('*')
                        if p.is_file() and p != directory / 'artifact.json'
                        and '__pycache__' not in p.parts}
        require(bool(actual_paths) and set(manifest['files']) == actual_paths, 'artifact index incomplete')
        for path, expected in manifest['files'].items():
            blob = (directory / path).read_bytes()
            require(len(blob) == expected['bytes'] and sha256(blob).hexdigest() == expected['sha256'], 'artifact byte mismatch: ' + path)
    protocol_data = (directory / 'protocol.json').read_bytes()
    protocol = json.loads(protocol_data)
    report = json.loads((directory / 'results.json').read_text())
    require(report['protocol_sha256'] == sha256(protocol_data).hexdigest(), 'protocol receipt mismatch')
    for path, digest in protocol['source_sha256'].items():
        require(sha256((directory / 'source' / path).read_bytes()).hexdigest() == digest, 'frozen source mismatch: ' + path)
    models = {}
    for record in report['inputs']:
        blob = gzip.decompress((directory / 'inputs' / f"{record['scenario']}.seed{record['seed']}.json.gz").read_bytes())
        model = json.loads(blob)
        digest = sha256(json.dumps(model, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()
        require(digest == record['model_sha256'] and model['synthetic'] is True, 'input fingerprint mismatch')
        key = record['seed'], record['scenario']
        require(key not in models, 'duplicate input')
        models[key] = model
    require(set(models) == {(s, m) for s in protocol['seeds'] for m in protocol['scenarios']}, 'input grid incomplete')
    rows = [json.loads(line) for line in (directory / 'predictions.jsonl').read_text().splitlines()]
    indexed, grouped = {}, {}
    expected_keys = set()
    for (seed, mode), model in models.items():
        for method in protocol['methods']:
            for e in model['episodes'][protocol['evaluation_start_episode']:protocol['episodes']]:
                for d in model['learning']['targets']:
                    expected_keys.add((seed, mode, method, e['id'], d['measure_id']))
    for row in rows:
        key = tuple(row[k] for k in ['seed', 'scenario', 'method', 'episode_id', 'measure_id'])
        require(key not in indexed, 'duplicate prediction opportunity')
        indexed[key] = row
        grouped.setdefault((row['seed'], row['scenario'], row['method'], row['measure_id']), []).append(row)
        model = models[row['seed'], row['scenario']]
        episode = next(e for e in model['episodes'] if e['id'] == row['episode_id'])
        observations = {o['id']: o for o in model['observations']}
        mid = row['measure_id']
        close(row['actual_delta'], observations[episode['after'][mid]]['value'] - observations[episode['before'][mid]]['value'], 'outcome receipt mismatch')
        require(at(row['started_at']) == at(episode['started_at']), 'issue time changed')
        require(at(row['outcome_recorded_at']) == at(episode['recorded_at']), 'outcome knowledge time changed')
        if 'latest_training_recorded_at' in row:
            mature = [at(e['recorded_at']) for e in model['episodes'] if at(e['recorded_at']) <= at(row['started_at'])]
            # These archived synthetic scenarios have no correction events.
            require(not any(o.get('supersedes') for o in model['observations']), 'correction-aware audit required')
            require(row['training_n'] == len(mature), 'training evidence count mismatch')
            require(at(row['latest_training_recorded_at']) == max(mature), 'latest knowledge receipt mismatch')
        if row.get('state_at') is not None:
            require(at(row['state_at']) == at(row['started_at']) + timedelta(days=model['learning']['horizon_days']), 'prediction state horizon mismatch')
        if not row['supported']:
            require(bool(row['issues']), 'abstention reason missing')
            require(all(row[k] is None for k in ['predicted_delta', 'lower', 'upper', 'absolute_error', 'width', 'covered', 'interval_score']), 'abstention scored as prediction')
            continue
        require(not row['issues'], 'supported prediction has unresolved issue')
        y, lo, hi = row['actual_delta'], row['lower'], row['upper']
        alpha = 1 - model['learning']['predictive_mass']
        close(row['absolute_error'], abs(y - row['predicted_delta']), 'row MAE mismatch')
        close(row['width'], hi - lo, 'row width mismatch')
        close(row['covered'], lo <= y <= hi, 'row coverage mismatch')
        close(row['interval_score'], hi - lo + 2 / alpha * (max(lo - y, 0) + max(y - hi, 0)), 'row interval score mismatch')
        if row.get('components'):
            close(row['predicted_delta'], row['components']['structural_mean'] + row['components']['transient_mean'], 'component sum mismatch')
    require(set(indexed) == expected_keys, 'prediction opportunity grid incomplete')
    seen, candidate = set(), []
    gate = protocol['cell_gate']
    for cell in report['results']:
        key = tuple(cell[k] for k in ['seed', 'scenario', 'method', 'measure_id'])
        require(key not in seen and key in grouped, 'duplicate or unknown summary cell')
        seen.add(key)
        selected = grouped[key]
        finite = [r for r in selected if r['supported']]
        paired = [r for r in finite if indexed[(r['seed'], r['scenario'], protocol['methods'][0], r['episode_id'], r['measure_id'])]['supported']]
        base = [indexed[(r['seed'], r['scenario'], protocol['methods'][0], r['episode_id'], r['measure_id'])] for r in paired]
        for field, expected in [('n', len(selected)), ('finite_n', len(finite)), ('finite_rate', len(finite) / len(selected)), ('paired_n', len(paired))]:
            close(cell[field], expected, field + ' denominator mismatch')
        metrics = {'coverage': (finite, 'covered'), 'mean_absolute_error': (finite, 'absolute_error'), 'mean_width': (finite, 'width'), 'mean_interval_score': (finite, 'interval_score'), 'paired_mae': (paired, 'absolute_error'), 'paired_baseline_mae': (base, 'absolute_error'), 'paired_interval_score': (paired, 'interval_score'), 'paired_baseline_interval_score': (base, 'interval_score'), 'paired_coverage': (paired, 'covered'), 'paired_baseline_coverage': (base, 'covered')}
        if 'mean_negative_log_predictive_density' in cell:
            metrics['mean_negative_log_predictive_density'] = finite, 'negative_log_predictive_density'
        for field, (sample, metric) in metrics.items():
            close(cell[field], avg(sample, metric), field + ' aggregate mismatch')
        verdict = {'finite': len(finite) / len(selected) >= gate['finite_rate_at_least'], 'paired': len(paired) / len(selected) >= gate['paired_rate_at_least'], 'coverage': bool(finite) and avg(finite, 'covered') >= gate['coverage_at_least'], 'mae': bool(paired) and avg(paired, 'absolute_error') <= gate['paired_mae_ratio_at_most'] * avg(base, 'absolute_error'), 'interval_score': bool(paired) and avg(paired, 'interval_score') <= gate['paired_interval_score_ratio_at_most'] * avg(base, 'interval_score')}
        require(cell['gate'] == verdict and cell['passes'] == all(verdict.values()), 'cell gate verdict mismatch')
        if key[2] == protocol['methods'][-1]:
            candidate.append(cell)
    require(seen == set(grouped), 'summary grid incomplete')
    shifted = [c for c in candidate if c['scenario'] in protocol['gain_scenarios'] and c['paired_n']]
    denominator = sum(c['paired_baseline_mae'] * c['paired_n'] for c in shifted)
    ratio = sum(c['paired_mae'] * c['paired_n'] for c in shifted) / denominator if denominator else None
    close(report['aggregate_shift_mae_ratio'], ratio, 'aggregate gain mismatch')
    eligible = all(c['passes'] for c in candidate) and ratio is not None and ratio <= protocol['aggregate_shift_mae_ratio_at_most']
    require(report['benchmark_eligible'] == eligible and report['default_changed'] is False, 'adoption verdict mismatch')
    return {'verified': True, 'prediction_opportunities': len(rows), 'summary_cells': len(seen), 'candidate_passed_cells': sum(c['passes'] for c in candidate), 'benchmark_eligible': eligible}


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('artifact_dir', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.artifact_dir)))
