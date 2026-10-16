"""Calculate complete 2017/2024 weights and full-geography HHI before risk.

These are inputs and concentration results of the fixed design. No covariance
is estimated from the incomplete intervening years.
"""
import hashlib
import json
import numpy as np
import pandas as pd
from analyze_monthly import ROOT,GOODS,STATES,REPORTERS,full_hhi_states,shapley


def main():
    monthly=ROOT/'results/monthly'
    out=ROOT/'results/endpoint_check'
    years=[2017,2024]
    quality=json.loads((monthly/'data_quality.json').read_text())
    path=ROOT/'data/monthly_panel_full.csv.gz'
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha==quality['monthly_panel_sha256'],'Panel changed after quality control'
    coverage=pd.read_csv(monthly/'year_coverage.csv')
    coverage=coverage[coverage.refYear.isin(years)]
    assert len(coverage)==4 and coverage.months_all_products.eq(12).all(),'Endpoint years incomplete'
    requests=pd.read_csv(monthly/'request_checks.csv')
    requests=requests[requests.frequency.eq('M')&(requests.period//100).isin(years)]
    assert len(requests)==288 and requests.status.eq('ok').all()
    world=pd.read_csv(monthly/'product_world_reconciliation.csv')
    world=world[(world.period//100).isin(years)]
    assert len(world)==48 and world['pass'].all()
    partners=pd.read_csv(monthly/'product_partner_reconciliation.csv')
    partners=partners[(partners.period//100).isin(years)]
    assert len(partners)>0 and partners['pass'].all()
    data=pd.read_csv(path)
    data=data[data.refYear.isin(years)].copy()
    product_rows=[];destination_rows=[];state_rows=[];summary=[]
    for reporter in REPORTERS:
        for year in years:
            d=data[data.reporterCode.eq(reporter)&data.refYear.eq(year)&data.cmdCode.isin(GOODS)&data.partnerCode.ne(0)]
            total=float(d.primaryValue.sum())
            products=d.groupby('cmdCode').primaryValue.sum()
            for cmd,value in products.items():
                product_rows.append(dict(reporter=reporter,year=year,cmdCode=int(cmd),value_usd=float(value),share=float(value/total)))
            destinations=d.groupby('partnerCode').primaryValue.sum()
            for destination,value in destinations.items():
                destination_rows.append(dict(reporter=reporter,year=year,partnerCode=int(destination),value_usd=float(value),share=float(value/total)))
        hhi=np.array(full_hhi_states(data,reporter,GOODS,2017,2024))
        for state,value in zip(STATES,hhi):
            state_rows.append(dict(reporter=reporter,state=state,hhi_all_destinations=float(value)))
        delta,mix,geo=shapley(hhi)
        summary.append(dict(reporter=reporter,initial_year=2017,final_year=2024,
            hhi_initial=float(hhi[0]),hhi_final=float(hhi[3]),delta_hhi=float(delta),
            mix_hhi=float(mix),geography_hhi=float(geo),risk_estimated=False))
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('product_weights',product_rows),('destination_weights',destination_rows),('hhi_states',state_rows),('summary',summary)]:
        pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    metadata=dict(scope='Complete endpoint inputs and full-geography concentration; no risk estimate',
        main_analysis_ready=quality['analysis_ready'],source_panel_sha256=sha,
        protocol_sha256=quality['protocol_sha256'],source_request_cells=288,
        complete_country_months=48,years=years,goods=list(GOODS),risk_estimated=False,summary=summary)
    (out/'validation.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
