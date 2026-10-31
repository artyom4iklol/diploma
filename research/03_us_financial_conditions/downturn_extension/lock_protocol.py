"""Freeze choices and input fingerprints before estimating new downturn models."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
R=P.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 if (P/'protocol_lock.json').exists():
  print('Protocol already fixed; no overwrite.');return
 spec={
  'date':'2026-10-31','author':'Суховерхов Артем','status':'fixed before new binary-model estimation; informed by the earlier GaR study and source feasibility, not external preregistration',
  'question':'Do US financial indicators improve out-of-sample probabilities of a quarterly euro-area GDP contraction beyond matched European predictors?',
  'primary_contrast':{'experiment':'core_long','horizon':1,'model':'EU_CREDIT','benchmark':'EU','metric':'Brier score','hypothesis':'lower expected out-of-sample Brier loss'},
  'area_main':'EA21 fixed-area late reconstructed AWMD September 2026; ECFIN October 2026 EA aggregate includes Bulgaria retrospectively; no splice with moving-area GDP',
  'area_robustness':'AWMD EA21 excluding Ireland GDP, same original full-area financial controls, explicitly a GDP-target sensitivity',
  'target':'100*log(YER[q]/YER[q-1]) < 0, at the specific future quarter q=t+h, not any contraction over the intervening h quarters',
  'target_end':'2025Q4','forecast_origins_start':'2006Q4','horizons':[1,4],
  'issue_rule':'end of origin quarter t; all main predictors through t-1; latest permissible training GDP target t-1; late-history hindcast with conservative one-quarter availability convention, not observed release vintages',
  'training_start':'1970Q1','training_min_rows':40,'training_min_each_class':3,
  'financial_primary_lag':1,'gdp_lag':1,'window':'expanding',
  'us_curve':'GS10 - TB3MS, monthly series averaged over three months; bill is on discount basis; this is a defined long-history proxy, not official constant-maturity T10Y3MM',
  'us_credit':'BAA10YM monthly, three-month mean','equity':'100*log(mean monthly EURO STOXX 50 level this quarter / preceding quarter); price-index change, not dividend return',
  'vix':'arithmetic mean of nonmissing daily closes per quarter','new_ciss':'arithmetic mean of nonmissing ECB daily NEW CISS; not the legacy weekly indicator; retrospective control',
  'estimator':'Firth logistic regression with FLIC intercept correction, training-only standardisation, no hyperparameter/model/lag search',
  'estimator_settings':{'max_iter':150,'tolerance':1e-8,'probability_clip_logloss':1e-12},
  'baseline_frequency':'(positives+0.5)/(n+1), fixed Jeffreys smoothing',
  'warning_threshold':0.20,'warning_status':'illustrative fixed probability threshold, not an estimated economic optimum',
  'bootstrap':{'replicates':4999,'seed':20261031,'method':'paired circular moving blocks of realised loss differences; conditional on saved forecasts, no refit','lengths_quarters':[4,8],'confidence':0.95,'scope':'uncertainty of the realised average loss comparison; limited by few episodes, not a causal or universal performance interval'},
  'secondary_family':'within each experiment, three US alternatives x two horizons; Holm-adjusted centred-bootstrap p-values; all intervals also shown',
  'experiments':[
   {'name':'core_long','start':'1970Q1','base':['gdp_lag','eu_curve_lag'],'additions':{'EU_CREDIT':['credit_lag'],'EU_CURVE':['us_curve_lag'],'EU_BOTH':['credit_lag','us_curve_lag']}},
   {'name':'europe_esi','start':'1985Q1','base':['gdp_lag','eu_curve_lag','esi_lag'],'additions':{'EU_CREDIT':['credit_lag'],'EU_CURVE':['us_curve_lag'],'EU_BOTH':['credit_lag','us_curve_lag']}},
   {'name':'europe_equity','start':'1990Q1','base':['gdp_lag','eu_curve_lag','esi_lag','equity_lag'],'additions':{'EU_CREDIT':['credit_lag'],'EU_CURVE':['us_curve_lag'],'EU_VIX':['vix_lag']}},
   {'name':'europe_stress','start':'1990Q1','base':['gdp_lag','esi_lag','equity_lag','ciss_lag'],'additions':{'EU_CREDIT':['credit_lag'],'EU_CURVE':['us_curve_lag'],'EU_VIX':['vix_lag']}},
   {'name':'current_indices','start':'1995Q1','first_origin':'2011Q2','base':['gdp_lag','eu_curve_lag','esi_lag','equity_lag'],'additions':{'EU_NFCI':['nfci_lag'],'EU_ANFCI':['anfci_lag']}},
  ],
  'refit_sensitivities':[
   {'name':'short_training_1985','start':'1985Q1'},
   {'name':'rolling_80','window':80},
   {'name':'market_current_quarter','financial_lag':0,'status':'retrospective potential-information sensitivity; reconstructed market aggregates not proof of actual publication by origin close'},
   {'name':'gdp_ex_ireland','gdp':'exIreland'},
   {'name':'contraction_below_minus_0_1','threshold':-0.1},
   {'name':'cepr_recession','target':'cepr','status':'today-dated CEPR quarters for both training and evaluation; labels may not have been announced at origin; retrospective robustness only'},
  ],
  'evaluation_slices':['all','exclude_2020Q1_Q2','gfc_2008Q2_2009Q2','debt_2011Q4_2013Q1','pandemic_2020Q1_Q2','2022_2025'],
  'archival_exercise':{'inputs':'inherited independently checked ECB RTD/ALFRED revision30 cube and release calendars','issue':'15 days after stored feature-origin r ends, in quarter r+1','target':'r+1+h, so first entirely future quarter, horizons 1 and 4','training_last_target':'r-1, source GDP available in inherited snapshot','training_start':'1995Q3','gdp':'within each origin vintage, not late-history AWM','evaluation_fact':'same inherited GDP assessment at six-month maturity where available; labels for new future-quarter mapping; no four-quarter cumulative growth target','scope':'own moving-area experiment; comparison with matched late-index counterpart changes only NFCI/ANFCI versions, not GDP/ESI/EQ, training rows or facts; not pooled with EA21 experiment'},
  'required_checks':['raw hashes','GDP/source reconciliation','area mapping','missing not zero','one row per quarter','training target and features never future','common samples within experiment','solver adjusted score and calibration','independent optimizer refit','future-data mutation invariance','probabilities and loss arithmetic','paired dates for intervals','untouched existing manuscripts and model results'],
  'interpretation':'forecast association, not causal effect; no result-driven period/model switch; primary benefit over a small base must also be assessed against stronger European bases and a frequency benchmark',
 }
 inherited=['revision30/results/equity_model_frames.csv','revision18/results/forecast_calendar_59.csv','revision18/results/evaluation_targets.csv','revision19/results/ANFCI_calendar_59.csv','revision30/results/equity_calendar.csv']
 inputs={str(p.relative_to(R)):sha(p) for p in (P/'data/raw').iterdir() if p.is_file()}
 inputs.update({n:sha(R/n) for n in inherited})
 protected={str(p.relative_to(R.parent.parent)):sha(p) for p in R.parent.parent.rglob('*.docx') if 'downturn_extension' not in p.parts}
 spec['input_sha256']=inputs
 spec['protected_documents_sha256']=protected
 text=json.dumps(spec,ensure_ascii=False,indent=2)+'\n'
 (P/'protocol_lock.json').write_text(text)
 (P/'protocol_lock.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'\n')
 print('Frozen protocol:',len(inputs),'input files;',len(protected),'protected Word documents.')

if __name__=='__main__':main()
