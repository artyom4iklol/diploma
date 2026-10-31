"""Independent checks of chronology, source preservation, solver and saved forecasts."""
from pathlib import Path
import json,hashlib,contextlib,io
import numpy as np,pandas as pd
from scipy.optimize import minimize,approx_fprime,brentq
from scipy.special import expit
from run_models import load_spec,prepare_frame,run_group
from logit_engine import objective_score
P=Path(__file__).resolve().parent;R=P.parent;O=P/'results'

def main():
 spec=load_spec();checks={};details={}
 def ck(name,condition,extra=None):
  checks[name]=bool(condition)
  if extra is not None:details[name]=extra
  if not condition:raise AssertionError(name)
 f=pd.read_csv(O/'forecasts.csv');calendar=pd.read_csv(O/'forecast_calendar.csv');coeff=[json.loads(s) for s in (O/'coefficients.jsonl').read_text().splitlines()];cd={(x['experiment'],x['h'],x['origin'],x['model']):x for x in coeff};panel=pd.read_csv(P/'data/processed/quarterly_panel.csv',index_col=0);panel.index=pd.PeriodIndex(panel.index,freq='Q')
 ck('unique_forecast_keys',not f.duplicated(['experiment','h','origin','model']).any())
 ck('probabilities_finite_inside_unit_interval',np.isfinite(f.probability).all() and f.probability.between(0,1,inclusive='neither').all())
 ck('no_future_evaluation_beyond_2025',pd.PeriodIndex(f.target_quarter,freq='Q').max()==pd.Period('2025Q4'))
 ck('forecasts_before_target_quarter_starts',all(pd.Timestamp(row.issue_date)<pd.Period(row.target_quarter).start_time for row in f.itertuples()))
 ck('training_targets_before_issue_quarter',all(pd.Period(row.last_training_target)<pd.Period(row.origin) for row in calendar.itertuples()))
 ck('GDP_features_before_issue_quarter',all(pd.Period(row.gdp_max_quarter)<pd.Period(row.origin) for row in calendar.itertuples()))
 ck('financial_features_no_later_than_issue_quarter',all(pd.Period(row.feature_max_quarter)<=pd.Period(row.origin) for row in calendar.itertuples()))
 ck('matched_training_dates_and_facts',all(g.n_train.nunique()==1 and g.training_hash.nunique()==1 and g.actual.nunique()==1 for _,g in f.groupby(['experiment','h','origin'])))
 ck('no_missing_forecasts_inside_each_model_group',all(g.groupby('model').origin.apply(lambda a:tuple(sorted(a))).nunique()==1 for _,g in f.groupby(['experiment','h'])))
 ck('76_and_73_main_evaluations',all(f[(f.experiment=='core_long')&(f.h==h)].groupby('model').size().eq(n).all() for h,n in [(1,76),(4,73)]))
 ck('15_main_contractions_both_horizons',f[f.experiment.eq('core_long')].groupby(['h','model']).actual.sum().eq(15).all())
 ck('Brier_loss_independently_recomputed',np.allclose(f.brier,(f.probability-f.actual)**2,atol=1e-14))
 pp=np.clip(f.probability,1e-12,1-1e-12);ll=-(f.actual*np.log(pp)+(1-f.actual)*np.log1p(-pp))
 ck('log_loss_independently_recomputed',np.allclose(f.log_loss,ll,atol=1e-10))
 ck('warnings_use_frozen_threshold',np.array_equal(f.alarm,(f.probability>=spec['warning_threshold']).astype(int)))
 ck('Firth_adjusted_scores_small',max(c['score_max'] for c in coeff)<1e-5,max(c['score_max'] for c in coeff))
 ck('FLIC_preserves_training_event_rate',max(abs(c['train_mean_probability']-c['train_event_rate']) for c in coeff)<1e-10)
 ck('all_fits_have_both_outcome_classes',all(min(c['positives'],c['n_train']-c['positives'])>=3 for c in coeff))
 for name,expected in spec['input_sha256'].items():ck('input_'+name,hashlib.sha256((R/name).read_bytes()).hexdigest()==expected)
 for name,expected in spec['protected_documents_sha256'].items():ck('protected_'+name,hashlib.sha256((R.parent.parent/name).read_bytes()).hexdigest()==expected)
 # Reconstruct every probability from raw-scale coefficients and independent source lookups.
 cases={x['name']:x for x in spec['refit_sensitivities']};caseframes={e:prepare_frame(panel,cases.get(e,{}))[0] for e in f.experiment.unique() if not e.startswith('archive')}
 v=pd.read_csv(R/'revision30/results/equity_model_frames.csv');v['q']=pd.PeriodIndex(v.quarter,freq='Q');vframes={o:g.set_index('q') for o,g in v.groupby('origin')};errors=[]
 for row in f[f.model.ne('FREQ')].itertuples():
  c=cd[(row.experiment,row.h,row.origin,row.model)];cols=c['columns'][1:]
  if row.experiment.startswith('archive'):x=vframes[c['feature_origin']].loc[pd.Period(c['feature_origin']),cols].to_numpy(dtype=float)
  else:x=caseframes[row.experiment].loc[pd.Period(row.origin),cols].to_numpy(dtype=float)
  calc=expit(c['coefficients'][0]+np.dot(c['coefficients'][1:],x));errors.append(abs(calc-row.probability))
 ck('all_saved_forecasts_rebuilt_from_coefficients',max(errors)<1e-11,{'forecasts':len(errors),'max_abs_error':max(errors)})
 # The archival paired exercise must leave the European model EXACTLY unchanged.
 a=f[f.experiment.eq('archive_vintage')];b=f[f.experiment.eq('archive_late_index')];a=a.set_index(['h','origin','model']);b=b.set_index(['h','origin','model']);ck('archive_counterfactual_same_sample_and_facts',a.index.equals(b.index) and a.training_hash.equals(b.training_hash) and a.actual.equals(b.actual))
 ix=a.index.get_level_values('model').isin(['EU','FREQ']);ck('archive_counterfactual_EU_unchanged',np.array_equal(a.loc[ix,'probability'],b.loc[ix,'probability']))
 ac=calendar[calendar.experiment.eq('archive_vintage')]
 ck('inherited_archival_sources_public_by_issue',all(max(pd.Timestamp(x.gdp_public),pd.Timestamp(x.esi_public),pd.Timestamp(x.equity_public))<=pd.Timestamp(x.issue_date) for x in ac.itertuples()))
 ck('archival_training_ends_before_known_GDP_boundary',all(pd.Period(x.last_training_target)<=pd.Period(x.feature_origin)-1 for x in ac.itertuples()))
 # FLIC independent numerical objective optimiser and finite-difference gradient.
 samples=[]
 for experiment,origin,model,h in [('core_long','2006Q4','EU_CREDIT',1),('core_long','2020Q1','EU_BOTH',1),('europe_equity','2019Q4','EU_VIX',4),('gdp_ex_ireland','2024Q4','EU_CREDIT',1),('rolling_80','2006Q4','EU_BOTH',4),('europe_stress','2025Q3','EU_VIX',1)]:
  c=cd[(experiment,h,origin,model)];row=calendar[(calendar.experiment==experiment)&(calendar.origin==origin)&(calendar.h==h)].iloc[0];frame,labels=prepare_frame(panel,cases.get(experiment,{}));target=labels.shift(-h);ix=pd.PeriodIndex(row.training_origins.split(';'),freq='Q');X=frame.loc[ix,c['columns'][1:]].to_numpy();y=target.loc[ix].to_numpy();Z=np.column_stack([np.ones(len(y)),(X-X.mean(0))/X.std(0)]);saved=np.array(c['firth_standardized'])
  def independent(b):
   eta=Z@b;pr=expit(eta);info=Z.T@((pr*(1-pr))[:,None]*Z);sign,ld=np.linalg.slogdet(info)
   return -float(np.sum(y*eta-np.logaddexp(0,eta))+.5*ld) if sign>0 else 1e100
  start=saved+np.linspace(-.02,.02,len(saved));opt=minimize(independent,start,method='BFGS',options={'gtol':2e-7,'maxiter':500});difference=float(np.max(np.abs(opt.x-saved)));objective_error=abs(independent(opt.x)-independent(saved));num=approx_fprime(saved,independent,1e-6);analytic=-objective_score(saved,Z,y)[1]
  eta=Z@opt.x;alpha=brentq(lambda x:float(expit(eta+x).sum()-y.sum()),-80,80);predx=frame.loc[pd.Period(origin),c['columns'][1:]].to_numpy();z=np.r_[1,(predx-X.mean(0))/X.std(0)];prob=expit(z@opt.x+alpha);savedp=f[(f.experiment==experiment)&(f.h==h)&(f.origin==origin)&(f.model==model)].probability.iloc[0]
  samples.append({'experiment':experiment,'origin':origin,'model':model,'h':h,'max_parameter_error':difference,'objective_error':objective_error,'probability_error':abs(prob-savedp),'gradient_check_error':float(np.max(np.abs(num-analytic)))})
 ck('independent_generic_optimizer_agrees',all(x['objective_error']<1e-8 and x['probability_error']<2e-6 and x['max_parameter_error']<2e-5 for x in samples),samples)
 ck('penalty_gradient_numerical_check',max(x['gradient_check_error'] for x in samples)<2e-4)
 # Change all future numeric data aggressively: previously dated forecasts must not change.
 mutation=[]
 for origin in ['2008Q3','2019Q4','2023Q4']:
  mutated=panel.copy();q=pd.Period(origin);numeric=mutated.select_dtypes(include='number').columns;mutated.loc[mutated.index>q,numeric]=mutated.loc[mutated.index>q,numeric]*1000+777
  with contextlib.redirect_stdout(io.StringIO()):new,_,_=run_group(mutated,spec,spec['experiments'][0],only_origins=[origin])
  old=f[(f.experiment=='core_long')&(f.origin==origin)];join=new.merge(old,on=['experiment','h','origin','model'],suffixes=('_mutated','_old'));err=float((join.probability_mutated-join.probability_old).abs().max());mutation.append({'origin':origin,'probability_error':err})
 ck('future_data_mutation_cannot_change_past_forecasts',max(x['probability_error'] for x in mutation)<1e-11,mutation)
 # Distinguish an actual responding model from a frozen/static output.
 c=cd[('core_long',1,'2019Q4','EU_CREDIT')];credit_index=c['columns'].index('credit_lag');ck('model_has_nonzero_US_response',abs(c['coefficients'][credit_index])>1e-8)
 pairs=pd.read_csv(O/'paired_comparisons.csv');ck('paired_comparison_intervals_finite_and_ordered',np.isfinite(pairs[['difference','ci_low','ci_high','skill']]).all().all() and (pairs.ci_low<=pairs.ci_high).all());ck('bootstrap_replication_count_frozen',pairs.bootstrap_replicates.eq(spec['bootstrap']['replicates']).all())
 # Independent mean loss differences; interval resampling does not alter mean estimates.
 expected=[]
 for x in pairs.itertuples():
  a=f[(f.experiment==x.experiment)&(f.h==x.h)&(f.model==x.model)].brier.mean();b=f[(f.experiment==x.experiment)&(f.h==x.h)&(f.model==x.benchmark)].brier.mean();expected.append(abs((a-b)-x.difference))
 ck('comparison_means_recomputed',max(expected)<1e-12)
 result={'passed':all(checks.values()),'checks_count':len(checks),'checks':checks,'details':details,'forecasts':len(f),'fits':len(coeff),'protected_documents':len(spec['protected_documents_sha256']),'scope':'internal arithmetic, source provenance, solver and chronology; does not convert late-history data into point-in-time observations'}
 (P/'checks/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['passed','checks_count','forecasts','fits','protected_documents']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
