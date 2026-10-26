"""Integrity checks for the full calculation, including deliberately weak cases."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/full'
def read(name):return json.loads((OUT/name).read_text())
checks={}
raw=(ROOT/'data/full_raw/eurostat_full.json').read_bytes();request=json.loads((ROOT/'data/full_raw/request.json').read_text())
checks['raw_response_sha256']=hashlib.sha256(raw).hexdigest()==request['response_sha256']
audit=read('data_audit.json');checks['national_grid_complete']=audit['national_model_grid_rows']==19440 and audit['national_paired_available']==19440
checks['zero_reconstruction_exact']=audit['groups_negative_residual']==0 and audit['max_absolute_residual']==0 and audit['unknown_indicators']==0
checks['no_duplicate_keys']=audit['duplicate_keys']==0
observability=read('observability_details.json');checks['value_quantity_consistent']=observability['zero_quantity_positive_value']==observability['positive_quantity_zero_value']==0
fp=hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in ['full_model_spec.json','ppml_engine.py'])+(OUT/'panel.csv').read_bytes()).hexdigest()
models=['primary_quantity','primary_value','since2022_quantity','exclude_BE_NL_quantity','observed_only_quantity','since2022_value','exclude_BE_NL_value','observed_only_value','omit_JP','omit_KR','omit_US','origin_product_trends','investigation_phase','dynamic_quantity','dynamic_value','pretrend_quantity','pretrend_value']
errors=[];max_score=0.;min_eigenvalue=0.
for model in models:
    r=read(model+'.json');assert r['fingerprint']==fp,(model,'input/engine changed')
    assert r['converged'] and r['separation']['positive_outcome_removed']==0
    score=max(r['max_fe_score_over_total_y'],r['max_x_score_over_total_y']);max_score=max(max_score,score)
    if score>1e-8:errors.append(model+' score')
    for cov in r['covariance'].values():
        e=float(np.linalg.eigvalsh((np.array(cov)+np.array(cov).T)/2).min());min_eigenvalue=min(e,min_eigenvalue)
        if e < -1e-7:errors.append(model+' non-PSD HAC')
    for c in r['coefficients']:
        assert np.isfinite(c['beta']) and c['multiplier']>0
        for lag in ['hac6','hac12']:
            lo,hi=c[lag]['beta_ci95'];assert lo<=c['beta']<=hi
checks['all_17_models_numerically_valid']=not errors
checks['balanced_observed_nonidentification_disclosed']=set(read('fit_errors.json'))=={'balanced_observed'} and 'rank deficient' in read('fit_errors.json')['balanced_observed']['error']
b=read('block_bootstrap_draws.json');assert b['fingerprint']==fp
draws=b['draws'];checks['all_398_block_fits_converged']=len(draws)==398 and all(x['success'] for x in draws)
checks['bootstrap_unique_draws']=len({(x['block_length'],x['draw']) for x in draws})==398
checks['bootstrap_first_order_scores']=max(x.get('score_error',np.inf) for x in draws)<1e-8
dec=read('accounting_decompositions.json')
checks['share_decomposition_identities']=all(abs(r['two_factor']['identity_error_pp'])<1e-10 and abs(r['three_factor_shapley']['identity_error_pp'])<1e-10 for r in dec)
contrib=pd.read_csv(OUT/'shapley_member_category_contributions.csv')
for r in dec:
    part=contrib[(contrib.outcome==r['outcome'])&(contrib.start==r['start'])]
    assert abs(part[['entry_mix_pp','category_mix_pp','china_share_pp']].sum().sum()-r['change_pp'])<1e-10
checks['member_category_contributions_add_up']=True
checks['value_change_identity']=all(abs(r['identity_error_eur'])<.01 for r in read('china_value_change_accounting.json'))
for name in ['numerical_validation.json','numerical_validation_national.json']:
    j=read(name);checks[name]=j['independent_sparse_IRLS']['passed'] and j['scale_invariance_passed']
checks['diagnostic_figures_exist']=all((OUT/'figures'/f'{name}.{suffix}').exists() for name in ['01_quantities_and_value_shares','02_dynamic_composition','03_specification_sensitivity'] for suffix in ['png','svg'])
result={'passed':all(checks.values()),'checks':checks,'estimated_specifications':17,'nonestimable_checks':1,'successful_block_refits':398,
        'max_relative_model_score_error':max_score,'smallest_HAC_eigenvalue':min_eigenvalue,'model_errors':errors,'fingerprint':fp,
        'does_not_assert':'Causal identification, constant-quality prices, universal originality, or validity of asymptotic intervals in a one-policy small-origin setting.'}
(OUT/'output_validation.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'],result
print(json.dumps(result,indent=2))
