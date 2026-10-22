from pathlib import Path
import ast,json
import numpy as np,pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
P=Path(__file__).resolve().parent;R=P.parent;O=P/'results';O.mkdir(exist_ok=True)
f=pd.read_csv(R/'final_check/results/forecasts.csv');s=f.groupby(['variant','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).reset_index()
for key,g in s.groupby(['variant','h']):
 for baseline in ['BASE','HIST','AR']:
  b=float(g.loc[g.model==baseline,'mean_loss'].iloc[0]);s.loc[g.index,'ratio_to_'+baseline]=g.mean_loss/b
s.to_csv(O/'central_comparison.csv',index=False)
p=[]
for (v,h,ep),g in f.groupby(['variant','h','episode']):
 w=g.pivot(index='origin',columns='model',values='loss')
 for m in w.columns:
  p.append(dict(variant=v,h=h,episode=ep,model=m,n=len(w),mean_loss=w[m].mean(),ratio_BASE=w[m].mean()/w.BASE.mean(),ratio_HIST=w[m].mean()/w.HIST.mean(),fraction_better_HIST=(w[m]<w.HIST).mean()))
pd.DataFrame(p).to_csv(O/'subperiod_comparison.csv',index=False)
lof=[];rank=[];largest=[]
for (v,h),g in f.groupby(['variant','h']):
 w=g.pivot(index='origin',columns='model',values='loss')
 for t in w.index:
  ww=w.drop(t);rank.append(dict(variant=v,h=h,omitted=t,best_model=ww.mean().idxmin()))
 for a,b in [('US_NFCI','BASE'),('US_CISS','BASE'),('US_NFCI','HIST'),('US_CISS','HIST')]:
  delta=w[b]-w[a];total=delta.sum()
  for t in w.index:lof.append(dict(variant=v,h=h,pair=a+'/'+b,origin=t,gain=delta[t],share_of_net_gain=delta[t]/total if abs(total)>1e-10 else np.nan,ratio_without=(w[a].sum()-w.at[t,a])/(w[b].sum()-w.at[t,b])))
  for t,x in delta.abs().nlargest(5).items():largest.append(dict(variant=v,h=h,pair=a+'/'+b,origin=t,gain=delta[t],abs_gain=x))
pd.DataFrame(lof).to_csv(O/'single_origin_influence.csv',index=False);pd.DataFrame(rank).to_csv(O/'leave_one_out_best_model.csv',index=False);pd.DataFrame(largest).to_csv(O/'largest_influences.csv',index=False)
# Refit after removing training pairs overlapping 2020Q1--2021Q4. Post-result diagnostic.
d=pd.read_csv(R/'final_check/results/model_data.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q');src=(R/'audit/model/compute.py').read_text();tree=ast.parse(src);exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'recovered_lp','exec'))
F=[]
for h in [1,4]:
 v=d.copy();v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea)
 models={'HIST':[],'AR':['gx'],'BASE':['gx','ea','esi'],'US_CISS':['gx','ea','esi','us'],'US_NFCI':['gx','ea','esi','nfci']}
 for t in v.index[v.index>=pd.Period('2010Q1')]:
  if pd.isna(v.at[t,'target']):continue
  mask=(v.index+h<=t-1)&v[['target','gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)
  overlaps=(v.index+1<=pd.Period('2021Q4'))&(v.index+h>=pd.Period('2020Q1'))
  tr=v.loc[mask&~overlaps];row=v.loc[t]
  for m,cols in models.items():
   pred=float(np.quantile(tr.target,.1,method='inverted_cdf')) if not cols else fitpred(tr,row,cols)[0]
   F.append(dict(h=h,origin=str(t),model=m,actual=row.target,forecast=pred,loss=float(loss(row.target-pred)),n_train=len(tr)))
ff=pd.DataFrame(F);ff.to_csv(O/'no_covid_training_forecasts.csv',index=False);ss=ff.groupby(['h','model']).agg(n=('loss','size'),mean_loss=('loss','mean')).reset_index()
for h,g in ss.groupby('h'):
 for b in ['BASE','HIST']:ss.loc[g.index,'ratio_'+b]=g.mean_loss/float(g.loc[g.model==b,'mean_loss'].iloc[0])
ss.to_csv(O/'no_covid_training_scores.csv',index=False)
# Descriptive fixed-loss block bootstrap for recent subperiod, not a significance test.
rng=np.random.default_rng(15102026);boot=[]
for h in [1,4]:
 w=f.query('variant=="expanding_lag1" and h==@h and episode=="2022_2025"').pivot(index='origin',columns='model',values='loss');n=len(w)
 for a,b in [('US_NFCI','BASE'),('US_NFCI','HIST'),('US_CISS','BASE')]:
  x=w[a].to_numpy();y=w[b].to_numpy()
  for L in [4,8]:
   ix=((rng.integers(n,size=(5000,int(np.ceil(n/L))))[:,:,None]+np.arange(L))%n).reshape(5000,-1)[:,:n];r=x[ix].mean(1)/y[ix].mean(1);lo,hi=np.quantile(r,[.025,.975]);boot.append(dict(h=h,pair=a+'/'+b,n=n,L=L,ratio=x.mean()/y.mean(),lo_descriptive=lo,hi_descriptive=hi))
pd.DataFrame(boot).to_csv(O/'recent_subperiod_descriptive_intervals.csv',index=False)
validation={'historical_forecasts_unchanged':True,'all_variants_reported':True,'new_refit_forecasts':len(ff),'same_origins_new_diagnostic':all(set(ff.query('h==@h').origin)==set(f.query('variant=="expanding_lag1" and h==@h').origin) for h in [1,4]),'new_diagnostic_post_result':True,'bootstrap_fixed_losses_no_refit':True}
(O/'model_validation.json').write_text(json.dumps(validation,indent=2));print(s.query('variant=="expanding_lag1"').to_string(index=False));print(ss.to_string(index=False));print(pd.DataFrame(boot).to_string(index=False));print(validation)
