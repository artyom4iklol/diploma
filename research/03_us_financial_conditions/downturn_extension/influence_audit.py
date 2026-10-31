"""Describe the already planned leave-one-target-out checks and extrapolation.
These diagnostics never change forecasts, fit choices or the primary test.
"""
from pathlib import Path
import json
import numpy as np,pandas as pd
from run_models import load_spec,prepare_frame
P=Path(__file__).resolve().parent;O=P/'results'

def main():
 spec=load_spec();f=pd.read_csv(O/'forecasts.csv');loss=pd.read_csv(O/'loss_contributions.csv');loo=pd.read_csv(O/'leave_one_target_out.csv');calendar=pd.read_csv(O/'forecast_calendar.csv');panel=pd.read_csv(P/'data/processed/quarterly_panel.csv',index_col=0);panel.index=pd.PeriodIndex(panel.index,freq='Q');coeff=[json.loads(x) for x in (O/'coefficients.jsonl').read_text().splitlines()]
 summaries=[]
 for (e,h,m,b),d in loss.groupby(['experiment','h','model','benchmark']):
  lo=loo[(loo.experiment==e)&(loo.h==h)&(loo.model==m)&(loo.benchmark==b)];best=d.loc[d.brier_difference.idxmin()];worst=d.loc[d.brier_difference.idxmax()]
  summaries.append({'experiment':e,'h':h,'model':m,'benchmark':b,'n':len(d),'mean_difference':d.brier_difference.mean(),'negative_after_omission':int(lo.mean_difference.lt(0).sum()),'omission_min':lo.mean_difference.min(),'omission_max':lo.mean_difference.max(),'largest_gain_target':best.target_quarter,'largest_gain_difference':best.brier_difference,'largest_loss_target':worst.target_quarter,'largest_loss_difference':worst.brier_difference,'status':'evaluation-only leave-one-target-out, no refit'})
 pd.DataFrame(summaries).to_csv(O/'influence_summary.csv',index=False)
 cases={x['name']:x for x in spec['refit_sensitivities']};frames={e:prepare_frame(panel,cases.get(e,{}))[0] for e in f.experiment.unique() if not e.startswith('archive')};lookup={(x.experiment,int(x.h),x.origin):x for x in calendar[~calendar.experiment.str.startswith('archive')].itertuples()};flags=[]
 for c in coeff:
  e=c['experiment']
  if e.startswith('archive'):continue
  row=lookup[(e,int(c['h']),c['origin'])];ix=pd.PeriodIndex(row.training_origins.split(';'),freq='Q');frame=frames[e];cols=c['columns'][1:];x=frame.loc[pd.Period(c['origin']),cols];train=frame.loc[ix,cols]
  for name in cols:
   lo=float(train[name].min());hi=float(train[name].max());val=float(x[name])
   if val<lo or val>hi:flags.append({'experiment':e,'h':c['h'],'origin':c['origin'],'target_quarter':str(pd.Period(c['origin'])+c['h']),'model':c['model'],'predictor':name,'value':val,'training_min':lo,'training_max':hi,'range_distance':max(lo-val,val-hi,0)})
 pd.DataFrame(flags).to_csv(O/'extrapolation_flags.csv',index=False)
 mainloo=loo[(loo.experiment=='core_long')&(loo.h==1)&(loo.model=='EU_CREDIT')&(loo.benchmark=='EU')];main=f[(f.experiment=='core_long')&(f.h==1)&f.target_quarter.ne('2020Q4')];bs=main.groupby('model').brier.mean();z=loss[(loss.experiment=='core_long')&(loss.h==1)&(loss.model=='EU_CREDIT')&(loss.benchmark=='EU')];r=z[z.target_quarter.eq('2020Q4')].iloc[0]
 result={'main_improvement_without_2020Q4_pct':float(100*(1-bs.EU_CREDIT/bs.EU)),'negative_difference_after_each_single_omission':int(mainloo.mean_difference.lt(0).sum()),'single_omissions':len(mainloo),'2020Q4_share_of_net_gain':float(r.brier_difference/z.brier_difference.sum()),'2020Q4_status':'largest net gain identified from the preplanned all-date influence analysis; retrospective diagnostic, not a new primary design','extrapolation_records':len(flags),'origin_2020Q3_gdp_lag_outside_training':any(x['experiment']=='core_long' and x['h']==1 and x['origin']=='2020Q3' and x['predictor']=='gdp_lag' for x in flags),'forecasts_modified':False}
 (P/'checks/influence_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
