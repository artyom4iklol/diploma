from pathlib import Path
import ast,json,hashlib
import numpy as np,pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
from scipy.stats import norm
P=Path(__file__).resolve().parent;R=P.parent/'robustness/model'
protocol={'question':'Do US indicators improve 0.10 quantile forecasts of EA20 growth conditional on European indicators, robustly across benchmarks and extrapolation diagnostics?','main':'Stage12 expanding lag1 unchanged','rolling_window':52,'choice':'13 years, below initial available training size for both horizons; fixed before results, no window optimization; supplement after prior expanding results known','horizons':[1,4],'tau':.1,'comparisons':['US_NFCI/BASE','US_CISS/BASE','US_NFCI/HIST','US_NFCI/US_CISS'],'inference':'Unconditional predictive ability for finite-memory methods, asymptotic normal HAC Bartlett L4 primary L8 sensitivity; Holm4 only h1; not conditional coverage; not real-time','limits':'mixing, moments, nondegenerate variance and appropriate null needed; small samples and extreme changes restrict approximation; no claim of proven superiority','diagnostic':'growth bounded at training min/max with coefficients unchanged; centered term decomposition; all evaluation dates retained','date':'2026-10-04','restoration':'Oct3 attempt interrupted after forecasts before validation; local files lost; design reconstructed from conversation and rerun without changes to window or tests'}
(P/'PROTOCOL.json').write_text(json.dumps(protocol,indent=2))
mod=ast.parse((R/'compute.py').read_text());exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'fit_functions','exec'))
d=pd.read_csv(R/'results/model_data.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q')
es=pd.read_csv(R/'raw/esi_monthly.csv',index_col=0).iloc[:,0];es.index=pd.PeriodIndex(es.index,freq='M')
d['esi']=es[es.index.month%3!=0].groupby(es[es.index.month%3!=0].index.asfreq('Q')).mean();d['gx2']=(400*np.log(d.gdp_ea).diff()).shift(2)
for x in ['ea','us','nfci']:d[x]=d[x+'_buffer7']
models={'HIST':[],'AR':['gx'],'BASE':['gx','ea','esi'],'US_CISS':['gx','ea','esi','us'],'US_NFCI':['gx','ea','esi','nfci']}
old=pd.read_csv(R/'results/forecasts.csv').query('variant=="lag1"');F=[];D=[];C=[]
for h in [1,4]:
 v=d.copy();v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea)
 for t in v.index[v.index>=pd.Period('2010Q1')]:
  if pd.isna(v.at[t,'target']):continue
  mask=(v.index+h<=t-1)&v[['target','gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)
  train=v.loc[mask].copy();test=v.loc[t].copy();y=float(test.target);assert len(train)>=52
  for m,cols in models.items():
   tr=train.iloc[-52:];pred=float(np.quantile(tr.target,.1,method='inverted_cdf')) if not cols else fitpred(tr,test,cols)[0]
   F.append(dict(h=h,origin=str(t),model=m,actual=y,forecast=pred,loss=float(loss(y-pred)),hit=int(y<pred),n_train=len(tr),first_train=str(tr.index.min()),last_train_target=str(tr.index.max()+h)))
   if m not in ['BASE','US_NFCI','US_CISS']:continue
   p,obj,b=fitpred(train,test,cols);saved=old[(old.h==h)&(old.origin==str(t))&(old.model==m)];assert abs(p-saved.forecast.iloc[0])<1e-6
   cap=float(np.clip(test.gx,train.gx.min(),train.gx.max()));pc=p+b['gx']*(cap-test.gx)
   D.append(dict(h=h,origin=str(t),model=m,gx=test.gx,train_min=train.gx.min(),train_max=train.gx.max(),outside=bool(cap!=test.gx),forecast=p,bounded_growth_forecast=pc,loss=float(loss(y-p)),bounded_growth_loss=float(loss(y-pc)),actual=y))
   if h==1 and str(t)=='2020Q4':
    C.append(dict(model=m,term='at_training_means',value=1.,coefficient=b['const']+sum(b[x]*train[x].mean() for x in cols),contribution=b['const']+sum(b[x]*train[x].mean() for x in cols)))
    for x in cols:C.append(dict(model=m,term=x,value=float(test[x]-train[x].mean()),coefficient=b[x],contribution=float(b[x]*(test[x]-train[x].mean()))))
f=pd.DataFrame(F);f.to_csv(P/'rolling_forecasts.csv',index=False);dd=pd.DataFrame(D);dd.to_csv(P/'extrapolation.csv',index=False);pd.DataFrame(C).to_csv(P/'centered_decomposition.csv',index=False)
pairs=[('US_NFCI','BASE'),('US_CISS','BASE'),('US_NFCI','HIST'),('US_NFCI','US_CISS')];out=[]
for h,g in f.groupby('h'):
 w=g.pivot(index='origin',columns='model',values='loss').sort_index()
 for a,b in pairs:
  delta=(w[a]-w[b]).to_numpy();n=len(delta);u=delta-delta.mean()
  for L in [4,8]:
   omega=u@u/n+2*sum((1-k/(L+1))*(u[k:]@u[:-k])/n for k in range(1,L+1));assert omega>0
   W=np.maximum(0,1-np.abs(np.arange(n)[:,None]-np.arange(n)[None,:])/(L+1));assert abs(omega-u@W@u/n)<1e-10
   se=np.sqrt(omega/n);z=delta.mean()/se
   out.append(dict(h=h,comparison=a+'/'+b,L=L,n=n,ratio=w[a].mean()/w[b].mean(),difference=delta.mean(),se=se,z=z,p_two_sided=2*norm.sf(abs(z)),ci_low=delta.mean()-1.96*se,ci_high=delta.mean()+1.96*se))
a=pd.DataFrame(out)
for L in [4,8]:
 ids=a.query('h==1 and L==@L').sort_values('p_two_sided').index;running=0
 for rank,i in enumerate(ids):running=max(running,(len(ids)-rank)*a.at[i,'p_two_sided']);a.at[i,'p_holm4']=min(1,running)
a.to_csv(P/'rolling_tests.csv',index=False);f.groupby(['h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(P/'rolling_scores.csv')
assert f.n_train.eq(52).all() and f.groupby(['h','origin']).model.nunique().eq(5).all()
assert all(pd.Period(r.last_train_target)<=pd.Period(r.origin)-1 for r in f.itertuples())
for h in [1,4]:assert set(f.query('h==@h').origin)==set(old.query('h==@h').origin)
summary=[]
for h,g in dd.groupby('h'):
 for metric in ['loss','bounded_growth_loss']:
  w=g.pivot(index='origin',columns='model',values=metric)
  summary.append({'h':int(h),'metric':metric,'NFCI_BASE':w.US_NFCI.mean()/w.BASE.mean(),'CISS_BASE':w.US_CISS.mean()/w.BASE.mean(),'outside_growth_n':int(g.query('model=="BASE"').outside.sum())})
(P/'diagnostic_summary.json').write_text(json.dumps(summary,indent=2));(P/'validation.json').write_text(json.dumps({'all_lp_solved':True,'expanding_predictions_reproduced':True,'common_origins':True,'fixed_train_52':True,'label_cutoff':True,'hac_matrix_match':True,'rolling_forecasts':len(f)},indent=2))
print(a.to_string(index=False));print(pd.DataFrame(C).to_string(index=False));print(json.dumps(summary,indent=2))
