"""Reproducible synthetic replay. Does not estimate personal or policy benefit."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qone_core.life import AdaptiveKernel


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='docs/evidence/adaptive-synthetic.json'); args=parser.parse_args()
    fixture=runpy.run_path(str(root/'examples/generate_adaptive_fixture.py'))['fixture']
    runs=[]
    for seed in (17,29,41):
        model=fixture(seed=seed,count=96); k=AdaptiveKernel(model)
        report=k.replay(); comparison=k.propose('2026-10-25T00:00:00Z',horizon_days=1)
        report.update(seed=seed,synthetic=True,comparison={key:comparison[key] for key in ('choice_status','preferred_id','frontier_ids')})
        runs.append(report)
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'src/qone_core/life').glob('*.py'))}
    import numpy,scipy
    result={'schema_version':1,'synthetic':True,'created_for':'2026-10-25','runs':runs,'source_sha256':sources,
            'runtime':{'python':sys.version.split()[0],'numpy':numpy.__version__,'scipy':scipy.__version__},
            'claims_excluded':['real_person_benefit','causal_effect','policy_value','joint_or_distribution_free_coverage','frontier_model_replication']}
    output=root/args.output; output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(output),'runs':[{'seed':r['seed'],'summary':r['summary'],'choice':r['comparison']['choice_status']} for r in runs]},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
