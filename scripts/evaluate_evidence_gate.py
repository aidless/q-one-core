"""Frozen synthetic counterexamples for bitemporal training evidence qualification."""
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import gzip
import importlib.util
import json
import platform
import sys

ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=ROOT/'artifacts/evidence-gate/v1'

def load_kernel(folder,name):
    spec=importlib.util.spec_from_file_location(name,folder/'__init__.py',submodule_search_locations=[str(folder)])
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module)
    return module.AdaptiveKernel

def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')

def common_equal(old,new):
    """All pre-existing fields must match; added evidence receipts may differ."""
    if isinstance(old,dict): return all(k in new and common_equal(v,new[k]) for k,v in old.items())
    if isinstance(old,list): return len(old)==len(new) and all(common_equal(a,b) for a,b in zip(old,new))
    return old==new

def evaluate(phase):
    import numpy, scipy
    protocol_data=(ARTIFACT/'protocol.json').read_bytes(); p=json.loads(protocol_data)
    baseline=load_kernel(ARTIFACT/'source/baseline/qone_core/life','evidence_baseline')
    for path,digest in p['source_sha256'].items():
        assert sha256((ARTIFACT/'source/baseline'/path).read_bytes()).hexdigest()==digest
    candidate=load_kernel(ROOT/'src/qone_core/life','evidence_candidate') if phase=='candidate' else baseline
    results=[]
    for name in p['cases']:
        blob=gzip.decompress((ARTIFACT/'inputs'/(name+'.json.gz')).read_bytes())
        assert sha256(blob).hexdigest()==p['input_sha256'][name]
        model=json.loads(blob); old,new=baseline(model),candidate(model)
        before,after=old.fitted(p['as_of']),new.fitted(p['as_of'])
        old_ids=[e['id'] for e in before['episodes']]; new_ids=[e['id'] for e in after['episodes']]
        wanted=p['excluded_episode_by_case'].get(name,[])
        expected_ids=[e['id'] for e in model['episodes'] if e['id'] not in wanted]
        row={'case':name,'old_training_n':len(old_ids),'new_training_n':len(new_ids),'expected_excluded_ids':wanted,
             'selection_matches':new_ids==expected_ids,'old_prediction':old.forecast(['study'],p['as_of']),
             'new_prediction':new.forecast(['study'],p['as_of'])}
        old_replay=old.replay()
        new_replay=new.replay(as_of=p['as_of']) if phase=='candidate' else new.replay()
        row['old_replay_row_n']=len(old_replay['rows']); row['new_replay_row_n']=len(new_replay['rows'])
        if phase=='candidate':
            row['evidence_summary']=after['evidence_summary']; row['excluded_episodes']=after['excluded_episodes']
            assert row['selection_matches'],name
            assert len(new_replay['rows'])==2*len(expected_ids),name
            assert after['evidence_summary']=={'available_n':40,'trainable_n':len(expected_ids),'excluded_n':len(wanted)},name
            assert {e['episode_id'] for e in after['excluded_episodes']}==set(wanted),name
            assert new_replay['evidence_summary']==after['evidence_summary'],name
            if not wanted:
                row['unchanged_existing_fields']=common_equal(row['old_prediction'],row['new_prediction']) and common_equal(old_replay,new_replay)
                assert row['unchanged_existing_fields'],name
            if name in ['late_outcome_conflict','late_before_conflict','superseded_outcome','unrelated_conflict','future_conflict']:
                row['past_unchanged']=common_equal(old.forecast(['study'],p['past_as_of']),new.forecast(['study'],p['past_as_of']))
                assert row['past_unchanged'],name
        results.append(row)
    report={'phase':phase,'protocol_sha256':sha256(protocol_data).hexdigest(),'runtime':{'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__},'cases':results,'synthetic_only':True,'personal_benefit_measured':False}
    if phase == 'candidate':
        report['source_sha256'] = {
            str(path.relative_to(ROOT / 'src')): sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / 'src/qone_core/life').glob('*.py'))
        }
    write(ARTIFACT/(phase+'.json'),report)
    print(json.dumps({'phase':phase,'cases':len(results),'selection_matching_cases':sum(r['selection_matches'] for r in results),'protocol_sha256':report['protocol_sha256']}))

if __name__=='__main__':
    parser=ArgumentParser(); parser.add_argument('--phase',choices=['baseline','candidate'],required=True)
    evaluate(parser.parse_args().phase)
