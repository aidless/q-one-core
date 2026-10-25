"""Frozen synthetic comparison of interval calibration, with negative scenarios."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import runpy
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qone_core.life import AdaptiveKernel
from qone_core.life.model import fingerprint

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/calibration-evaluation/v1'


def scenario(seed,mode,count,shift_at):
    fixture=runpy.run_path(str(ROOT/'examples/generate_adaptive_fixture.py'))['fixture']
    model=fixture(seed=seed,count=count)
    rng=random.Random(seed+10000)
    obs={o['id']:o for o in model['observations']}
    for i,e in enumerate(model['episodes']):
        if i<shift_at: continue
        for mid,oid in e['after'].items():
            if mode=='mean_shift': obs[oid]['value']+=6 if mid=='practice' else -4
            elif mode=='noise_shift': obs[oid]['value']+=rng.gauss(0,4)
    return model


def main():
    protocol=json.loads((ART/'protocol.json').read_text())
    protocol_sha=sha256((ART/'protocol.json').read_bytes()).hexdigest()
    summaries=[]; inputs=[]; raw_lines=[]
    for seed in protocol['seeds']:
        for mode in protocol['scenarios']:
            model=scenario(seed,mode,protocol['episodes'],protocol['shift_at_episode'])
            inputs.append({'seed':seed,'scenario':mode,'model_sha256':fingerprint(model)})
            reports={}
            # The point model is identical across methods. Cache reuse changes no data.
            base=AdaptiveKernel(model); raw_cache=base._raw_replay()
            for method,config in protocol['methods'].items():
                configured=deepcopy(model)
                if config is not None: configured['learning']['calibration']=config
                k=base if config is None else AdaptiveKernel(configured)
                k._raw_cache=raw_cache
                reports[method]=k.replay()
            indexed={name:{(r['episode_id'],r['measure_id']):r for r in report['rows']} for name,report in reports.items()}
            for method,rows in indexed.items():
                for mid in ['practice','work']:
                    keys=[(f'e{i}',mid) for i in range(protocol['evaluation_start_episode'],protocol['episodes'])]
                    selected=[rows[key] for key in keys]
                    finite=[r for r in selected if r['predictive_width'] is not None]
                    baseline=[indexed['student_t'][(r['episode_id'],mid)] for r in finite]
                    summary={'seed':seed,'scenario':mode,'method':method,'measure_id':mid,'unit':'条','n':len(selected),'finite_n':len(finite),
                             'finite_rate':len(finite)/len(selected),'point_max_difference':max(abs(r['predicted_delta']-indexed['student_t'][key]['predicted_delta']) for key,r in zip(keys,selected))}
                    if finite:
                        summary.update(coverage=sum(r['interval_contains_observation'] for r in finite)/len(finite),
                          mean_width=sum(r['predictive_width'] for r in finite)/len(finite),
                          mean_interval_score=sum(r['interval_score'] for r in finite)/len(finite),
                          paired_baseline_coverage=sum(r['interval_contains_observation'] for r in baseline)/len(baseline),
                          paired_baseline_width=sum(r['predictive_width'] for r in baseline)/len(baseline),
                          paired_baseline_interval_score=sum(r['interval_score'] for r in baseline)/len(baseline))
                    gate=protocol['default_adoption_gate']
                    summary['gate']={'enough_finite':summary['finite_rate']>=gate['finite_interval_rate_at_least'],
                         'coverage':bool(finite) and summary['coverage']>=gate['observed_coverage_at_least'],
                         'score':bool(finite) and summary['mean_interval_score']<=summary['paired_baseline_interval_score'],
                         'point_unchanged':summary['point_max_difference']==0}
                    summary['passes']=all(summary['gate'].values());summaries.append(summary)
                    for row in selected:
                        receipt=row.get('calibration') or {}
                        raw_lines.append({'seed':seed,'scenario':mode,'method':method,**{key:row[key] for key in ['episode_id','measure_id','training_n','actual_delta','predicted_delta','lower','upper','predictive_width','interval_contains_observation','interval_score']},
                                          'calibration_status':receipt.get('status'),'calibration_n':receipt.get('calibration_n'),'adjusted_alpha':receipt.get('adjusted_alpha'),'last_score_recorded_at':receipt.get('last_score_recorded_at')})
    eligibility={method:all(s['passes'] for s in summaries if s['method']==method) for method in ['rolling','aci']}
    report={'schema_version':1,'protocol_sha256':protocol_sha,'synthetic':True,'results':summaries,'default_eligible':eligibility,
            'inputs':inputs,'runtime':{'python':platform.python_version()},'claims_excluded':['real_person_benefit','policy_value','causality','distribution_free_coverage']}
    import numpy,scipy
    report['runtime'].update(numpy=numpy.__version__,scipy=scipy.__version__)
    (ART/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (ART/'predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n' for r in raw_lines))
    print(json.dumps({'default_eligible':eligibility,'case_count':len(summaries),'rows':len(raw_lines),'results':str(ART/'results.json')},ensure_ascii=False))


if __name__=='__main__':main()
