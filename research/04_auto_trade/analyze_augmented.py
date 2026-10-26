"""Country-entry margins, model contrasts, research diagnostics and integrity.

No firm/model entry or causal effects inferred from customs-entry countries.
"""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/augmented';FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
def read(name):return json.loads((OUT/name).read_text())
annual=pd.read_csv(ROOT/'results/full/annual_member_flows.csv')
cn=annual[annual.origin=='CN'];rows=[]
for start in [2023,2024]:
    for cat in ['BEV','PHEV','HEV']:
        for outcome in ['quantity','value_eur']:
            a=cn[(cn.year==start)&(cn.category==cat)].set_index('reporter')[outcome].sort_index()
            b=cn[(cn.year==2025)&(cn.category==cat)].set_index('reporter')[outcome].reindex(a.index)
            continuing=(a>0)&(b>0);new=(a==0)&(b>0);exit_=(a>0)&(b==0)
            intensive=float((b[continuing]-a[continuing]).sum());entry=float(b[new].sum());exits=-float(a[exit_].sum())
            delta=float(b.sum()-a.sum());err=delta-intensive-entry-exits;assert abs(err)<.001
            rows.append({'start':start,'end':2025,'category':cat,'outcome':outcome,'total_start':float(a.sum()),'total_end':float(b.sum()),
                         'change':delta,'continuing_country_change':intensive,'new_positive_country_component':entry,'exited_country_component':exits,
                         'active_countries_start':int((a>0).sum()),'active_countries_end':int((b>0).sum()),
                         'new_countries':','.join(a.index[new]),'exited_countries':','.join(a.index[exit_]),'identity_error':err})
pd.DataFrame(rows).to_csv(OUT/'country_entry_margin.csv',index=False)

# Mechanical clearance-jurisdiction exposure, not a port-closure/sales forecast.
end=cn[cn.year==2025];exposure=[]
for cat in ['BEV','PHEV','HEV']:
    x=end[end.category==cat];q=x.quantity.sum();gate=x.loc[x.reporter.isin(['BE','NL']),'quantity'].sum()
    for shock in [.10,.25]:
        exposure.append({'year':2025,'category':cat,'assumed_fraction_disrupted_in_BE_NL_clearance':shock,
                         'BE_NL_registered_units':int(gate),'EU_registered_units':int(q),'mechanically_exposed_units':gate*shock,
                         'share_of_total_units_pct':gate*shock/q*100,
                         'assumptions':'Fixed2025 registration geography, no rerouting, no inventory or demand response. Customs jurisdiction is not the physical port route. Exposure is not lost sales or a causal tariff scenario.'})
pd.DataFrame(exposure).to_csv(OUT/'clearance_jurisdiction_exposure.csv',index=False)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
co=pd.read_csv(OUT/'coefficients.csv');models=[('rest_preferred','Все остальные поставщики: полная модель'),('rest_no_trend','Без линейных трендов'),('rest_no_season','Без специальной сезонности'),('four_origin_augmented','Сравнение: только JP/KR/US'),('rest_since2022','Окно с 2022 года'),('rest_exclude_BE_NL','Исключены BE/NL'),('rest_observed_only','Только опубликованные исходные пары')]
fig,axes=plt.subplots(1,2,figsize=(12.2,5.1),sharey=True,layout='constrained')
for ax,cat,color in zip(axes,['PHEV','HEV'],['#1673a5','#b35b16']):
    for i,(model,label) in enumerate(models):
        r=co[(co.model==model+'_quantity')&(co.term==cat+'__definitive')].iloc[0]
        ax.errorbar(r.multiplier,len(models)-i-1,xerr=np.array([[r.multiplier-r.hac12_lo],[r.hac12_hi-r.multiplier]]),fmt='o',color=color,capsize=3)
    ax.set_xscale('log');ax.axvline(1,color='#777777',ls='--');ax.grid(axis='x',alpha=.2)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v,p:f'{v:g}'));ax.set_xlabel(cat+' / BEV: относительный множитель')
axes[0].set_yticks(np.arange(len(models)),[x[1] for x in reversed(models)])
fig.supxlabel('Окончательная фаза: ноябрь 2024 — декабрь 2025. Количество, 95% HAC(12). Условные связи; базовые периоды и наборы контролей указаны в спецификациях.',fontsize=9)
for suffix in ['png','svg']:fig.savefig(FIG/('01_augmented_sensitivity.'+suffix),dpi=180,bbox_inches='tight')
plt.close(fig)

# Half-year diagnostics compare to the same half-year in2022; both reference
# halves omitted to identify seasonal effects. Pre-investigation terms marked.
dyn=read('rest_halfyear_quantity.json');c={x['term']:x for x in dyn['coefficients']};periods=[f'{y}H{h}' for y in range(2021,2026) for h in [1,2]]
fig,axes=plt.subplots(2,1,figsize=(11.8,6.5),sharex=True,layout='constrained')
for ax,cat,color in zip(axes,['PHEV','HEV'],['#1673a5','#b35b16']):
    b=[];lo=[];hi=[]
    for period in periods:
        if period.startswith('2022'):beta=l=h=0
        else:
            r=c[cat+'__'+period];beta=r['beta'];l,h=r['hac12']['beta_ci95']
        b.append(beta);lo.append(l);hi.append(h)
    x=np.arange(10);ax.errorbar(x,b,yerr=[np.array(b)-lo,np.array(hi)-b],fmt='o-',color=color,capsize=3,label=cat+' / BEV, CN относительно остальных')
    ax.axhline(0,color='#555555',lw=.8);ax.axvspan(1.65,3.35,color='#bbbbbb',alpha=.15,label='Базовый 2022 год')
    ax.axvline(5.0,color='#777777',ls=':',label='2023H2 содержит сигнал расследования')
    ax.axvline(7,color='#555555',ls='--',label='2024H2 содержит введение окончательных мер')
    ax.set_ylabel('Логарифм относительного\nмножителя');ax.legend(frameon=False,fontsize=8,loc='upper left');ax.grid(axis='y',alpha=.2)
axes[-1].set_xticks(np.arange(10),periods)
fig.supxlabel('Сравнение с соответствующим полугодием 2022 года. Учтена сезонность происхождение × категория. Диагностика динамики, не причинный эффект.',fontsize=9)
for suffix in ['png','svg']:fig.savefig(FIG/('02_halfyear_diagnostics.'+suffix),dpi=180,bbox_inches='tight')
plt.close(fig)

checks={};fp=hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in ['augmented_model_spec.json','ppml_engine_augmented.py','run_augmented_model.py','results/full/panel.csv'])).hexdigest()
audit=read('data_audit.json');checks['broad_panel_complete_and_nonnegative']=audit['rows']==9720 and audit['unknown_indicators']==audit['quantity_negative']==audit['value_negative']==0
checks['CN_plus_REST_exactly_extraEU']=audit['exact_reconstruction_quantity'] and audit['exact_reconstruction_value']
checks['all_18_specifications_estimated']=len(read('fit_errors.json'))==0 and co.model.nunique()==18
model_paths=[OUT/(name+'.json') for name in sorted(co.model.unique())];maxerr=0
for path in model_paths:
    j=json.loads(path.read_text());assert j['fingerprint']==fp and j['converged']
    assert j['separation']['positive_outcome_removed']==0
    maxerr=max(maxerr,j['max_fe_score_over_total_y'],j['max_x_score_over_total_y'])
checks['all_model_scores_small']=maxerr<1e-8
amend=json.loads((ROOT/'augmented_model_spec.json').read_text())['technical_amendment']
maxdiff=0
for suffix in ['quantity','value']:
    prior=np.array([c['beta'] for c in amend['initial_preferred_coefficients'][suffix]])
    current=np.array([c['beta'] for c in read('rest_preferred_'+suffix+'.json')['coefficients']])
    maxdiff=max(maxdiff,float(np.max(np.abs(prior-current))))
checks['dynamic_normalization_did_not_change_preferred_coefficients']=maxdiff<1e-10
checks['new_numerical_implementation_verified']=read('numerical_validation.json')['passed']
checks['full_informative_panel_share_equivalence']=read('conditional_share_equivalence.json')['passed']
draws=read('paired_block_draws.json')['draws'];checks['398_successful_weighted_refits']=len(draws)==398 and all(d['success'] for d in draws)
checks['199_paired_draws']=read('paired_block_summary.json')['paired_ratio_of_mean_indices']['successful_pairs']==199
checks['bootstrap_scores_small']=max(d.get('score_error',np.inf) for d in draws)<1e-8
checks['entry_margin_identity']=all(abs(r['identity_error'])<.001 for r in rows)
checks['original_baseline_validation_still_passes']=json.loads((ROOT/'results/full/output_validation.json').read_text())['passed']
base_fp=hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in ['full_model_spec.json','ppml_engine.py','results/full/panel.csv'])).hexdigest()
checks['baseline_source_and_engine_unchanged']=base_fp==json.loads((ROOT/'results/full/output_validation.json').read_text())['fingerprint']
result={'passed':all(checks.values()),'checks':checks,'fingerprint':fp,'specifications':18,'weighted_refits':398,'max_relative_score':maxerr,
        'max_preferred_beta_difference_after_normalization_correction':maxdiff,'interpretation':'Numerical/data validation, not acceptance of parallel trends, causality or publication priority.'}
(OUT/'output_validation.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'],result
print(json.dumps(result,indent=2),flush=True)
print(pd.DataFrame(rows).query('start==2023 and outcome=="quantity"').to_string(index=False),flush=True)
