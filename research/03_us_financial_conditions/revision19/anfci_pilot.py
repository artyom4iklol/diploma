"""Offline ANFCI extension. All European inputs/targets remain frozen at revision18."""
from pathlib import Path
import sys,json,hashlib,platform
import numpy as np,pandas as pd,scipy
from scipy.stats import norm

P=Path(__file__).resolve().parent;ROOT=P.parent;O=P/'results';S=P/'sources'
sys.path.insert(0,str(ROOT/'revision18'))
from fit_pilot import fit,loss,hac
MODELS={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],'AR_ESI_NFCI':['gx','esi','nfci'],'AR_ESI_ANFCI':['gx','esi','anfci']}
PAIRS=[('AR_ESI_ANFCI','AR_ESI_NFCI'),('AR_ESI_ANFCI','AR_ESI'),('AR_ESI_ANFCI','HIST')]

def read_weekly(path,series=None,vintage=None):
 a=pd.read_csv(path)
 if series and vintage:
  assert a.columns[1].startswith(series+'_'),(path,a.columns.tolist())
  returned_vintage=pd.to_datetime(a.columns[1].split('_')[-1],format='%Y%m%d')
  # ALFRED may label the latest available release rather than a later requested day.
  assert returned_vintage<=pd.Timestamp(vintage),(path,returned_vintage,vintage)
 n=pd.Series(pd.to_numeric(a.iloc[:,1],errors='coerce').to_numpy(),index=pd.to_datetime(a.iloc[:,0])).dropna().sort_index()
 assert len(n)>500 and not n.index.duplicated().any()
 if vintage:assert n.index.max()<=pd.Timestamp(vintage)
 return n

def aggregate(n,quarters,origin):
 # Same rule as revision18.feature_frame, including seven-day buffer per quarter.
 return pd.Series({q:float(n[(n.index>=q.start_time)&(n.index+pd.Timedelta(days=7)<=q.end_time)].mean()) for q in quarters if q<=origin}).reindex(quarters)

def frames():
 O.mkdir(exist_ok=True)
 a=pd.read_csv(ROOT/'revision18/results/vintaged_model_frames.csv');a['q']=pd.PeriodIndex(a.quarter,freq='Q')
 manifest=json.loads((S/'anfci_vintages/manifest.json').read_text());assert len(manifest)==59
 for m in manifest:
  p=S/m['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
 new_nfci=read_weekly(S/'current/nfci_2026-10-16.csv','NFCI','2026-10-16')
 new_anfci=read_weekly(S/'current/anfci_2026-10-16.csv','ANFCI','2026-10-16')
 merged=[];calendar=[];aggregation_checks=[]
 cal=pd.read_csv(ROOT/'revision18/results/forecast_calendar_59.csv')
 for row in cal.itertuples():
  t=pd.Period(row.origin);v=a[a.origin.eq(row.origin)].copy().set_index('q');qs=v.index
  af=read_weekly(S/'anfci_vintages'/('anfci_'+row.nfci_vintage+'.csv'),'ANFCI',row.nfci_vintage)
  nf=read_weekly(ROOT/'revision16/sources/nfci_vintages'/('nfci_'+row.nfci_vintage+'.csv'),'NFCI',row.nfci_vintage)
  assert ((af.index+pd.Timedelta(days=7)<=t.end_time)&(af.index>=t.start_time)).any()
  v['anfci']=aggregate(af,qs,t);v['nfci_revised_20261016']=aggregate(new_nfci,qs,t);v['anfci_revised_20261016']=aggregate(new_anfci,qs,t)
  check=aggregate(nf,qs,t);dif=float((check-v.nfci).abs().max());assert dif<1e-12
  aggregation_checks.append(dict(origin=row.origin,nfci_aggregation_max_difference=dif))
  ix=af[(af.index>=t.start_time)&(af.index+pd.Timedelta(days=7)<=t.end_time)].index
  assert v.loc[t,['gx','esi','nfci','anfci']].notna().all()
  calendar.append(dict(origin=row.origin,forecast_date=row.forecast_date,anfci_vintage=row.nfci_vintage,last_anfci_observation_used=str(ix.max().date()),anfci=v.at[t,'anfci'],nfci=v.at[t,'nfci'],weekly_values_used=len(ix),conservative_method_period='through_2017' if t<pd.Period('2018Q1') else '2018_onward'))
  merged.append(v.reset_index(drop=True))
 d=pd.concat(merged,ignore_index=True);d.to_csv(O/'vintaged_model_frames_ANFCI.csv',index=False)
 pd.DataFrame(calendar).to_csv(O/'ANFCI_calendar_59.csv',index=False)
 pd.DataFrame(aggregation_checks).to_csv(O/'NFCI_aggregation_crosscheck.csv',index=False)
 # A future observation must not enter an earlier quarter aggregate.
 t=pd.Period('2018Q4');qs=pd.period_range('1995Q1','2025Q4',freq='Q')
 before=aggregate(new_anfci,qs,t);changed=new_anfci.copy();changed.loc[changed.index>t.end_time]=123456.
 after=aggregate(changed,qs,t);assert (before.dropna()-after.dropna()).abs().max()==0
 return d

def run():
 allv=frames();allv['q']=pd.PeriodIndex(allv.quarter,freq='Q')
 targets=pd.read_csv(ROOT/'revision18/results/evaluation_targets.csv')
 records=[];coefs=[];checks=[];cutoffs=[]
 for variant in ['expanding','rolling52','no_covid_training']:
  for info in ['historical','revised_financial_counterfactual_20261016']:
   for h in [1,4]:
    for trgt in targets[targets.h.eq(h)].itertuples():
     t=pd.Period(trgt.origin);v=allv[allv.origin.eq(trgt.origin)].copy().set_index('q');v['target']=v['y'+str(h)]
     if info!='historical':
      v['nfci']=v.nfci_revised_20261016;v['anfci']=v.anfci_revised_20261016
     mask=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)&v[['target','gx','esi','nfci','anfci']].notna().all(axis=1)
     if variant=='no_covid_training':mask&=~((v.index+1<=pd.Period('2021Q4'))&(v.index+h>=pd.Period('2020Q1')))
     train=v[mask]
     if variant=='rolling52':train=train.iloc[-52:];assert len(train)==52
     assert len(train)>=40 and train.index.max()+h<=t-1
     row=v.loc[t]
     episode='pre2020' if t+h<pd.Period('2020Q1') else '2022_2025' if t+1>=pd.Period('2022Q1') else 'covid_overlap'
     for model,cols in MODELS.items():
      if info!='historical' and model not in ['AR_ESI_NFCI','AR_ESI_ANFCI']:continue
      pred,b,qc=fit(train,row,cols)
      rec=dict(variant=variant,information=info,h=h,origin=str(t),forecast_date=str(t.end_time.normalize().date()+pd.Timedelta(days=15)),target_end=str(t+h),episode=episode,model=model,n_train=len(train),last_training_target=str(train.index.max()+h),actual=trgt.actual,actual_latest=trgt.actual_latest,forecast=pred,loss=float(loss(trgt.actual-pred)),loss_latest=float(loss(trgt.actual_latest-pred)),hit=int(trgt.actual<pred),hit_latest=int(trgt.actual_latest<pred),**qc)
      records.append(rec);coefs.append({k:rec[k] for k in ['variant','information','h','origin','model']}|b)
      if info=='historical' and variant=='expanding' and model=='AR_ESI_ANFCI' and trgt.origin in ['2011Q2','2017Q3','2020Q4','2023Q1','2025Q3']:
       p2,b2,q2=fit(train,row,cols,'highs-ipm');assert abs(qc['objective']-q2['objective'])<1e-6 and abs(pred-p2)<1e-6
       checks.append(dict(h=h,origin=str(t),objective_difference=qc['objective']-q2['objective'],forecast_difference=pred-p2))
     if info=='historical':cutoffs.append(dict(variant=variant,h=h,origin=str(t),n_train=len(train),last_training_target=str(train.index.max()+h),maximum_allowed=str(t-1)))
  print(variant,'complete',flush=True)
 f=pd.DataFrame(records);assert len(f)==2373
 f.to_csv(O/'ANFCI_forecasts.csv',index=False);pd.DataFrame(coefs).to_csv(O/'ANFCI_coefficients.csv',index=False);pd.DataFrame(cutoffs).to_csv(O/'ANFCI_training_checks.csv',index=False)
 scores=f.groupby(['variant','information','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),mean_loss_latest=('loss_latest','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).reset_index()
 for (variant,h),g in scores[scores.information.eq('historical')].groupby(['variant','h']):
  for b in ['HIST','AR','AR_ESI','AR_ESI_NFCI']:
   den=float(g[g.model.eq(b)].mean_loss.iloc[0]);idx=scores.index[scores.variant.eq(variant)&scores.h.eq(h)];scores.loc[idx,'ratio_'+b]=scores.loc[idx,'mean_loss']/den
 scores.to_csv(O/'ANFCI_scores.csv',index=False)
 hist=f[f.information.eq('historical')];compare=[];influence=[];tests=[];subset=[];revisions=[]
 for (variant,h),g in hist.groupby(['variant','h']):
  w=g.pivot(index='origin',columns='model',values='loss').sort_index()
  for a,b in PAIRS:
   da=w[a].to_numpy();db=w[b].to_numpy();diff=da-db;gain=db-da
   compare.append(dict(variant=variant,h=h,comparison=a+'/'+b,n=len(w),ratio=da.mean()/db.mean(),difference=diff.mean()))
   for i,origin in enumerate(w.index):influence.append(dict(variant=variant,h=h,comparison=a+'/'+b,omitted_origin=origin,ratio_without=(da.sum()-da[i])/(db.sum()-db[i]),gain_at_origin=gain[i],share_of_net_gain=gain[i]/gain.sum() if abs(gain.sum())>1e-12 else np.nan))
   if variant=='rolling52':
    for L in [4,8]:
     se=float(hac(diff,L));z=float(diff.mean()/se);pval=float(2*norm.sf(abs(z)))
     tests.append(dict(variant=variant,h=h,comparison=a+'/'+b,n=len(w),L=L,difference=diff.mean(),se=se,z=z,p_two_sided=pval,lo=diff.mean()-1.96*se,hi=diff.mean()+1.96*se))
  for name,selection in [
   ('origin_2018Q1_onward',g.origin.ge('2018Q1')),
   ('all_four_repairs_omitted',~g.origin.isin(['2022Q2','2023Q1','2023Q2','2025Q3'])),
   ('ESI_gap_2023_omitted',~g.origin.isin(['2023Q1','2023Q2']))]:
   for model,gg in g[selection].groupby('model'):subset.append(dict(variant=variant,h=h,subset=name,model=model,n=len(gg),mean_loss=gg.loss.mean(),hit_rate=gg.hit.mean()))
  for m in ['AR_ESI_NFCI','AR_ESI_ANFCI']:
   a=g[g.model.eq(m)].sort_values('origin');b=f[(f.variant.eq(variant))&f.h.eq(h)&f.model.eq(m)&f.information.ne('historical')].sort_values('origin')
   assert list(a.origin)==list(b.origin)
   revisions.append(dict(variant=variant,h=h,model=m,n=len(a),loss_historical=a.loss.mean(),loss_revised=b.loss.mean(),ratio_historical_to_revised=a.loss.mean()/b.loss.mean(),mean_absolute_forecast_difference=float(np.abs(a.forecast.to_numpy()-b.forecast.to_numpy()).mean())))
 tt=pd.DataFrame(tests)
 for L in [4,8]:
  ids=tt.query('h==1 and L==@L').sort_values('p_two_sided').index;running=0.
  for rank,i in enumerate(ids):running=max(running,(len(ids)-rank)*tt.at[i,'p_two_sided']);tt.at[i,'holm3_new_primary_h1']=min(1.,running)
 pd.DataFrame(compare).to_csv(O/'ANFCI_comparisons.csv',index=False);pd.DataFrame(influence).to_csv(O/'ANFCI_single_date_influence.csv',index=False);pd.DataFrame(subset).to_csv(O/'ANFCI_subsets.csv',index=False);tt.to_csv(O/'ANFCI_GW_rolling52.csv',index=False);pd.DataFrame(revisions).to_csv(O/'ANFCI_revision_effect.csv',index=False)
 hist.groupby(['variant','h','episode','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(O/'ANFCI_episode_scores.csv')
 old=pd.read_csv(ROOT/'revision18/results/pilot_forecasts.csv');old=old[old.information.eq('historical_NFCI')].drop(columns='information')
 common=hist[~hist.model.eq('AR_ESI_ANFCI')].drop(columns='information')
 key=['variant','h','origin','model'];j=old.merge(common,on=key,validate='one_to_one',suffixes=('_old','_new'))
 assert len(j)==1356
 cross={c:float((j[c+'_old']-j[c+'_new']).abs().max()) for c in ['forecast','loss','actual','n_train']}
 assert max(cross.values())<1e-10,cross
 # Deliberately perturb target labels that are not yet eligible for training.
 t=pd.Period('2018Q4');v=allv[allv.origin.eq(str(t))].copy().set_index('q');mutation=[]
 for h in [1,4]:
  v['target']=v['y'+str(h)];mask=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)&v[['target','gx','esi','nfci','anfci']].notna().all(axis=1)
  before=fit(v[mask],v.loc[t],MODELS['AR_ESI_ANFCI'])[0];u=v.copy();u.loc[u.index+h>t-1,'target']=123456.;after=fit(u[mask],u.loc[t],MODELS['AR_ESI_ANFCI'])[0];assert abs(after-before)<1e-12
  mutation.append(dict(h=h,prediction_difference=after-before))
 validation=dict(forecasts=len(f),historical_forecasts=len(hist),paired_revised_counterfactual_forecasts=int(f.information.ne('historical').sum()),historical_versions=59,common_rows_and_origins=True,baseline_reproduction_rows=len(j),baseline_maximum_differences=cross,solver_checks=checks,future_label_mutation=mutation,maximum_condition=float(f.condition.max()),all_forecasts_finite=bool(np.isfinite(f[['actual','forecast','loss']].to_numpy()).all()),versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__),formal_causal_identification=False,complete_reconstruction_of_market_information=False)
 assert validation['all_forecasts_finite']
 (O/'ANFCI_validation.json').write_text(json.dumps(validation,indent=2))
 print(scores.query("variant=='expanding' and information=='historical'").to_string(index=False));print(tt.query('h==1 and L==4').to_string(index=False));print(json.dumps(validation,indent=2))

if __name__=='__main__':run()
