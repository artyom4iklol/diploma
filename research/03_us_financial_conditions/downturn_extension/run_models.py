"""Frozen, matched-sample recursive contraction-probability experiments."""
from pathlib import Path
import json,hashlib,copy
import numpy as np,pandas as pd
from logit_engine import fit,predict,metrics
P=Path(__file__).resolve().parent;R=P.parent;OUT=P/'results'

def load_spec():
 b=(P/'protocol_lock.json').read_bytes();assert hashlib.sha256(b).hexdigest()==(P/'protocol_lock.sha256').read_text().strip()
 return json.loads(b)

def prepare_frame(panel,case):
 d=panel.copy();growth='growth_exIreland' if case.get('gdp')=='exIreland' else 'growth'
 if case.get('gdp')=='exIreland':d['gdp_lag']=d[growth].shift(1)
 if case.get('financial_lag')==0:
  for c in ['eu_curve','credit','us_curve','esi','equity','vix','ciss','nfci','anfci']:d[c+'_lag']=d[c]
 if case.get('target')=='cepr':labels=d.cepr.astype(float)
 else:labels=d[growth].lt(case.get('threshold',0)).astype(float).where(d[growth].notna())
 return d,labels

def fit_origin(frame,features,y,current,mask):
 train=frame.loc[mask,features].to_numpy();target=y.loc[mask].to_numpy();predx=frame.loc[[current],features].to_numpy()
 m=fit(train,target);p=float(predict(m,predx)[0]);return p,m

def run_group(panel,spec,group,case=None,only_origins=None,save_artifacts=True):
 case=case or {};d,labels=prepare_frame(panel,case);modelcols={'FREQ':[],'EU':group['base']}
 modelcols.update({k:group['base']+v for k,v in group['additions'].items()});union=sorted(set(sum(modelcols.values(),[])))
 preds=[];coefs=[];calendar=[];start=pd.Period(case.get('start',group['start']));exp=case.get('name',group['name'])
 for h in spec['horizons']:
  y=labels.shift(-h)
  origins=pd.period_range(group.get('first_origin','2006Q4'),'2025Q4',freq='Q')
  if only_origins is not None:origins=pd.PeriodIndex(only_origins,freq='Q')
  for t in origins:
   if t+h>pd.Period('2025Q4') or t not in d.index:continue
   if not np.isfinite(d.loc[t,union].to_numpy(dtype=float)).all():raise ValueError(f'Predictor missing {exp} {t}')
   mask=(d.index>=start)&(d.index+h<=t-1)&d[union].notna().all(axis=1)&y.notna()
   ix=d.index[mask]
   if case.get('window'):
    ix=ix[-case['window']:];mask=d.index.isin(ix)
   yt=y.loc[mask];n=len(yt);pos=int(yt.sum())
   if n<spec['training_min_rows'] or min(pos,n-pos)<spec['training_min_each_class']:raise ValueError(f'Insufficient training {exp} {t} h={h} n={n}, positives={pos}')
   dates=';'.join(map(str,ix));trainhash=hashlib.sha256(dates.encode()).hexdigest()
   calendar.append({'experiment':exp,'h':h,'origin':str(t),'issue_date':str(t.end_time.date()),'target_quarter':str(t+h),'feature_max_quarter':str(t if case.get('financial_lag')==0 else t-1),'gdp_max_quarter':str(t-1),'last_training_origin':str(ix[-1]),'last_training_target':str(ix[-1]+h),'n_train':n,'train_events':pos,'training_hash':trainhash,'training_origins':dates})
   actual=float(labels.loc[t+h]);growth=d.loc[t+h,'growth_exIreland' if case.get('gdp')=='exIreland' else 'growth']
   for name,cols in modelcols.items():
    if name=='FREQ':p=(pos+.5)/(n+1);m=None
    else:p,m=fit_origin(d,cols,y,t,mask)
    row={'experiment':exp,'h':h,'origin':str(t),'issue_date':str(t.end_time.date()),'target_quarter':str(t+h),'model':name,'actual':actual,'probability':p,'growth_qoq_log':growth,'n_train':n,'train_events':pos,'training_hash':trainhash,'brier':(p-actual)**2,'log_loss':-(actual*np.log(np.clip(p,1e-12,1-1e-12))+(1-actual)*np.log(np.clip(1-p,1e-12,1))), 'alarm':int(p>=.2)}
    preds.append(row)
    if m:
     c={k:v for k,v in m.items() if k not in ['coef','firth_standardized','mean','scale']};c.update({'experiment':exp,'h':h,'origin':str(t),'model':name,'columns':['intercept']+cols,'coefficients':m['coef'].tolist(),'firth_standardized':m['firth_standardized'].tolist(),'training_mean':m['mean'].tolist(),'training_scale':m['scale'].tolist(),'training_hash':trainhash})
     coefs.append(c)
  print(f'{exp} h={h} finished',flush=True)
 return pd.DataFrame(preds),coefs,pd.DataFrame(calendar)

def archival(spec):
 allv=pd.read_csv(R/'revision30/results/equity_model_frames.csv');allv['q']=pd.PeriodIndex(allv.quarter,freq='Q');cal=pd.read_csv(R/'revision18/results/forecast_calendar_59.csv');eqcal=pd.read_csv(R/'revision30/results/equity_calendar.csv');targ=pd.read_csv(R/'revision18/results/evaluation_targets.csv');facts=targ[targ.h.eq(1)].set_index('target_end')
 preds=[];coefs=[];timing=[]
 for row in cal.itertuples():
  r=pd.Period(row.origin);date=pd.Timestamp(row.forecast_date);issueq=date.to_period('Q');assert issueq==r+1
  assert pd.Timestamp(row.gdp_public_available)<=date and pd.Timestamp(row.esi_public_available)<=date and pd.Timestamp(row.nfci_vintage)<=date
  eqr=eqcal[eqcal.origin.eq(row.origin)].iloc[0];assert pd.Timestamp(eqr.equity_public)<=date
  v=allv[allv.origin.eq(row.origin)].set_index('q').sort_index().copy()
  # y1[s] in the inherited cube is annualized one-quarter GDP growth at s+1 in this origin vintage.
  g1=(v.y1/4).shift(1)
  union=['gx','esi','eq','nfci','anfci','nfci_revised_20261016','anfci_revised_20261016']
  for h in spec['horizons']:
   goal=r+1+h
   if goal>pd.Period('2025Q4'):continue
   key=str(goal)
   if key not in facts.index:raise ValueError('Missing predetermined six-month-maturity target '+key)
   y=g1.shift(-(1+h)).lt(0).astype(float).where(g1.shift(-(1+h)).notna())
   mask=(v.index>=pd.Period('1995Q3'))&(v.index+1+h<=r-1)&v[union].notna().all(axis=1)&y.notna()
   ix=v.index[mask];yy=y.loc[mask];n=len(ix);pos=int(yy.sum());assert n>=40 and min(pos,n-pos)>=3
   training_hash=hashlib.sha256(';'.join(map(str,ix)).encode()).hexdigest();actual=float(facts.loc[key,'actual']<0);latest=float(facts.loc[key,'actual_latest']<0)
   for variant,fields in [('archive_vintage',('nfci','anfci')),('archive_late_index',('nfci_revised_20261016','anfci_revised_20261016'))]:
    timing.append({'experiment':variant,'h':h,'origin':str(issueq),'feature_origin':str(r),'issue_date':str(date.date()),'target_quarter':key,'feature_max_quarter':str(r),'gdp_max_quarter':str(r-1),'last_training_target':str(ix[-1]+1+h),'n_train':n,'train_events':pos,'training_hash':training_hash,'gdp_public':row.gdp_public_available,'esi_public':row.esi_public_available,'equity_public':eqr.equity_public,'fact_snapshot':facts.loc[key,'matured_snapshot'],'fact_public':facts.loc[key,'matured_public_date'],'late_index_note':'only the American index history is replaced; European vintages remain the same'})
    models={'FREQ':[],'EU':['gx','esi','eq'],'EU_NFCI':['gx','esi','eq',fields[0]],'EU_ANFCI':['gx','esi','eq',fields[1]]}
    for name,cols in models.items():
     if cols:p,m=fit_origin(v,cols,y,r,mask)
     else:p=(pos+.5)/(n+1);m=None
     preds.append({'experiment':variant,'h':h,'origin':str(issueq),'issue_date':str(date.date()),'target_quarter':key,'model':name,'actual':actual,'actual_latest':latest,'probability':p,'growth_qoq_log':float(facts.loc[key,'actual'])/4,'n_train':n,'train_events':pos,'training_hash':training_hash,'brier':(p-actual)**2,'log_loss':-(actual*np.log(np.clip(p,1e-12,1))+(1-actual)*np.log(np.clip(1-p,1e-12,1))),'alarm':int(p>=.2)})
     if m:
      c={k:vv for k,vv in m.items() if k not in ['coef','firth_standardized','mean','scale']};c.update({'experiment':variant,'h':h,'origin':str(issueq),'feature_origin':str(r),'model':name,'columns':['intercept']+cols,'coefficients':m['coef'].tolist(),'firth_standardized':m['firth_standardized'].tolist(),'training_mean':m['mean'].tolist(),'training_scale':m['scale'].tolist(),'training_hash':training_hash});coefs.append(c)
 print('Historical-vintage and matched late-index experiments finished',flush=True)
 return pd.DataFrame(preds),coefs,pd.DataFrame(timing)

def main():
 spec=load_spec();OUT.mkdir(exist_ok=True)
 # Verify all frozen raw/inherited inputs before fitting.
 for name,expected in spec['input_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==expected,name
 panel=pd.read_csv(P/'data/processed/quarterly_panel.csv',index_col=0);panel.index=pd.PeriodIndex(panel.index,freq='Q')
 allf=[];allc=[];allcal=[]
 for group in spec['experiments']:
  f,c,cal=run_group(panel,spec,group);allf.append(f);allc+=c;allcal.append(cal)
 for case in spec['refit_sensitivities']:
  f,c,cal=run_group(panel,spec,spec['experiments'][0],case);allf.append(f);allc+=c;allcal.append(cal)
 f,c,cal=archival(spec);allf.append(f);allc+=c;allcal.append(cal)
 forecasts=pd.concat(allf,ignore_index=True);forecasts.to_csv(OUT/'forecasts.csv',index=False)
 pd.concat(allcal,ignore_index=True).to_csv(OUT/'forecast_calendar.csv',index=False)
 with (OUT/'coefficients.jsonl').open('w') as out:
  for c in allc:out.write(json.dumps(c,ensure_ascii=False)+'\n')
 scores=[]
 for (e,h,m),v in forecasts.groupby(['experiment','h','model']):scores.append({'experiment':e,'h':h,'model':m,**metrics(v.actual,v.probability)})
 pd.DataFrame(scores).to_csv(OUT/'scores.csv',index=False)
 manifest={'protocol_sha256':(P/'protocol_lock.sha256').read_text().strip(),'forecasts':len(forecasts),'fits':len(allc),'experiments':sorted(forecasts.experiment.unique()),'maximum_score':max(c['score_max'] for c in allc),'maximum_training_calibration_error':max(abs(c['train_mean_probability']-c['train_event_rate']) for c in allc),'fallback_optimizers':sum(c['optimizer_fallback'] for c in allc),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}}
 manifest['implementation']={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['logit_engine.py','run_models.py','build_panel.py']}
 (P/'checks/model_run.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
