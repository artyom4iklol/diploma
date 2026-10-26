"""Exact category/geography accounting and observational coverage diagnostics.

These are identities in published imports, not estimated causal effects.
"""
from pathlib import Path
import itertools, json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/full'
spec=json.loads((ROOT/'full_model_spec.json').read_text())
d=pd.read_csv(OUT/'panel.csv',keep_default_na=False)
for col in ['quantity','value_eur','quantity_raw','value_eur_raw']:d[col]=pd.to_numeric(d[col],errors='coerce')
d['year']=d.month.str[:4].astype(int)
national=d[d.reporter!='EU27_2020'].copy();aggregate=d[d.reporter=='EU27_2020'].copy()
annual=national.groupby(['reporter','origin','category','year'])[['quantity','value_eur']].sum().reset_index()
annual['customs_eur_per_vehicle']=np.divide(annual.value_eur,annual.quantity,out=np.full(len(annual),np.nan),where=annual.quantity>0)
annual.to_csv(OUT/'annual_member_flows.csv',index=False)
agg=aggregate.groupby(['origin','category','year'])[['quantity','value_eur']].sum().reset_index()
agg['customs_eur_per_vehicle']=agg.value_eur/agg.quantity
agg.to_csv(OUT/'annual_eu_flows.csv',index=False)

decompositions=[];geography=[]
reporters=spec['reporters'];categories=['BEV','PHEV','HEV']
for outcome,start,end in itertools.product(['quantity','value_eur'],[2023,2024],[2025]):
    def matrix(origin,year):
        q=annual[(annual.origin==origin)&(annual.year==year)].pivot(index='reporter',columns='category',values=outcome)
        return q.reindex(index=reporters,columns=categories).to_numpy(float)
    C=[matrix('CN',yr) for yr in [start,end]];E=[matrix('EXT_EU27_2020',yr) for yr in [start,end]]
    assert all(np.all(c<=e) for c,e in zip(C,E))
    # EU-wide two-factor symmetric Kitagawa identity.
    cc=[c.sum(axis=0) for c in C];ee=[e.sum(axis=0) for e in E]
    w=[e/e.sum() for e in ee];s=[c/e for c,e in zip(cc,ee)]
    within=(w[0]+w[1])/2*(s[1]-s[0]);mix=(s[0]+s[1])/2*(w[1]-w[0])
    total=C[1].sum()/E[1].sum()-C[0].sum()/E[0].sum()
    # Three-factor Shapley, averaging all six substitution orders:
    # EU share = sum_m a_m sum_p b_mp s_mp.
    aa=[e.sum(axis=1)/e.sum() for e in E]
    bb=[np.divide(e,e.sum(axis=1)[:,None],out=np.zeros_like(e),where=e.sum(axis=1)[:,None]>0) for e in E]
    ss=[np.divide(c,e,out=np.zeros_like(c),where=e>0) for c,e in zip(C,E)]
    def shapley(shares):
        factors=[aa,bb,shares];answer=np.zeros((3,len(reporters),len(categories)))
        def contribution(states):return factors[0][states[0]][:,None]*factors[1][states[1]]*factors[2][states[2]]
        for order in itertools.permutations(range(3)):
            states=[0,0,0];old=contribution(states)
            for component in order:
                states[component]=1;new=contribution(states)
                answer[component]+=(new-old)/6;old=new
        return answer
    components=shapley(ss)
    # An undefined share in a zero-denominator cell has no observed level
    # contribution but can affect counterfactual factor attribution. Bound
    # each unknown endpoint share independently over [0,1], using linearity.
    base=components.sum(axis=(1,2));lower=base.copy();upper=base.copy()
    for endpoint in [0,1]:
        for i,j in zip(*np.where(E[endpoint]==0)):
            alternate=[v.copy() for v in ss];alternate[endpoint][i,j]=1
            delta=shapley(alternate).sum(axis=(1,2))-base
            lower+=np.minimum(delta,0);upper+=np.maximum(delta,0)
    error=float(total-components.sum())
    assert abs(error)<1e-12
    record={'outcome':outcome,'start':start,'end':end,'china_share_start_pct':float(C[0].sum()/E[0].sum()*100),
            'china_share_end_pct':float(C[1].sum()/E[1].sum()*100),'change_pp':float(total*100),
            'two_factor':{'within_category_pp':float(within.sum()*100),'category_mix_pp':float(mix.sum()*100),
                          'components':[{'category':cat,'within_pp':float(within[j]*100),'mix_pp':float(mix[j]*100)} for j,cat in enumerate(categories)],
                          'identity_error_pp':float((total-within.sum()-mix.sum())*100)},
            'three_factor_shapley':{'geographic_entry_mix_pp':float(components[0].sum()*100),'within_entry_category_mix_pp':float(components[1].sum()*100),
                                    'china_shares_within_entry_category_pp':float(components[2].sum()*100),'identity_error_pp':error*100,
                                    'zero_denominator_convention':'Zero baseline share, with sharp componentwise bounds allowing each undefined share independently in [0,1]. Bounds across components are not simultaneously additive.',
                                    'component_bounds_pp':{name:[float(lower[j]*100),float(upper[j]*100)] for j,name in enumerate(['geographic_entry_mix','within_entry_category_mix','china_shares_within_entry_category'])}},
            'interpretation':'CN country of origin; national importer is customs entry, not necessarily consumption. Three selected new-vehicle codes only. Deterministic accounting, no sampling CI or causal interpretation.',
            'zero_denominator_cells':sum(int((e==0).sum()) for e in E)}
    decompositions.append(record)
    for i,reporter in enumerate(reporters):
        for j,cat in enumerate(categories):
            geography.append({'outcome':outcome,'start':start,'end':end,'reporter':reporter,'category':cat,
                              'entry_mix_pp':components[0,i,j]*100,'category_mix_pp':components[1,i,j]*100,'china_share_pp':components[2,i,j]*100})
(OUT/'accounting_decompositions.json').write_text(json.dumps(decompositions,ensure_ascii=False,indent=2)+'\n')
pd.DataFrame(geography).to_csv(OUT/'shapley_member_category_contributions.csv',index=False)

model=national[national.origin.isin(spec['origins'])].copy()
units=model.groupby(['reporter','origin','category']).strictly_observed.agg(['sum','count']).reset_index()
units['balanced_observed']=units['sum']==60;units.to_csv(OUT/'continuing_observed_units.csv',index=False)
bad=(model.quantity==0)&(model.value_eur>0)
audit={'zero_quantity_positive_value':int(bad.sum()),'positive_quantity_zero_value':int(((model.quantity>0)&(model.value_eur==0)).sum()),
       'national_positive_quantity_rows':int((model.quantity>0).sum()),'national_zero_quantity_rows':int((model.quantity==0).sum()),
       'observed_only_positive_trade_mass_quantity_fraction':float(model.loc[model.strictly_observed,'quantity'].sum()/model.quantity.sum()),
       'observed_only_positive_trade_mass_value_fraction':float(model.loc[model.strictly_observed,'value_eur'].sum()/model.value_eur.sum()),
       'balanced_observed_units':int(units.balanced_observed.sum()),
       'balanced_units_by_origin_category':units[units.balanced_observed].groupby(['origin','category']).size().to_dict(),
       'balanced_sensitivity_limitation':'Full six-term design cannot identify category contrasts when a China hybrid has no continuously positive 60-month unit. Retain as non-estimable, not as support for main result.'}
audit['balanced_units_by_origin_category']={'|'.join(k):int(v) for k,v in audit['balanced_units_by_origin_category'].items()}
(OUT/'observability_details.json').write_text(json.dumps(audit,indent=2)+'\n')

# Period totals and entry-country concentration, with denominator and shares explicit.
rows=[]
for year,cat in itertools.product(range(2021,2026),categories):
    x=annual[(annual.year==year)&(annual.category==cat)&(annual.origin=='CN')]
    for outcome in ['quantity','value_eur']:
        total=x[outcome].sum();ports=x.loc[x.reporter.isin(['BE','NL']),outcome].sum()
        weights=x[outcome].to_numpy()/total
        rows.append({'year':year,'category':cat,'outcome':outcome,'china_total':total,'BE_NL_total':ports,
                     'BE_NL_share_pct':ports/total*100,'entry_HHI':np.sum(weights**2),'effective_entry_countries':1/np.sum(weights**2)})
pd.DataFrame(rows).to_csv(OUT/'entry_concentration.csv',index=False)
value_change=[]
for start in [2023,2024]:
    r0=agg[(agg.origin=='CN')&(agg.year==start)].set_index('category').reindex(categories)
    r1=agg[(agg.origin=='CN')&(agg.year==2025)].set_index('category').reindex(categories)
    dq=r1.quantity.to_numpy()-r0.quantity.to_numpy();du=r1.customs_eur_per_vehicle.to_numpy()-r0.customs_eur_per_vehicle.to_numpy()
    qpart=(r0.customs_eur_per_vehicle.to_numpy()+r1.customs_eur_per_vehicle.to_numpy())/2*dq
    upart=(r0.quantity.to_numpy()+r1.quantity.to_numpy())/2*du
    delta=float(r1.value_eur.sum()-r0.value_eur.sum())
    value_change.append({'start':start,'end':2025,'value_change_eur':delta,'quantity_component_eur':float(qpart.sum()),'within_CN8_customs_unit_value_component_eur':float(upart.sum()),
                         'identity_error_eur':float(delta-qpart.sum()-upart.sum()),
                         'by_category':[{'category':cat,'quantity_component_eur':float(qpart[j]),'unit_value_component_eur':float(upart[j])} for j,cat in enumerate(categories)],
                         'interpretation':'Symmetric two-factor accounting V=sum(q*u). Unit customs value includes model/quality mix, transfer valuation and valuation changes; not a constant-quality price or tariff pass-through effect.'})
(OUT/'china_value_change_accounting.json').write_text(json.dumps(value_change,indent=2)+'\n')
print('ACCOUNTING',json.dumps(decompositions,ensure_ascii=False),flush=True)
print('OBSERVABILITY',json.dumps(audit,ensure_ascii=False),flush=True)
