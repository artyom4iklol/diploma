"""Evaluate frozen forecasts; paired time-block intervals, no model re-selection."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.stats import norm
from logit_engine import metrics
from run_models import load_spec
P=Path(__file__).resolve().parent;O=P/'results'

def block_indices(n,B,L,rng):
 starts=rng.integers(0,n,size=(B,int(np.ceil(n/L))))
 return ((starts[:,:,None]+np.arange(L))%n).reshape(B,-1)[:,:n]

def holm(pvals):
 a=np.asarray(pvals,dtype=float);order=np.argsort(a);out=np.empty(len(a));last=0.
 for k,j in enumerate(order):last=max(last,(len(a)-k)*a[j]);out[j]=min(1.,last)
 return out

def run():
 spec=load_spec();f=pd.read_csv(O/'forecasts.csv');B=spec['bootstrap']['replicates'];seed=spec['bootstrap']['seed'];pairs=[];slices=[];loo=[];cal=[];contrib=[]
 # Determine only predefined evaluation slices; these never alter fitted coefficients.
 def subset(v,name):
  q=pd.PeriodIndex(v.target_quarter,freq='Q')
  if name=='all':return v
  if name=='exclude_2020Q1_Q2':return v[~q.isin(pd.PeriodIndex(['2020Q1','2020Q2'],freq='Q'))]
  if name=='2022_2025':return v[q>=pd.Period('2022Q1')]
  bounds={'gfc_2008Q2_2009Q2':('2008Q2','2009Q2'),'debt_2011Q4_2013Q1':('2011Q4','2013Q1'),'pandemic_2020Q1_Q2':('2020Q1','2020Q2')}
  lo,hi=bounds[name];return v[(q>=pd.Period(lo))&(q<=pd.Period(hi))]
 for (e,h,m),v in f.groupby(['experiment','h','model']):
  for name in spec['evaluation_slices']:
   z=subset(v,name)
   if len(z):slices.append({'experiment':e,'h':h,'model':m,'sample':name,**metrics(z.actual,z.probability)})
  bins=np.array([0,.1,.2,.4,.6,.8,1.000001]);inds=np.searchsorted(bins,v.probability,side='right')-1
  for k in sorted(set(inds)):
   z=v[inds==k];n=len(z);pos=z.actual.sum();rate=pos/n;a=norm.ppf(.975);den=1+a*a/n;center=(rate+a*a/(2*n))/den;half=a*np.sqrt(rate*(1-rate)/n+a*a/(4*n*n))/den
   cal.append({'experiment':e,'h':h,'model':m,'bin_low':bins[k],'bin_high':min(1,bins[k+1]),'n':n,'events':int(pos),'mean_probability':z.probability.mean(),'event_rate':rate,'wilson_low':center-half,'wilson_high':center+half})
 for (e,h),v in f.groupby(['experiment','h']):
  p=v.pivot(index='origin',columns='model',values='probability').sort_index();a=v.groupby('origin').actual.first().reindex(p.index);assert p.notna().all().all() and v.groupby('origin').actual.nunique().eq(1).all()
  losses=(p.sub(a,axis=0))**2
  rng=np.random.default_rng(seed+int(h)*100+sum(map(ord,e)))
  for L in spec['bootstrap']['lengths_quarters']:
   ix=block_indices(len(p),B,L,rng)
   modelpairs=[(m,'EU') for m in p if m not in ['EU','FREQ']]+[(m,'FREQ') for m in p if m!='FREQ']
   for m,b in modelpairs:
    delta=(losses[m]-losses[b]).to_numpy();observed=delta.mean();boots=delta[ix].mean(axis=1);null=boots-observed;pb=(np.sum(np.abs(null)>=abs(observed))+1)/(B+1)
    baseboots=losses[b].to_numpy()[ix].mean(axis=1);gainboots=-boots/baseboots
    row={'experiment':e,'h':h,'model':m,'benchmark':b,'n':len(p),'block_quarters':L,'brier_model':losses[m].mean(),'brier_benchmark':losses[b].mean(),'difference':observed,'ci_low':np.quantile(boots,.025),'ci_high':np.quantile(boots,.975),'skill':1-losses[m].mean()/losses[b].mean(),'skill_ci_low':np.quantile(gainboots,.025),'skill_ci_high':np.quantile(gainboots,.975),'bootstrap_p_two_sided':pb,'bootstrap_replicates':B,'interpretation':'paired saved-loss uncertainty, conditional on estimated forecasts'}
    pairs.append(row)
    if L==4:
     for i,origin in enumerate(p.index):
      target=v[v.origin.eq(origin)].target_quarter.iloc[0]
      contrib.append({'experiment':e,'h':h,'model':m,'benchmark':b,'origin':origin,'target_quarter':target,'brier_difference':delta[i]})
      loo.append({'experiment':e,'h':h,'model':m,'benchmark':b,'omitted_origin':origin,'omitted_target':target,'mean_difference':(delta.sum()-delta[i])/(len(delta)-1),'status':'evaluation-only omission, coefficients unchanged'})
 out=pd.DataFrame(pairs);out['holm_p']=np.nan
 for key,idx in out.groupby(['experiment','benchmark','block_quarters']).groups.items():out.loc[idx,'holm_p']=holm(out.loc[idx,'bootstrap_p_two_sided'])
 out.to_csv(O/'paired_comparisons.csv',index=False);pd.DataFrame(slices).to_csv(O/'episode_scores.csv',index=False);pd.DataFrame(loo).to_csv(O/'leave_one_target_out.csv',index=False);pd.DataFrame(cal).to_csv(O/'calibration.csv',index=False);pd.DataFrame(contrib).to_csv(O/'loss_contributions.csv',index=False)
 # A pre-model data audit detected a real outcome revision: assess saved forecasts against the independent source too.
 cross=pd.read_csv(P/'data/processed/gdp_crosscheck.csv').set_index('quarter');alternate=[]
 for (e,h,m),v in f[~f.experiment.str.startswith('archive')&~f.experiment.isin(['cepr_recession','gdp_ex_ireland'])].groupby(['experiment','h','model']):
  g=cross.eurostat_growth.reindex(v.target_quarter).to_numpy();keep=np.isfinite(g);assert keep.all();threshold=-.1 if e=='contraction_below_minus_0_1' else 0;yy=(g<threshold).astype(int)
  alternate.append({'experiment':e,'h':h,'model':m,'changed_labels':int(np.sum(yy!=v.actual.to_numpy())),**metrics(yy,v.probability),'status':'same saved forecasts, independent later Eurostat assessment; no refit'})
 for (e,h,m),v in f[f.experiment.str.startswith('archive')].groupby(['experiment','h','model']):alternate.append({'experiment':e,'h':h,'model':m,'changed_labels':int(np.sum(v.actual_latest!=v.actual)),**metrics(v.actual_latest,v.probability),'status':'same saved forecasts, inherited later within-RTD GDP assessment; no refit'})
 pd.DataFrame(alternate).to_csv(O/'outcome_revision_scores.csv',index=False)
 primary=out[out.experiment.eq('core_long')&out.h.eq(1)&out.model.eq('EU_CREDIT')&out.benchmark.eq('EU')&out.block_quarters.eq(4)].iloc[0].to_dict()
 summary={'primary':primary,'all_paired_rows':len(out),'sample_matching':True,'no_model_selection':True,'conditional_interval_scope':spec['bootstrap']['scope']}
 (P/'checks/evaluation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':run()
