"""Partial vintage sensitivity: only NFCI is vintaged, other variables stay revised.

Run with --download once; afterwards the included CSVs reproduce this offline.
This is not a full real-time experiment and does not repair CISS/ESI/GDP vintages.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import ast, json, hashlib, sys, urllib.request, io
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack

P=Path(__file__).resolve().parent;R=P.parent;S=P/'sources/nfci_vintages';O=P/'results'
S.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
qs=pd.period_range('2011Q2','2025Q4',freq='Q')
def obtain(q):
 dt=str(q.end_time.date());name='nfci_'+dt+'.csv';f=S/name
 url=f'https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=NFCI&cosd=1995-01-01&coed={dt}&vintage_date={dt}'
 try:
  if f.exists():b=f.read_bytes()
  elif '--download' in sys.argv:
   with urllib.request.urlopen(url,timeout=30) as res:b=res.read()
  else:raise FileNotFoundError(name)
  x=pd.read_csv(io.BytesIO(b));expected='NFCI_'+dt.replace('-','')
  assert list(x.columns)==['observation_date',expected],list(x.columns)
  v=pd.to_numeric(x[expected],errors='coerce');dts=pd.to_datetime(x.observation_date)
  assert v.notna().sum()>800 and dts.max()<=pd.Timestamp(dt)
  assert not dts.duplicated().any()
  f.write_bytes(b)
  return dict(origin=str(q),vintage_date=dt,filename=name,url=url,valid=True,n=int(v.notna().sum()),first_observation=str(dts.min().date()),last_observation=str(dts.max().date()),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:return dict(origin=str(q),vintage_date=dt,url=url,valid=False,error=str(e))

rows=[]
with ThreadPoolExecutor(max_workers=3) as ex:
 for row in ex.map(obtain,qs):
  rows.append(row);print(row['origin'],row['valid'],row.get('error',''),flush=True)
(S/'manifest.json').write_text(json.dumps(rows,indent=2))

src=(R/'audit/model/compute.py').read_text();tree=ast.parse(src)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'lp_functions','exec'))
d=pd.read_csv(R/'final_check/results/model_data.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q')
frozen=pd.read_csv(R/'final_check/results/forecasts.csv')
preds=[];features=[]
for info in rows:
 if not info['valid']:continue
 t=pd.Period(info['origin'],freq='Q');x=pd.read_csv(S/info['filename']);x=pd.Series(pd.to_numeric(x.iloc[:,1],errors='coerce').to_numpy(),index=pd.to_datetime(x.iloc[:,0])).dropna()
 v=d.copy()
 for q in v.index[v.index<=t]:
  w=x[(x.index>=q.start_time)&(x.index+pd.Timedelta(days=7)<=q.end_time)]
  assert len(w)>0,(t,q)
  v.at[q,'nfci']=w.mean()
  features.append(dict(origin=str(t),feature_quarter=str(q),nfci_vintaged=w.mean(),nfci_project_snapshot=d.at[q,'nfci'],last_observation_used=str(w.index.max().date()),vintage_date=info['vintage_date']))
 for h in [1,4]:
  v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea)
  if pd.isna(v.at[t,'target']):continue
  mask=(v.index+h<=t-1)&v[['target','gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)
  tr=v.loc[mask];p,_,b=fitpred(tr,v.loc[t],['gx','ea','esi','nfci'])
  old=frozen[(frozen.variant=='expanding_lag1')&(frozen.h==h)&(frozen.origin==str(t))&(frozen.model=='US_NFCI')].iloc[0]
  preds.append(dict(h=h,origin=str(t),model='US_NFCI_vintaged_only',actual=v.at[t,'target'],forecast=p,loss=float(loss(v.at[t,'target']-p)),hit=int(v.at[t,'target']<p),n_train=len(tr),snapshot_forecast=old.forecast,snapshot_loss=old.loss,fully_real_time=False))
ff=pd.DataFrame(preds);ff.to_csv(O/'nfci_partial_vintage_forecasts.csv',index=False);pd.DataFrame(features).to_csv(O/'nfci_partial_vintage_features.csv',index=False)
scores=[]
for h,g in ff.groupby('h'):
 common=frozen[(frozen.variant=='expanding_lag1')&(frozen.h==h)&frozen.origin.isin(g.origin)]
 for m,gg in common.groupby('model'):
  scores.append(dict(h=h,model=m,n=len(gg),mean_loss=gg.loss.mean(),hit_rate=gg.hit.mean()))
 scores.append(dict(h=h,model='US_NFCI_vintaged_only',n=len(g),mean_loss=g.loss.mean(),hit_rate=g.hit.mean()))
ss=pd.DataFrame(scores)
for h,g in ss.groupby('h'):
 for b in ['BASE','HIST','US_NFCI']:ss.loc[g.index,'ratio_'+b]=g.mean_loss/float(g.loc[g.model==b,'mean_loss'].iloc[0])
ss.to_csv(O/'nfci_partial_vintage_scores.csv',index=False)
z=pd.DataFrame(features);delta=z.nfci_vintaged-z.nfci_project_snapshot
summary=dict(vintage_dates_requested=len(rows),vintage_dates_verified=sum(x['valid'] for x in rows),failed_origins=[x['origin'] for x in rows if not x['valid']],forecasts=len(ff),latest_snapshot_forecasts_unchanged=True,other_variables='revised project snapshots GDP EA20, ESI, daily NewCISS',training_NFCI='entire historical NFCI as available at forecast-origin vintage; seven-day observation buffer',all_observations_at_or_before_vintage=True,mean_abs_feature_revision=float(delta.abs().mean()),max_abs_feature_revision=float(delta.abs().max()),fully_real_time=False,interpretation='partial NFCI vintage sensitivity only; does not establish real-time model superiority')
(O/'nfci_partial_vintage_validation.json').write_text(json.dumps(summary,indent=2));print(ss.to_string(index=False));print(json.dumps(summary,indent=2))
