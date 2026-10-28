"""Deterministic robustness checks for the complete thesis, without new fits.

All cases are reported, including reversals. No source cells, model parameters,
preferred specifications, periods or existing scenario outputs are altered.
"""
from pathlib import Path
import hashlib
import json
import io
import os
import tempfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results/thesis_audit'


def write(path, payload):
    if isinstance(payload, str): payload = payload.encode('utf8')
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(payload); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def concentration(annual, base, outcome, exclude=()):
    countries = sorted(set(annual.reporter)-set(exclude))
    arrays = []
    for year in [base, 2025]:
        a = annual[(annual.year==year)&~annual.reporter.isin(exclude)]
        M = a.pivot(index='reporter', columns='category', values=outcome).reindex(index=countries, columns=['BEV','PHEV','HEV'], fill_value=0).to_numpy(float)
        assert np.all(M>=0) and np.all(M.sum(axis=0)>0)
        b = M.sum(axis=0)/M.sum()
        G = M/M.sum(axis=0)
        arrays.append((b,G))
    H = lambda b,G: float(np.sum((G@b)**2))
    b0,g0 = arrays[0]; b1,g1 = arrays[1]
    h00,h01,h10,h11 = H(b0,g0),H(b0,g1),H(b1,g0),H(b1,g1)
    db = ((h10-h00)+(h11-h01))/2
    dg = ((h01-h00)+(h11-h10))/2
    assert abs(h11-h00-db-dg)<1e-12
    return dict(base=base,end=2025,outcome=outcome,excluded=','.join(exclude),countries=len(countries),h0=h00,h1=h11,change=h11-h00,product_component=db,geography_component=dg)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = ['results/augmented/panel_china_rest.csv','results/augmented/coefficients.csv']
    fingerprints = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources}
    panel = pd.read_csv(ROOT/sources[0]); assert len(panel)==9720
    assert not panel.duplicated(['reporter','origin','category','month']).any()
    panel['year'] = panel.month.str[:4].astype(int)
    cn = panel[panel.origin=='CN']
    annual = cn.groupby(['year','reporter','category'],as_index=False)[['quantity','value_eur']].sum()
    cases=[]; leave=[]
    for base in [2023,2024]:
        for outcome in ['quantity','value_eur']:
            for exclude in [(),('NL',),('BE','NL')]: cases.append(concentration(annual,base,outcome,exclude))
            for country in sorted(cn.reporter.unique()): leave.append(concentration(annual,base,outcome,(country,)))
    write(OUT/'hhi_exclusions.csv',pd.DataFrame(cases).to_csv(index=False))
    write(OUT/'hhi_leave_one_country.csv',pd.DataFrame(leave).to_csv(index=False))
    thresholds=[]
    for base in [2023,2024]:
        for cat in ['PHEV','HEV']:
            a=annual[(annual.year==base)&(annual.category==cat)].set_index('reporter').quantity
            b=annual[(annual.year==2025)&(annual.category==cat)].set_index('reporter').quantity.reindex(a.index)
            delta=b-a; net=float(delta.sum()); assert net>0
            for threshold in [1,10,100,1000]:
                low=a<threshold
                low_change=float(delta[low].sum()); established=float(delta[~low].sum())
                assert abs(low_change+established-net)<1e-10
                thresholds.append(dict(base=base,end=2025,category=cat,baseline_threshold=threshold,baseline_countries_below=int(low.sum()),change_below_threshold=low_change,change_above_threshold=established,total_change=net,fraction_of_change_below_threshold=low_change/net,baseline_quantity_below=float(a[low].sum()),end_quantity_below=float(b[low].sum())))
    write(OUT/'baseline_presence_thresholds.csv',pd.DataFrame(thresholds).to_csv(index=False))
    observability=[]
    for (origin,cat),d in panel.groupby(['origin','category']):
        observability.append(dict(origin=origin,category=cat,rows=len(d),positive_quantity=int((d.quantity>0).sum()),zero_quantity=int((d.quantity==0).sum()),both_source_indicators_observed=int(d.strictly_observed.sum()),quantity_total=float(d.quantity.sum()),value_total=float(d.value_eur.sum())))
    write(OUT/'observability_by_technology.csv',pd.DataFrame(observability).to_csv(index=False))
    co=pd.read_csv(ROOT/sources[1]); selected=co[co.model.isin(['rest_preferred_quantity','rest_preferred_value'])&co.term.str.endswith('__definitive')]
    assert len(selected)==4
    write(OUT/'hac_bandwidth_sensitivity.csv',selected.to_csv(index=False))
    summary={}
    for base in [2023,2024]:
        for outcome in ['quantity','value_eur']:
            d=[x for x in leave if x['base']==base and x['outcome']==outcome]
            summary[f'{base}_{outcome}']={'cases':len(d),'negative_hhi_changes':sum(x['change']<0 for x in d),'positive_hhi_changes':sum(x['change']>0 for x in d),'delta_min':min(x['change']for x in d),'delta_max':max(x['change']for x in d),'geography_component_negative':sum(x['geography_component']<0 for x in d),'positive_cases_excluding':[x['excluded']for x in d if x['change']>0]}
    for p,sha in fingerprints.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha
    result={'date':'2026-10-28','purpose':'Complete diploma audit; post-analysis diagnostics, all cases retained','no_collection':True,'no_model_refits':True,'source_sha256':fingerprints,'leave_one_country_summary':summary,'checks':{'hhi_exclusion_cases':len(cases),'leave_one_country_cases':len(leave),'baseline_threshold_cases':len(thresholds),'observability_groups':len(observability),'hac_cases':len(selected),'adding_up_tolerance':1e-12,'passed':True},'limits':['Exclusions change the estimand and renormalize country and product weights. They do not correct source data.','Leave-one-country results are influence diagnostics, not a sampling distribution or confidence interval.','Baseline thresholds classify the contribution of zero or small initial flows. They do not identify firms or replace the exact positive-flow decomposition.','HAC bandwidth sensitivity reuses saved estimates and does not identify a causal effect.']}
    write(OUT/'audit_summary.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
