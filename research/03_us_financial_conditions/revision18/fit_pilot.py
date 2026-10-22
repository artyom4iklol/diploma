"""Reproducible offline four-model pilot; no network, no fitted-result selection."""
from pathlib import Path
import json,platform,hashlib
import numpy as np,pandas as pd,scipy
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
from scipy.stats import norm

P=Path(__file__).resolve().parent;O=P/'results'
TAU=.1
MODELS={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],'AR_ESI_NFCI':['gx','esi','nfci']}
REPAIRS=['2022Q2','2023Q1','2023Q2','2025Q3']

def loss(u):return np.maximum(TAU*u,(TAU-1)*u)

def fit(train,row,cols,method='highs'):
 y=train.target.to_numpy();n=len(y)
 if not cols:
  p=float(np.quantile(y,TAU,method='inverted_cdf'))
  return p,{'const':p},dict(objective=float(loss(y-p).sum()),rank=1,condition=1.0)
 mu=train[cols].mean().to_numpy();sd=train[cols].std(ddof=0).to_numpy();assert (sd>0).all()
 x=np.c_[np.ones(n),(train[cols].to_numpy()-mu)/sd];xp=np.r_[1,(row[cols].to_numpy(dtype=float)-mu)/sd];k=x.shape[1]
 opt=linprog(np.r_[np.zeros(k),np.full(n,TAU),np.full(n,1-TAU)],A_eq=hstack([csr_matrix(x),eye(n),-eye(n)],format='csr'),b_eq=y,bounds=[(None,None)]*k+[(0,None)]*(2*n),method=method)
 assert opt.success,opt.message
 beta=opt.x[:k];obj=float(loss(y-x@beta).sum());assert abs(obj-opt.fun)<1e-6
 rank=int(np.linalg.matrix_rank(x));assert rank==k
 b=dict(zip(['const']+cols,np.r_[beta[0]-(beta[1:]*mu/sd).sum(),beta[1:]/sd]))
 return float(xp@beta),b,dict(objective=obj,rank=rank,condition=float(np.linalg.cond(x)))

def hac(x,L):
 u=np.asarray(x)-np.mean(x);n=len(u);om=u@u/n+2*sum((1-k/(L+1))*(u[k:]@u[:-k])/n for k in range(1,min(n,L+1)))
 return np.sqrt(max(om,0)/n)

def run():
 allv=pd.read_csv(O/'vintaged_model_frames.csv');target=pd.read_csv(O/'evaluation_targets.csv');allv['q']=pd.PeriodIndex(allv.quarter,freq='Q')
 predictions=[];coefs=[];checks=[];trainchecks=[]
 for variant in ['expanding','rolling52','no_covid_training']:
  for info in ['historical_NFCI','revised_NFCI_counterfactual']:
   # Counterfactual is meaningful for the nested NFCI model only; shared baselines copied.
   for h in [1,4]:
    for trgt in target[target.h.eq(h)].itertuples():
     t=pd.Period(trgt.origin,freq='Q');v=allv[allv.origin.eq(trgt.origin)].copy().set_index('q');v['target']=v['y'+str(h)]
     if info=='revised_NFCI_counterfactual':v['nfci']=v.nfci_revised
     mask=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)&v[['target','gx','esi','nfci']].notna().all(axis=1)
     if variant=='no_covid_training':mask&=~((v.index+1<=pd.Period('2021Q4'))&(v.index+h>=pd.Period('2020Q1')))
     train=v[mask]
     if variant=='rolling52':train=train.iloc[-52:];assert len(train)==52
     assert len(train)>=40 and train.index.max()+h<=t-1
     row=v.loc[t];episode='pre2020' if t+h<pd.Period('2020Q1') else '2022_2025' if t+1>=pd.Period('2022Q1') else 'covid_overlap'
     for model,cols in MODELS.items():
      if info=='revised_NFCI_counterfactual' and model!='AR_ESI_NFCI':continue
      pred,b,chk=fit(train,row,cols)
      rec=dict(variant=variant,information=info,h=h,origin=trgt.origin,forecast_date=str(t.end_time.normalize().date()+pd.Timedelta(days=15)),target_end=str(t+h),episode=episode,model=model,n_train=len(train),last_training_target=str(train.index.max()+h),actual=trgt.actual,actual_latest=trgt.actual_latest,forecast=pred,loss=float(loss(trgt.actual-pred)),loss_latest=float(loss(trgt.actual_latest-pred)),hit=int(trgt.actual<pred),hit_latest=int(trgt.actual_latest<pred),**chk)
      predictions.append(rec);coefs.append({k:rec[k] for k in ['variant','information','h','origin','model']}|b)
      if info=='historical_NFCI' and variant=='expanding' and model=='AR_ESI_NFCI' and trgt.origin in ['2011Q2','2020Q4','2023Q1','2025Q3']:
       p2,b2,c2=fit(train,row,cols,'highs-ipm');assert abs(chk['objective']-c2['objective'])<1e-6
       checks.append(dict(h=h,origin=trgt.origin,objective_difference=chk['objective']-c2['objective'],forecast_difference=pred-p2))
     if info=='historical_NFCI':trainchecks.append(dict(variant=variant,h=h,origin=trgt.origin,n_train=len(train),last_training_target=str(train.index.max()+h),maximum_allowed=str(t-1),pass_no_current_or_future_GDP=True))
  print(variant,'complete',flush=True)
 f=pd.DataFrame(predictions);f.to_csv(O/'pilot_forecasts.csv',index=False);pd.DataFrame(coefs).to_csv(O/'pilot_coefficients.csv',index=False);pd.DataFrame(trainchecks).to_csv(O/'training_calendar_checks.csv',index=False)
 scores=f.groupby(['variant','information','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),mean_loss_latest=('loss_latest','mean'),hits=('hit','sum'),hit_rate=('hit','mean'),hit_rate_latest=('hit_latest','mean'),min_n_train=('n_train','min'),max_n_train=('n_train','max')).reset_index()
 for (variant,h),g in scores[scores.information.eq('historical_NFCI')].groupby(['variant','h']):
  for baseline in ['HIST','AR','AR_ESI']:
   den=float(g[g.model.eq(baseline)].mean_loss.iloc[0]);idx=scores.index[scores.variant.eq(variant)&scores.h.eq(h)];scores.loc[idx,'ratio_'+baseline]=scores.loc[idx,'mean_loss']/den
 scores.to_csv(O/'pilot_scores.csv',index=False)
 comparisons=[];influence=[];robust=[];tests=[];revisions=[]
 pairs=[('AR_ESI_NFCI','AR_ESI'),('AR_ESI_NFCI','HIST'),('AR_ESI_NFCI','AR')]
 for (variant,h),g in f[f.information.eq('historical_NFCI')].groupby(['variant','h']):
  w=g.pivot(index='origin',columns='model',values='loss').sort_index()
  for a,b in pairs:
   da=w[a].to_numpy();db=w[b].to_numpy();diff=da-db
   comparisons.append(dict(variant=variant,h=h,comparison=a+'/'+b,n=len(w),ratio=da.mean()/db.mean(),difference=diff.mean()))
   for i,t in enumerate(w.index):influence.append(dict(variant=variant,h=h,comparison=a+'/'+b,omitted_origin=t,ratio_without=(da.sum()-da[i])/(db.sum()-db[i]),gain_at_origin=db[i]-da[i],share_of_net_gain=(db[i]-da[i])/(db-da).sum() if abs((db-da).sum())>1e-12 else np.nan))
   if variant=='rolling52':
    for L in [4,8]:
     se=hac(diff,L);z=diff.mean()/se;pval=float(2*norm.sf(abs(z)))
     tests.append(dict(variant=variant,h=h,comparison=a+'/'+b,n=len(w),L=L,difference=diff.mean(),se=se,z=z,p_two_sided=pval,lo=diff.mean()-1.96*se,hi=diff.mean()+1.96*se,method='GW unconditional constant instrument; fixed rolling52; asymptotic Bartlett HAC; instability and revisions caveat'))
  for label,exclude in [('all_four_repairs',REPAIRS),('ESI_gap_2023',['2023Q1','2023Q2'])]:
   keep=g[~g.origin.isin(exclude)]
   for m,gg in keep.groupby('model'):robust.append(dict(variant=variant,h=h,omission=label,model=m,n=len(gg),mean_loss=gg.loss.mean(),hit_rate=gg.hit.mean()))
  subset=f[(f.variant.eq(variant))&f.h.eq(h)&f.information.eq('revised_NFCI_counterfactual')].sort_values('origin')
  actual_nfci=g[g.model.eq('AR_ESI_NFCI')].sort_values('origin')
  assert list(subset.origin)==list(actual_nfci.origin)
  revisions.append(dict(variant=variant,h=h,n=len(subset),loss_historical_NFCI=actual_nfci.loss.mean(),loss_revised_NFCI=subset.loss.mean(),ratio_historical_to_revised=actual_nfci.loss.mean()/subset.loss.mean(),mean_abs_forecast_difference=float((actual_nfci.forecast.to_numpy()-subset.forecast.to_numpy()).__abs__().mean()),max_abs_forecast_difference=float((actual_nfci.forecast.to_numpy()-subset.forecast.to_numpy()).__abs__().max())))
 tt=pd.DataFrame(tests)
 for L in [4,8]:
  ids=tt.query('h==1 and L==@L').sort_values('p_two_sided').index;running=0
  for rank,i in enumerate(ids):running=max(running,(len(ids)-rank)*tt.at[i,'p_two_sided']);tt.at[i,'holm3_primary_h1']=min(1.,running)
 pd.DataFrame(comparisons).to_csv(O/'pilot_comparisons.csv',index=False);pd.DataFrame(influence).to_csv(O/'pilot_single_date_influence.csv',index=False);pd.DataFrame(robust).to_csv(O/'pilot_repaired_dates_sensitivity.csv',index=False);tt.to_csv(O/'pilot_GW_rolling52.csv',index=False);pd.DataFrame(revisions).to_csv(O/'pilot_NFCI_revision_effect.csv',index=False)
 f[f.information.eq('historical_NFCI')].groupby(['variant','h','episode','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(O/'pilot_episode_scores.csv')
 # Target values used for scoring cannot affect predictions: fit only historical labels.
 mutations=[]
 for h in [1,4]:
  t=pd.Period('2018Q4');v=allv[allv.origin.eq(str(t))].set_index('q').copy();v['target']=v['y'+str(h)];mask=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)&v[['target','gx','esi','nfci']].notna().all(axis=1)
  before=fit(v[mask],v.loc[t],MODELS['AR_ESI_NFCI'])[0];v.loc[v.index+h>t-1,'target']=12345.;after=fit(v[mask],v.loc[t],MODELS['AR_ESI_NFCI'])[0];assert abs(after-before)<1e-12;mutations.append(dict(h=h,prediction_difference=after-before))
 validation=dict(forecasts=len(f),historical_forecasts=int(f.information.eq('historical_NFCI').sum()),NFCI_counterfactual_forecasts=int(f.information.eq('revised_NFCI_counterfactual').sum()),independent_LP_solver_checks=checks,current_future_label_mutation=mutations,all_models_common_origins=True,all_models_common_training_rows=True,all_designs_full_rank=True,minimum_training_rows=int(f.n_train.min()),maximum_condition=float(f.condition.max()),versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__),no_unconditional_superiority_claim_from_expanding=True)
 assert len(f)==1695 and f.groupby(['variant','information','h','origin']).model.nunique().isin([1,4]).all()
 (O/'pilot_validation.json').write_text(json.dumps(validation,indent=2));print(scores.query("information=='historical_NFCI' and variant=='expanding'").to_string(index=False));print(tt.query('h==1 and L==4').to_string(index=False));print(json.dumps(validation,indent=2))

if __name__=='__main__':run()
