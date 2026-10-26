"""Sharpen the question with exact concentration accounting, not new regressions.

All three categories, both quantity/value, and both2023/2024 baselines retained.
These are post-analysis descriptive decompositions of observed customs entry.
"""
from pathlib import Path
import itertools, json, math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/geography_focus';OUT.mkdir(exist_ok=True)
a=pd.read_csv(ROOT/'results/full/annual_member_flows.csv')
a=a[a.origin=='CN'];reporters=sorted(a.reporter.unique());categories=['BEV','PHEV','HEV']
ports=np.array([r in ['BE','NL'] for r in reporters]);assert ports.sum()==2 and (~ports).sum()==25

def matrix(year,outcome):
    return a[a.year==year].pivot(index='reporter',columns='category',values=outcome).reindex(index=reporters,columns=categories).to_numpy(float)

def shapley(v0,v1,fun):
    out=np.zeros(len(v0));divisor=math.factorial(len(v0))
    for order in itertools.permutations(range(len(v0))):
        values=[v.copy() if hasattr(v,'copy') else v for v in v0];before=fun(values)
        for j in order:
            values[j]=v1[j];after=fun(values);out[j]+=(after-before)/divisor
            before=after
    return out

# H(pool)=sum_m[sum_p b_p*g_mp]^2. Two factors: category weights and
# within-category country shares. Standardisation is not a no-tariff world.
pooled=[];by_category=[]
for outcome,start in itertools.product(['quantity','value_eur'],[2023,2024]):
    x0=matrix(start,outcome);x1=matrix(2025,outcome)
    b0=x0.sum(axis=0)/x0.sum();b1=x1.sum(axis=0)/x1.sum()
    g0=x0/x0.sum(axis=0);g1=x1/x1.sum(axis=0)
    fun=lambda vals:float(np.sum((vals[1]@vals[0])**2))
    h00=fun([b0,g0]);h10=fun([b1,g0]);h01=fun([b0,g1]);h11=fun([b1,g1])
    mix=.5*((h10-h00)+(h11-h01));geo=.5*((h01-h00)+(h11-h10));err=h11-h00-mix-geo
    assert abs(err)<1e-12
    assert np.allclose(shapley([b0,g0],[b1,g1],fun),[mix,geo],atol=1e-12,rtol=0)
    assert all(1/27-1e-12<=h<=1+1e-12 for h in [h00,h10,h01,h11])
    pooled.append({'outcome':outcome,'start':start,'end':2025,'HHI_start':h00,'HHI_end':h11,'HHI_change':h11-h00,
                   'product_mix_component':mix,'within_product_geography_component':geo,
                   'fixed_start_product_mix_end_geography_HHI':h01,'end_product_mix_fixed_start_geography_HHI':h10,
                   'product_mix_change_at_start_geography':h10-h00,'product_mix_change_at_end_geography':h11-h01,
                   'geography_change_at_start_mix':h01-h00,'geography_change_at_end_mix':h11-h10,
                   'unallocated_interaction':h11-h10-h01+h00,
                   'effective_entry_countries_start':1/h00,'effective_entry_countries_end':1/h11,'identity_error':err})
    for j,cat in enumerate(categories):
        vec0=x0[:,j];vec1=x1[:,j];v=[]
        for x in [vec0,vec1]:
            total=x.sum();p=x[ports].sum();o=x[~ports].sum()
            assert total>0 and p>0 and o>0,'Group concentration not observed; do not impute'
            v.append([float(p/total),float(np.sum((x[ports]/p)**2)),float(np.sum((x[~ports]/o)**2))])
        f=lambda vals:vals[0]**2*vals[1]+(1-vals[0])**2*vals[2]
        c=shapley(v[0],v[1],f);h0=f(v[0]);h1=f(v[1]);error=h1-h0-c.sum()
        assert abs(error)<1e-12
        assert abs(h0-np.sum((vec0/vec0.sum())**2))<1e-12
        assert abs(h1-np.sum((vec1/vec1.sum())**2))<1e-12
        by_category.append({'outcome':outcome,'start':start,'end':2025,'category':cat,'HHI_start':h0,'HHI_end':h1,'HHI_change':h1-h0,
                            'BE_NL_share_start':v[0][0],'BE_NL_share_end':v[1][0],
                            'BE_NL_within_HHI_start':v[0][1],'BE_NL_within_HHI_end':v[1][1],
                            'other25_within_HHI_start':v[0][2],'other25_within_HHI_end':v[1][2],
                            'between_groups_share_component':float(c[0]),'within_BE_NL_concentration_component':float(c[1]),
                            'within_other25_concentration_component':float(c[2]),'identity_error':float(error)})
pd.DataFrame(pooled).to_csv(OUT/'pooled_HHI_product_geography.csv',index=False)
pd.DataFrame(by_category).to_csv(OUT/'category_HHI_group_shapley.csv',index=False)
margin=pd.read_csv(ROOT/'results/augmented/country_entry_margin.csv');q=margin[(margin.start==2023)&(margin.outcome=='quantity')].copy()
q['new_country_fraction_of_net_change']=np.where(q.change!=0,q.new_positive_country_component/q.change,np.nan)
q.to_csv(OUT/'entry_margin_summary.csv',index=False)
validation={'passed':True,'pooled_decompositions':len(pooled),'category_decompositions':len(by_category),
            'all_pooled_identity_errors_below_1e_minus12':all(abs(x['identity_error'])<1e-12 for x in pooled),
            'all_group_identity_errors_below_1e_minus12':all(abs(x['identity_error'])<1e-12 for x in by_category),
            'all_group_denominators_observed_positive':True,'scale':'HHI on0–1 scale; changes are HHI index points, not percentage points of an import share.',
            'scope':'China-origin customs imports in three selected new-vehicle codes;27 member clearance jurisdictions.',
            'interpretation':'Deterministic accounting, not causal attribution, final demand, firm entry or physical port-route resilience. No sampling confidence intervals invented.',
            'status':'Descriptive refinement after baseline and augmented results; all fixed categories/outcomes/baselines reported.'}
old=pd.read_csv(ROOT/'results/full/entry_concentration.csv')
for r in by_category:
    for endpoint in ['start','end']:
        ref=old[(old.year==r[endpoint])&(old.category==r['category'])&(old.outcome==r['outcome'])].iloc[0]
        assert abs(r['HHI_'+endpoint]-ref.entry_HHI)<1e-12
validation['crosscheck_prior_HHI_passed']=True
(OUT/'decompositions.json').write_text(json.dumps({'pooled':pooled,'by_category':by_category,'validation':validation},indent=2)+'\n')
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps({'pooled_quantity_2023_2025':pooled[0],'category_quantity_2023_2025':by_category[:3],'validation':validation},indent=2))
