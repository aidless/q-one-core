"""Deterministic synthetic engineering fixture. Never personal evidence."""
import json
import hashlib
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def fixture(seed=17, count=96):
    rng=random.Random(seed)
    dims=[{'id':key,'name':name} for key,name in [('physical','身体与恢复'),('learning','学习与能力'),('work','工作与创造'),('material','物质与资源'),('relations','关系与支持'),('environment','环境与生活条件'),('agency','自主与意义'),('recreation','休闲与体验')]]
    measures=[{'id':key,'name':name,'definition':definition,'dimension_id':dim,'scale':'ratio','unit':unit,'freshness_days':7,'persistence':'hold'} for key,name,definition,dim,unit in [
        ('energy','可用专注时长','当天记录可持续专注的分钟数','physical','分钟'),
        ('practice','独立验收练习','通过事前验收标准的练习条数','learning','条'),
        ('work','已验收产出','按固定口径验收的产出条数','work','条')]]
    measures += [{'id':'support','name':'可获得支持','definition':'用户选择的支持类别，不对类别做加减','dimension_id':'relations','scale':'ordinal','unit':'类别','categories':['暂不可获得','需预约','可及时获得'],'freshness_days':30},
                 {'id':'meaning','name':'当前重视的事情','definition':'保留用户原话，不强制打分','dimension_id':'agency','scale':'qualitative','unit':'原话','freshness_days':30}]
    observations=[]; episodes=[]
    def obs(key,mid,value,at):
        observations.append({'id':key,'measure_id':mid,'value':value,'observed_at':at.isoformat(),'recorded_at':at.isoformat(),'source_kind':'user_report','source':'SYNTHETIC fixture; not a real person'})
        return key
    for i in range(count):
        start=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=i*2)
        end=start+timedelta(days=1)
        energy=rng.uniform(45,85); actions=[a for bit,a in enumerate(['study','build']) if i%4 & (1<<bit)]
        before={mid:obs(f'e{i}-before-{mid}',mid,v,start) for mid,v in [('energy',energy),('practice',50),('work',40)]}
        delta_practice=12*('study' in actions)-4*('build' in actions)+0.04*(energy-60)*('study' in actions)+rng.gauss(0,0.6)
        delta_work=8*('build' in actions)+1*('study' in actions)+rng.gauss(0,0.5)
        after={mid:obs(f'e{i}-after-{mid}',mid,v,end) for mid,v in [('practice',50+delta_practice),('work',40+delta_work)]}
        episodes.append({'id':f'e{i}','started_at':start.isoformat(),'ended_at':end.isoformat(),'recorded_at':end.isoformat(),'action_ids':actions,'before':before,'after':after,'source':'SYNTHETIC assigned action; seed='+str(seed)})
    at=datetime(2026,10,25,tzinfo=timezone.utc)
    for mid,v in [('energy',60),('practice',50),('work',40),('support','需预约'),('meaning','想把时间花在能积累的事情上')]: obs('current-'+mid,mid,v,at)
    goals=[{'id':key,'title':title,'dimension_id':dim,'success_criterion':criterion,'value_ids':['growth'],'conditions':[{'measure_id':mid,'op':'gte','target':target}]} for key,title,dim,criterion,mid,target in [('learn','积累已验收练习','learning','独立验收练习累计到70条','practice',70),('deliver','完成可验收产出','work','已验收产出累计到55条','work',55)]]
    actions=[{'id':key,'title':title,'first_step':first,'done_when':done,'minutes':minutes,'goal_ids':[goal],'depends_on':[],'costs':[{'resource_id':'time','unit':'分钟','amount':minutes}],'effects':[]} for key,title,first,done,minutes,goal in [
        ('study','完成一轮定向练习','打开固定练习清单，先做一题','按同一验收标准记录通过的条数',45,'learn'),
        ('build','完成一轮交付','打开当前交付物，定位一处未验收内容','保存产出并记录验收结果',90,'deliver')]]
    for episode in episodes:
        executed=[next(a for a in actions if a['id']==aid) for aid in sorted(episode['action_ids'])]
        episode['action_definition_sha256']=hashlib.sha256(json.dumps(executed,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return {'schema_version':1,'title':'合成示例：学习、交付与时间取舍','synthetic':True,'dimensions':dims,
        'values':[{'id':'growth','statement':'本示例优先考虑能力积累，其次交付','declared_by':'user'}],
        'measures':measures,'observations':observations,'resources':[{'id':'time','name':'当天可安排时间','unit':'分钟','budget':60,'valid_from':at.isoformat(),'valid_until':(at+timedelta(days=1)).isoformat()}],
        'goals':goals,'goal_order':['learn','deliver'],'hypotheses':[],'actions':actions,'guardrails':[],
        'learning':{'horizon_days':1,'context_features':[{'measure_id':'energy','unit':'分钟','center':60,'scale':20}],
                    'targets':[{'measure_id':mid,'unit':'条','scale':10} for mid in ['practice','work']],
                    'action_ids':['study','build'],'min_samples':20,'min_portfolio_samples':3,'predictive_mass':0.9},'episodes':episodes}


if __name__=='__main__':
    path=Path(__file__).with_name('adaptive.synthetic.json')
    path.write_text(json.dumps(fixture(),ensure_ascii=False,indent=2)+'\n')
    print(path)
