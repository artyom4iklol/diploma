from pathlib import Path
import ast,json,platform
import numpy as np,pandas as pd,scipy
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
from scipy.stats import norm
P=Path(__file__).resolve().parent;ROOT=P.parent;O=P/'results';O.mkdir(exist_ok=True)
src=(ROOT/'audit/model/compute.py').read_text();tree=ast.parse(src);exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'lp_functions','exec'))
raw=ROOT/'robustness/model/raw';d=pd.read_csv(raw/'quarterly.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q');assert not d.index.duplicated().any() and d.gdp_ea.gt(0).all()
d['gx']=400*np.log(d.gdp_ea).diff().shift(1);d['gx2']=400*np.log(d.gdp_ea).diff().shift(2)
j=json.loads((raw/'esi.json').read_text());es=pd.Series({pd.Period(t,freq='M'):j['value'].get(str(i),np.nan) for t,i in j['dimension']['time']['category']['index'].items()}).sort_index();d['esi']=es[es.index.month%3!=0].groupby(es[es.index.month%3!=0].index.asfreq('Q')).mean()
av=[]
for name,file,col,dat in [('ea','ecb_ciss_ea.csv','OBS_VALUE','TIME_PERIOD'),('us','ecb_ciss_us.csv','OBS_VALUE','TIME_PERIOD'),('nfci','fred_nfci.csv','NFCI','observation_date')]:
 x=pd.read_csv(raw/file);x=pd.Series(pd.to_numeric(x[col],errors='coerce').values,index=pd.to_datetime(x[dat])).dropna().sort_index();assert not x.index.duplicated().any();vals=[]
 for q in d.index:
  xx=x[(x.index>=q.start_time)&(x.index+pd.Timedelta(days=7)<=q.end_time)];assert len(xx);vals.append(xx.mean());av.append(dict(series=name,origin=str(q),last_observation=str(xx.index.max().date()),assumed_available=str((xx.index.max()+pd.Timedelta(days=7)).date())))
 d[name]=vals
old=pd.read_csv(ROOT/'robustness/model/results/model_data.csv',index_col=0)
assert np.allclose(d.gdp_ea,old.gdp_ea)
for k in ['ea','us','nfci']:assert np.allclose(d[k],old[k+'_buffer7'])
d.to_csv(O/'model_data.csv');pd.DataFrame(av).to_csv(O/'availability.csv',index=False)
F=[];C=[];D=[];mat=[];solver=[]
for variant in ['expanding_lag1','rolling52','expanding_lag2','expanding_no_growth']:
 for h in [1,4]:
  v=d.copy();v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea);growth='gx2' if variant=='expanding_lag2' else 'gx';base=([] if variant=='expanding_no_growth' else [growth])+['ea','esi'];models={'HIST':[],'AR':[growth],'BASE':base,'US_CISS':base+['us'],'US_NFCI':base+['nfci']}
  for t in v.index[v.index>=pd.Period('2010Q1')]:
   if pd.isna(v.at[t,'target']):continue
   tr=v.loc[(v.index+h<=t-1)&v[['target','gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)]
   if variant=='rolling52':tr=tr.iloc[-52:];assert len(tr)==52
   row=v.loc[t];y=float(row.target);episode='pre2020' if t+h<pd.Period('2020Q1') else '2022_2025' if t+1>=pd.Period('2022Q1') else 'covid_overlap'
   for m,cols in models.items():
    if cols:
     pred,obj,b=fitpred(tr,row,cols);X=np.c_[np.ones(len(tr)),(tr[cols]-tr[cols].mean())/tr[cols].std(ddof=0)];assert np.linalg.matrix_rank(X)==X.shape[1];mat.append(dict(variant=variant,h=h,origin=str(t),model=m,condition=np.linalg.cond(X)));C.append(dict(variant=variant,h=h,origin=str(t),model=m,**b))
     if variant=='expanding_lag1' and m=='US_NFCI' and str(t) in ['2010Q1','2020Q4','2025Q1']:
      p2,o2,_=fitpred(tr,row,cols,'highs-ipm');assert abs(obj-o2)<1e-6;solver.append(dict(h=h,origin=str(t),objective_difference=obj-o2,prediction_difference=pred-p2))
     if variant=='expanding_lag1' and m in ['BASE','US_NFCI','US_CISS']:
      cap=float(np.clip(row.gx,tr.gx.min(),tr.gx.max()));pc=pred+b['gx']*(cap-row.gx);D.append(dict(h=h,origin=str(t),model=m,forecast=pred,bounded_forecast=pc,loss=float(loss(y-pred)),bounded_loss=float(loss(y-pc)),outside=bool(cap!=row.gx)))
    else:pred=float(np.quantile(tr.target,.1,method='inverted_cdf'))
    assert tr.index.max()+h<=t-1;F.append(dict(variant=variant,h=h,origin=str(t),episode=episode,model=m,n_train=len(tr),actual=y,forecast=pred,loss=float(loss(y-pred)),hit=int(y<pred)))
 print(variant,'complete',flush=True)
f=pd.DataFrame(F);f.to_csv(O/'forecasts.csv',index=False);pd.DataFrame(C).to_csv(O/'coefficients.csv',index=False);pd.DataFrame(D).to_csv(O/'extrapolation.csv',index=False);pd.DataFrame(mat).to_csv(O/'matrix_checks.csv',index=False)
f.groupby(['variant','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).to_csv(O/'scores.csv');f.groupby(['variant','h','episode','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(O/'episode_scores.csv')
def se_hac(x,L):
 u=np.asarray(x)-np.mean(x);n=len(u);om=u@u/n+2*sum((1-k/(L+1))*(u[k:]@u[:-k])/n for k in range(1,min(L+1,n)));return np.sqrt(max(om,0)/n)
comp=[];loo=[];hac=[];cal=[]
for (variant,h),g in f.groupby(['variant','h']):
 w=g.pivot(index='origin',columns='model',values='loss').sort_index()
 for a,b in [('US_NFCI','BASE'),('US_CISS','BASE'),('US_NFCI','HIST'),('US_NFCI','US_CISS')]:
  va=w[a].to_numpy();vb=w[b].to_numpy();delta=va-vb;comp.append(dict(variant=variant,h=h,comparison=a+'/'+b,ratio=va.mean()/vb.mean(),difference=delta.mean()))
  for i,t in enumerate(w.index):loo.append(dict(variant=variant,h=h,comparison=a+'/'+b,omitted_origin=t,ratio_without=(va.sum()-va[i])/(vb.sum()-vb[i]),gain_at_origin=vb[i]-va[i]))
  if variant=='rolling52':
   for L in [4,8]:
    se=se_hac(delta,L);hac.append(dict(h=h,comparison=a+'/'+b,L=L,difference=delta.mean(),se=se,p=2*norm.sf(abs(delta.mean()/se)),lo=delta.mean()-1.96*se,hi=delta.mean()+1.96*se))
 for m,gg in g.groupby('model'):
  hits=gg.sort_values('origin').hit.to_numpy();n=len(hits);ph=hits.mean();z=norm.ppf(.975);den=1+z*z/n;ctr=(ph+z*z/(2*n))/den;half=z*np.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den;row=dict(variant=variant,h=h,model=m,n=n,hits=int(hits.sum()),rate=ph,iid_wilson_low=ctr-half,iid_wilson_high=ctr+half)
  for L in [4,8]:
   se=se_hac(hits-.1,L);row['hac_p_L'+str(L)]=2*norm.sf(abs((ph-.1)/se)) if se>0 else np.nan
  cal.append(row)
a=pd.DataFrame(hac)
for L in [4,8]:
 ids=a.query('h==1 and L==@L').sort_values('p').index;running=0
 for rank,i in enumerate(ids):running=max(running,(len(ids)-rank)*a.at[i,'p']);a.at[i,'holm4']=min(1,running)
a.to_csv(O/'rolling_hac.csv',index=False);pd.DataFrame(comp).to_csv(O/'comparisons.csv',index=False);pd.DataFrame(loo).to_csv(O/'leave_one_origin_out.csv',index=False);pd.DataFrame(cal).to_csv(O/'coverage.csv',index=False)
f4=f.query('h==4').copy();f4['phase']=pd.PeriodIndex(f4.origin,freq='Q').quarter;f4.groupby(['variant','model','phase']).agg(n=('hit','size'),hits=('hit','sum'),rate=('hit','mean')).to_csv(O/'h4_phases.csv');d[['gx','ea','us','nfci','esi']].corr().to_csv(O/'feature_correlations.csv')
comparisons={}
for variant,file,n in [('expanding_lag1','extrapolation.csv',369),('rolling52','rolling_forecasts.csv',615)]:
 old=pd.read_csv(ROOT/'acceptance'/file);merged=f.query('variant==@variant').merge(old,on=['h','origin','model'],suffixes=('_new','_old'));assert len(merged)==n;err=float((merged.forecast_new-merged.forecast_old).abs().max());assert err<1e-6;comparisons[variant]=dict(n=n,max_abs_error=err)
mut=[]
for h in [1,4]:
 t=pd.Period('2018Q4');preds=[]
 for change in [False,True]:
  v=d.copy()
  if change:v.loc[v.index>t,'gdp_ea']*=1.5
  v['gx']=400*np.log(v.gdp_ea).diff().shift(1);v['gx2']=400*np.log(v.gdp_ea).diff().shift(2);v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea);tr=v.loc[(v.index+h<=t-1)&v[['target','gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)];preds.append(fitpred(tr,v.loc[t],['gx','ea','esi','nfci'])[0])
 assert abs(preds[0]-preds[1])<1e-10;mut.append(dict(h=h,difference=preds[1]-preds[0]))
assert len(f)==2460 and f.groupby(['variant','h','origin']).model.nunique().eq(5).all()
validation=dict(forecasts=len(f),raw_aggregation_matches=True,archived_comparisons=comparisons,independent_solver_checks=solver,future_mutation=mut,full_rank=True,common_origins=True,versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__))
(O/'validation.json').write_text(json.dumps(validation,indent=2));print(json.dumps(validation,indent=2))
