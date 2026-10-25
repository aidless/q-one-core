"""A self-consistent checksum must not hide arithmetic or denominator errors."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('predictive_receipt_audit', ROOT / 'scripts/verify_predictive_artifact.py')
audit = module_from_spec(spec)
spec.loader.exec_module(audit)
REFERENCE = ROOT / 'artifacts/recency-evaluation/v1'


def test_published_negative_result_passes_independent_audit():
    result = audit.verify(REFERENCE)
    assert result['verified'] and result['prediction_opportunities'] == 5376
    assert result['candidate_passed_cells'] == 10 and not result['benchmark_eligible']


@pytest.mark.parametrize('damage', ['summary', 'drop_opportunity', 'adoption', 'source'])
def test_injected_error_is_rejected_even_without_manifest_checksum_check(tmp_path, damage):
    artifact = tmp_path / 'artifact'
    shutil.copytree(REFERENCE, artifact)
    if damage in {'summary', 'adoption'}:
        p = artifact / 'results.json'
        report = json.loads(p.read_text())
        if damage == 'summary':
            report['results'][0]['mean_width'] += 1
        else:
            report['benchmark_eligible'] = True
        p.write_text(json.dumps(report))
    elif damage == 'drop_opportunity':
        p = artifact / 'predictions.jsonl'
        p.write_text('\n'.join(p.read_text().splitlines()[1:]) + '\n')
    else:
        p = artifact / 'source/experiments/recency_power.py'
        p.write_text(p.read_text() + '\n# changed\n')
    with pytest.raises(ValueError):
        audit.verify(artifact, check_manifest=False)


def test_empty_checksum_index_is_rejected(tmp_path):
    artifact = tmp_path / 'artifact'
    shutil.copytree(REFERENCE, artifact)
    p = artifact / 'artifact.json'
    manifest = json.loads(p.read_text())
    manifest['files'] = {}
    p.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='artifact index incomplete'):
        audit.verify(artifact)
