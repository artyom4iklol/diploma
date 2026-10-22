"""Descriptive diagnostics of frozen forecasts; no new model fits."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent;R=P.parent;O=P/'results';O.mkdir(exist_ok=True)
f=pd.read_csv(R/'revision25/results/forecasts.csv');assert len(f)==4520
keys=['variant','config','h','model'];e=f.actual-f.forecast
np.testing.assert_allclose(f.loss,np.where(e<0,-.9*e,.1*e),atol=1e-12)
f['loss_below']=.9*np.maximum(-e,0);f['loss_above']=.1*np.maximum(e,0)
dc=f.groupby(keys).agg(n=('loss','size'),loss=('loss','mean'),loss_below=('loss_below','mean'),loss_above=('loss_above','mean'),hits=('hit','sum')).reset_index()
dc['below_share_pct']=100*dc.loss_below/dc.loss
dc['mean_gap_below']=dc.loss_below*dc.n/.9/dc.hits.replace(0,np.nan)
dc['mean_gap_above']=dc.loss_above*dc.n/.1/(dc.n-dc.hits).replace(0,np.nan)
np.testing.assert_allclose(dc.loss,dc.loss_below+dc.loss_above,atol=1e-12)
dc.to_csv(O/'loss_decomposition.csv',index=False)
common=set(f.loc[f.h==1,'origin'])&set(f.loc[f.h==4,'origin'])
assert len(common)==55 and min(common)=='2011Q2' and max(common)=='2024Q4'
co=f[f.origin.isin(common)].groupby(keys).agg(n=('loss','size'),mean_loss=('loss','mean'),hits=('hit','sum')).reset_index()
assert co.n.eq(55).all();co.to_csv(O/'common_origins_scores.csv',index=False)
pairs=[('AR_ESI_NFCI','AR_ESI'),('AR_ESI_ANFCI','AR_ESI'),('AR_ESI_NFCI','HIST'),('AR_ESI_ANFCI','HIST'),('AR_ESI_ANFCI','AR_ESI_NFCI')]
rows=[]
for (v,c,h),g in f.groupby(['variant','config','h']):
 w=g.pivot(index='origin',columns='model',values='loss').sort_index()
 for m,b in pairs:
  for k in range(len(w)-3):
   ids=w.index[k:k+4];a=w.drop(ids);d=a[m]-a[b]
   rows.append(dict(variant=v,config=c,h=h,model=m,benchmark=b,block_start=ids[0],block_end=ids[-1],n_remaining=len(a),difference=d.mean(),ratio=a[m].mean()/a[b].mean(),contains_2020Q4='2020Q4' in ids))
bl=pd.DataFrame(rows);bl.to_csv(O/'four_origin_block_omissions.csv',index=False)
bs=bl.groupby(['variant','config','h','model','benchmark']).agg(blocks=('difference','size'),favourable=('difference',lambda x:int((x<0).sum())),min_difference=('difference','min'),max_difference=('difference','max'),min_ratio=('ratio','min'),max_ratio=('ratio','max')).reset_index()
bs.to_csv(O/'four_origin_block_summary.csv',index=False)
a=f.query("variant=='expanding' and config=='Q_raw' and h==4").copy();a['phase']=pd.PeriodIndex(a.origin,freq='Q').quarter
ph=a.groupby(['phase','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hits=('hit','sum'),first_origin=('origin','min'),last_origin=('origin','max')).reset_index()
for _,g in a.groupby('phase'):assert np.all(np.diff(pd.PeriodIndex(sorted(g.origin.unique()),freq='Q').asi8)==4)
assert sorted(ph.groupby('phase').n.first())==[13,14,14,14]
ph.to_csv(O/'h4_nonoverlap_phases.csv',index=False)
j={'date':'2026-10-21','new_model_fits':0,'forecast_rows':len(f),'decompositions':len(dc),'matched_origins':len(common),'block_comparisons':len(bl),'phase_rows':len(ph),'source_sha256':hashlib.sha256((R/'revision25/results/forecasts.csv').read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()}
(O/'validation.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
