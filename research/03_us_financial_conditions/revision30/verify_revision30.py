"""Independent arithmetic, chronology and manuscript checks of saved revision 30 outputs.
No refits or network calls. Fitting and future-event mutation checks are recorded separately.
"""
from pathlib import Path
import json,hashlib,re
import numpy as np
import pandas as pd
from PIL import Image
P=Path(__file__).resolve().parent;R=P.parent;O=P/'results';checks={}
def ck(name,ok):
 checks[name]=bool(ok)
 if not ok:raise AssertionError(name)
f=pd.read_csv(O/'equity_forecasts.csv');s=pd.read_csv(O/'equity_scores.csv');c=pd.read_csv(O/'equity_comparisons.csv');cal=pd.read_csv(O/'equity_calendar.csv');mo=pd.read_csv(O/'equity_monthly_inputs.csv');frames=pd.read_csv(O/'equity_model_frames.csv');tr=pd.read_csv(O/'equity_training_checks.csv');co=pd.read_csv(O/'equity_coefficients.csv')
ck('1808_unique_forecasts',len(f)==1808 and not f.duplicated(['guard','h','origin','model']).any())
ck('904_coefficients_791_regressions',len(co)==904 and sum(co.model!='HIST')==791)
ck('finite_forecasts_and_facts',np.isfinite(f[['forecast','actual','loss']]).all().all())
e=f.actual-f.forecast
ck('asymmetric_loss_recomputed',np.allclose(f.loss,e*(.1-(e<0).astype(int)),rtol=1e-12,atol=1e-12))
ck('hits_recomputed',np.array_equal(f.hit,(e<0).astype(int)))
ck('same_dates_all_models',all(f[f.h.eq(h)].groupby(['guard','model']).origin.apply(lambda a:tuple(sorted(a))).nunique()==1 and f[f.h.eq(h)].groupby(['guard','model']).size().eq(n).all() for h,n in [(1,58),(4,55)]))
ck('common_training_n_and_actual',f.groupby(['h','origin']).n_train.nunique().eq(1).all() and f.groupby(['h','origin']).actual.nunique().eq(1).all())
expected=[]
for sample,omit in [('all',[]),('omit_2020Q4',['2020Q4']),('omit_repaired_origins',['2020Q2','2021Q1','2022Q2'])]:
 z=f[~f.origin.isin(omit)].groupby(['guard','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).reset_index();z['sample']=sample
 for bm in ['HIST','AR_ESI','AR_ESI_EQ']:
  den=z[z.model.eq(bm)].set_index(['guard','h']).mean_loss
  z['ratio_'+bm]=[x.mean_loss/den[x.guard,x.h] for x in z.itertuples()]
 expected.append(z)
j=pd.concat(expected).merge(s,on=['sample','guard','h','model'],suffixes=('_a','_b'),validate='one_to_one')
ck('96_score_rows_recomputed',len(j)==96 and all(np.allclose(j[k+'_a'],j[k+'_b'],rtol=1e-11,atol=1e-11) for k in ['n','mean_loss','hits','hit_rate','ratio_HIST','ratio_AR_ESI','ratio_AR_ESI_EQ']))
for r in c.itertuples():
 z=f[(f.guard==r.guard)&(f.h==r.h)].pivot(index='origin',columns='model',values='loss');d=z[r.model]-z[r.benchmark];wo=np.array([d.drop(o).mean() for o in d.index]);assert np.isclose(d.mean(),r.difference) and np.isclose(wo.min(),r.min_omission_difference) and np.isclose(wo.max(),r.max_omission_difference) and sum(wo<0)==r.negative_after_each_single_omission
ck('16_single_omission_summaries_recomputed',len(c)==16)
old=pd.read_csv(R/'revision25/results/forecasts.csv');old=old[(old.variant=='expanding')&old.config.isin(['Q_raw','Q_clip_g'])].copy();old['guard']=old.config.str.removeprefix('Q_');j=f.merge(old,on=['guard','h','origin','model'],suffixes=('_new','_old'),validate='one_to_one')
ck('1130_prior_forecasts_reproduced',len(j)==1130 and all(np.allclose(j[k+'_new'],j[k+'_old'],rtol=0,atol=1e-8) for k in ['forecast','loss','actual','n_train']))
ck('59_complete_input_sets',len(cal)==59 and cal.available.all() and np.isfinite(cal['eq']).all())
ck('public_dates_and_freezes',all(pd.Timestamp(x.equity_public)<=pd.Timestamp(x.forecast_date) and pd.Timestamp(x.equity_freeze)<=pd.Period(x.origin).end_time for x in cal.itertuples()))
mm=mo.merge(cal[['origin','forecast_date']],on='origin',validate='many_to_one');ck('every_monthly_update_before_forecast',(pd.to_datetime(mm.public_update)<=pd.to_datetime(mm.forecast_date)).all())
for r in cal.itertuples():
 t=pd.Period(r.origin,freq='Q');req=[str(q.asfreq('M','start')+i) for q in [t-1,t] for i in [0,1]];z=mo[mo.origin.eq(r.origin)].set_index('month');assert len(z)==len(z.index.unique());vv=z.loc[req].value.to_numpy();value=100*np.log(vv[2:].mean()/vv[:2].mean());assert np.isclose(value,r.eq,rtol=0,atol=1e-10);assert set(z[z.used_for_current_eq].index)==set(req)
ck('59_current_EQ_values_independently_recomputed',True)
# Reconstruct every quarterly equity feature from the stored monthly input snapshot.
for origin,z in mo.groupby('origin'):
 values=z.set_index('month').value
 for rr in frames[frames.origin.eq(origin)&frames['eq'].notna()].itertuples():
  q=pd.Period(rr.quarter);req=[str(v.asfreq('M','start')+i) for v in [q-1,q] for i in [0,1]];vv=values.loc[req].to_numpy();assert np.isclose(rr.eq,100*np.log(vv[2:].mean()/vv[:2].mean()),atol=1e-10,rtol=0)
ck('all_nonmissing_EQ_features_reconstructed',True)
ck('113_common_training_sets',len(tr)==113 and tr.same_as_original_training.all() and tr.n_train.eq(tr.old_n_train).all())
models={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],'AR_ESI_NFCI':['gx','esi','nfci'],'AR_ESI_ANFCI':['gx','esi','anfci'],'AR_ESI_EQ':['gx','esi','eq'],'AR_ESI_EQ_NFCI':['gx','esi','eq','nfci'],'AR_ESI_EQ_ANFCI':['gx','esi','eq','anfci']}
for rr in tr.itertuples():
 t=pd.Period(rr.origin);v=frames[frames.origin.eq(rr.origin)].copy();v.index=pd.PeriodIndex(v.quarter,freq='Q');mask=(v.index>=pd.Period('1995Q3'))&(v.index+rr.h<=t-1)&v[['y'+str(rr.h),'gx','esi','nfci','anfci','eq']].notna().all(axis=1);train=v[mask];assert ';'.join(map(str,train.index))==rr.training_rows;assert len(train)==rr.n_train;cur=v.loc[t]
 for b in co[(co.h==rr.h)&co.origin.eq(rr.origin)].itertuples():
  pred=b.const+sum(getattr(b,k)*cur[k] for k in models[b.model]);clipped=float(np.clip(cur.gx,train.gx.min(),train.gx.max()))
  if b.model=='HIST':assert np.isclose(pred,np.quantile(train['y'+str(rr.h)],.1,method='inverted_cdf'),atol=1e-10)
  for guard in ['raw','clip_g']:
   y=pred+(getattr(b,'gx',0) if 'gx' in models[b.model] else 0)*(clipped-cur.gx) if guard=='clip_g' else pred
   saved=f[(f.h==rr.h)&f.origin.eq(rr.origin)&f.model.eq(b.model)&f.guard.eq(guard)].forecast.iloc[0];assert np.isclose(y,saved,rtol=1e-10,atol=1e-10)
ck('chronological_training_and_1808_predictions_reconstructed',True)
cross=pd.read_csv(O/'equity_api_legacy_crosscheck.csv');ck('60_legacy_API_crosschecks_exact',len(cross)==60 and cross.paired.gt(0).all() and cross.max_abs_difference.eq(0).all())
rep=pd.read_csv(O/'equity_bulletin_repairs.csv').set_index('month');ck('four_published_repairs',len(rep)==4 and all(rep.loc[k,'value']==v for k,v in {'2020-04':2839.6,'2021-01':3592.2,'2022-04':3837.3,'2022-05':3691.8}.items()))
lock=json.loads((P/'protocol_lock.json').read_text());ck('locked_protocol_hash',hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()==lock['sha256'])
vd=json.loads((O/'equity_data_validation.json').read_text());vm=json.loads((O/'equity_model_validation.json').read_text());ck('stored_future_mutations_and_solver_checks',all(x['max_feature_change']==0 for x in vd['future_mutations']) and all(x['forecast_difference']==0 for x in vm['future_label_mutations']) and len(vm['solver_checks'])==18 and all(abs(x['objective_difference'])<1e-6 for x in vm['solver_checks']))
full=s[(s['sample']=='all')&s.model.isin(['AR_ESI_EQ_NFCI','AR_ESI_EQ_ANFCI'])];ck('new_US_models_lose_HIST_on_full_samples',full.ratio_HIST.gt(1).all())
a=s[s.model.eq('AR_ESI_EQ_ANFCI')];ck('ANFCI_EQ_small_gain_survives_diagnostics',a[(a.guard=='raw')&(a['sample']=='omit_2020Q4')].ratio_AR_ESI_EQ.lt(1).all() and a[(a.guard=='clip_g')&(a['sample']=='all')].ratio_AR_ESI_EQ.lt(1).all())
t=(R/'manuscript/Diploma_US_Financial_Conditions_Euro_Area.md').read_text();ck('five_figures_linked',len(re.findall(r'!\[.*?\]\(\.\./revision30/figures/.*?\.png\)',t))==5)
for path in re.findall(r'!\[.*?\]\(([^)]+)\)',t):
 img=R/'manuscript'/path;assert img.is_file();Image.open(img).verify();assert img.with_suffix('.svg').is_file()
ck('figure_assets_present_and_readable',True)
ck('no_accidental_double_escaped_inline_log','100\\\\ln' not in t)
ck('new_results_and_access_limit_disclosed',all(x in t for x in ['1 808','904','1 130','3,4 и 5,1%','1,9 и 2,3%','SOURCE_ACCESS_AUDIT.md']))
result={'revision':30,'passed':all(checks.values()),'checks':checks,'forecasts_checked':len(f),'fitting_procedures_stored':len(co),'refits_in_this_verifier':0,'manuscript_sha256':hashlib.sha256(t.encode()).hexdigest()}
(O/'FINAL_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':len(checks),'forecasts':len(f)}))
