"""Fixed eight-model extension; no search over indicators, periods, or hyperparameters."""
from pathlib import Path
import sys,json,hashlib,platform
import pandas as pd,numpy as np,scipy
P=Path(__file__).resolve().parent;R=P.parent;O=P/'results'
sys.path.insert(0,str(R/'revision18'));from fit_pilot import fit,loss
M={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],'AR_ESI_NFCI':['gx','esi','nfci'],'AR_ESI_ANFCI':['gx','esi','anfci'],'AR_ESI_EQ':['gx','esi','eq'],'AR_ESI_EQ_NFCI':['gx','esi','eq','nfci'],'AR_ESI_EQ_ANFCI':['gx','esi','eq','anfci']}
REPAIR_ORIGINS=['2020Q2','2021Q1','2022Q2']
def run():
 lock=json.loads((P/'protocol_lock.json').read_text());assert hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()==lock['sha256']
 a=pd.read_csv(R/'revision19/results/vintaged_model_frames_ANFCI.csv').merge(pd.read_csv(O/'equity_frames.csv'),on=['origin','quarter'],validate='one_to_one');a['q']=pd.PeriodIndex(a.quarter,freq='Q');a.to_csv(O/'equity_model_frames.csv',index=False)
 targets=pd.read_csv(R/'revision18/results/evaluation_targets.csv');cal=pd.read_csv(O/'equity_calendar.csv');good=set(cal.loc[cal.available,'origin']);preds=[];coef=[];checks=[];trcheck=[];mutations=[]
 for h in [1,4]:
  for target in targets[targets.h.eq(h)&targets.origin.isin(good)].itertuples():
   t=pd.Period(target.origin,freq='Q');v=a[a.origin.eq(target.origin)].copy().set_index('q');v['target']=v['y'+str(h)];elig=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)
   oldmask=elig&v[['target','gx','esi','nfci','anfci']].notna().all(axis=1);mask=oldmask&v['eq'].notna();tr=v[mask];row=v.loc[t];assert len(tr)>=40 and row[['gx','esi','nfci','anfci','eq']].notna().all()
   assert tr.index.max()+h<=t-1;clip=float(np.clip(row.gx,tr.gx.min(),tr.gx.max()));same=bool(np.array_equal(mask,oldmask))
   trcheck.append(dict(h=h,origin=str(t),n_train=len(tr),old_n_train=int(oldmask.sum()),same_as_original_training=same,last_target=str(tr.index.max()+h),last_allowed=str(t-1),training_rows=';'.join(map(str,tr.index))))
   for model,cols in M.items():
    pr,b,qc=fit(tr,row,cols);assert abs(pr-b['const']-sum(b[k]*row[k] for k in cols))<1e-8
    coef.append(dict(h=h,origin=str(t),model=model,**b,**qc))
    if model in ['AR_ESI_EQ','AR_ESI_EQ_NFCI','AR_ESI_EQ_ANFCI'] and str(t) in ['2011Q2','2020Q4','2024Q4']:
     p2,b2,q2=fit(tr,row,cols,'highs-ipm');assert abs(qc['objective']-q2['objective'])<1e-6
     checks.append(dict(h=h,origin=str(t),model=model,objective_difference=qc['objective']-q2['objective'],forecast_difference=pr-p2))
    for guard in ['raw','clip_g']:
     pr2=pr if guard=='raw' else pr+b.get('gx',0.)*(clip-row.gx)
     preds.append(dict(variant='expanding',guard=guard,h=h,origin=str(t),forecast_date=str((t.end_time.normalize()+pd.Timedelta(days=15)).date()),model=model,n_train=len(tr),actual=float(target.actual),forecast=pr2,loss=float(loss(target.actual-pr2)),hit=int(target.actual<pr2),same_as_original_training=same))
   if str(t)=='2018Q4':
    cols=M['AR_ESI_EQ_ANFCI'];before=fit(tr,row,cols)[0];v.loc[v.index+h>t-1,'target']=123456.;after=fit(v[mask],row,cols)[0];assert abs(after-before)<1e-12;mutations.append(dict(h=h,forecast_difference=after-before))
  print('h',h,'complete',flush=True)
 f=pd.DataFrame(preds);assert not f.duplicated(['guard','h','origin','model']).any();assert np.isfinite(f[['loss','forecast','actual']]).all().all()
 f.to_csv(O/'equity_forecasts.csv',index=False);pd.DataFrame(coef).to_csv(O/'equity_coefficients.csv',index=False);pd.DataFrame(trcheck).to_csv(O/'equity_training_checks.csv',index=False)
 old=pd.read_csv(R/'revision25/results/forecasts.csv');old=old[(old.variant=='expanding')&old.config.isin(['Q_raw','Q_clip_g'])].copy();old['guard']=old.config.str.replace('Q_','',regex=False)
 j=f[f.same_as_original_training].merge(old,on=['guard','h','origin','model'],suffixes=('_new','_old'),validate='one_to_one');diff={k:float((j[k+'_new']-j[k+'_old']).abs().max()) for k in ['forecast','loss','actual','n_train']};assert max(diff.values())<1e-8,diff
 scores=[]
 for name,exclude in [('all',[]),('omit_2020Q4',['2020Q4']),('omit_repaired_origins',REPAIR_ORIGINS)]:
  z=f[~f.origin.isin(exclude)].groupby(['guard','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).reset_index();z['sample']=name
  for (g,h),b in z.groupby(['guard','h']):
   for bm in ['HIST','AR_ESI','AR_ESI_EQ']:
    den=float(b[b.model.eq(bm)].mean_loss.iloc[0]);z.loc[b.index,'ratio_'+bm]=b.mean_loss/den
  scores.append(z)
 scores=pd.concat(scores);scores.to_csv(O/'equity_scores.csv',index=False)
 comps=[]
 for (guard,h),g in f.groupby(['guard','h']):
  w=g.pivot(index='origin',columns='model',values='loss').sort_index()
  for m in ['AR_ESI_EQ_NFCI','AR_ESI_EQ_ANFCI']:
   for bm in ['AR_ESI_EQ','HIST']:
    d=w[m]-w[bm];wo=(d.sum()-d)/(len(d)-1)
    comps.append(dict(guard=guard,h=h,model=m,benchmark=bm,n=len(d),difference=float(d.mean()),ratio=float(w[m].mean()/w[bm].mean()),date_wins=int((d<0).sum()),difference_omit_2020Q4=float(wo.loc['2020Q4']),negative_after_each_single_omission=int((wo<0).sum()),min_omission_difference=float(wo.min()),max_omission_difference=float(wo.max())))
 pd.DataFrame(comps).to_csv(O/'equity_comparisons.csv',index=False)
 validation=dict(forecasts=len(f),fitting_procedures=len(coef),regression_fits=sum(c['model']!='HIST' for c in coef),common_training_rows=True,common_evaluation_dates=True,training_n_min=int(f.n_train.min()),training_n_max=int(f.n_train.max()),old_forecasts_reproduced=len(j),baseline_max_differences=diff,changed_training_cases=sum(not r['same_as_original_training'] for r in trcheck),solver_checks=checks,future_label_mutations=mutations,protocol_sha256=lock['sha256'],new_p_values=False,versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__))
 (O/'equity_model_validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 print(scores.query("sample=='all' and guard=='raw'").to_string(index=False));print('validation:',len(f),'forecasts,',len(j),'old forecasts reproduced; changed training',validation['changed_training_cases'])
if __name__=='__main__':run()
