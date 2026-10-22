"""Limited sensitivity checks explicitly specified before fitting the pilot."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from fit_pilot import fit,loss,MODELS

P=Path(__file__).resolve().parent;O=P/'results'
a=pd.read_csv(O/'vintaged_model_frames.csv');a['q']=pd.PeriodIndex(a.quarter,freq='Q');targets=pd.read_csv(O/'evaluation_targets.csv');ff=pd.read_csv(O/'pilot_forecasts.csv')
rows=[]
# The only repaired GDP observation is printed to one decimal place.
# Both endpoints are numerical scenarios, not mathematically certified bounds.
for h,printed,scale in [(1,.6,400),(4,5.4,100)]:
 t=pd.Period('2022Q2');v=a[a.origin.eq(str(t))].copy().set_index('q');v['target']=v['y'+str(h)]
 target=float(targets[(targets.origin.eq(str(t)))&targets.h.eq(h)].actual.iloc[0])
 for side_q in [-1,0,1]:
  for side_y in [-1,0,1]:
   qoq=.6+side_q*.05;yoy=5.4+side_y*.05
   u=v.copy();u.at[pd.Period('2022Q1')-h,'target']=scale*np.log1p((qoq if h==1 else yoy)/100)
   u.at[t,'gx']=400*np.log1p(qoq/100)
   mask=(u.index>=pd.Period('1995Q3'))&(u.index+h<=t-1)&u[['target','gx','esi','nfci']].notna().all(axis=1)
   for variant in ['expanding','rolling52']:
    tr=u[mask]
    if variant=='rolling52':tr=tr.iloc[-52:]
    for model,cols in MODELS.items():
     p,b,c=fit(tr,u.loc[t],cols)
     rows.append(dict(variant=variant,h=h,origin=str(t),model=model,qoq_scenario=qoq,yoy_scenario=yoy,forecast=p,loss=float(loss(target-p))))
r=pd.DataFrame(rows);r.to_csv(O/'GDP_rounding_scenarios.csv',index=False)
changes=[]
for (variant,h,model),g in r.groupby(['variant','h','model']):
 orig=ff[(ff.variant.eq(variant))&ff.h.eq(h)&ff.model.eq(model)&ff.information.eq('historical_NFCI')]
 oldloss=float(orig[orig.origin.eq('2022Q2')].loss.iloc[0]);base=float(orig.loss.mean())
 for row in g.itertuples():changes.append(dict(variant=variant,h=h,model=model,qoq_scenario=row.qoq_scenario,yoy_scenario=row.yoy_scenario,full_sample_mean_loss=base+(row.loss-oldloss)/len(orig)))
pd.DataFrame(changes).to_csv(O/'GDP_rounding_full_sample_effect.csv',index=False)
summary=[]
for (variant,h),g in ff[ff.information.eq('historical_NFCI')].groupby(['variant','h']):
 w=g.pivot(index='origin',columns='model',values='loss').sort_index()
 for m in ['AR_ESI_NFCI','AR_ESI','AR']:
  count=sum(((w[m].sum()-w[m])/(w.HIST.sum()-w.HIST)>1))
  summary.append(dict(variant=variant,h=h,model=m,HIST_better_after_any_single_omission=int(count),total_omissions=len(w)))
pd.DataFrame(summary).to_csv(O/'HIST_single_date_dominance.csv',index=False)
# Chronological assertions on every source/forecast/target pair.
cal=pd.read_csv(O/'forecast_calendar_59.csv');tc=pd.read_csv(O/'training_calendar_checks.csv')
assert (pd.to_datetime(cal.gdp_public_available)<=pd.to_datetime(cal.forecast_date)).all()
assert (pd.to_datetime(cal.esi_public_available)<=pd.to_datetime(cal.forecast_date)).all()
assert (pd.to_datetime(targets.matured_public_date)<=pd.to_datetime(targets.maturity_deadline)).all()
assert (pd.PeriodIndex(tc.last_training_target,freq='Q')<=pd.PeriodIndex(tc.maximum_allowed,freq='Q')).all()
assert ff.forecast.notna().all() and np.isfinite(ff[['actual','forecast','loss']].to_numpy()).all()
v=dict(rounded_GDP_scenarios=len(r),maximum_full_sample_mean_loss_change=float(max(abs(x['full_sample_mean_loss']-float(ff[(ff.variant.eq(x['variant']))&ff.h.eq(x['h'])&ff.model.eq(x['model'])&ff.information.eq('historical_NFCI')].loss.mean())) for x in changes)),all_public_calendar_checks=True,all_training_cutoff_checks=True,all_target_maturity_checks=True,all_forecasts_finite=True,source_tables_visually_checked=['eb202204 table2.1 p153 and table2.6 p157','eb202302 table2.6 p126','eb202304 table2.6 p125','eb202506 table2.6 p120'],primary_decision='GO: write diploma and an applied replication/extension article; no stable NFCI superiority established; no publication guarantee')
(O/'final_validation.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
