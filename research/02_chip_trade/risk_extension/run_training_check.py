"""Calculate the prespecified 2018–2020 training comparison when that slice is complete.

Outputs are separate from the main 2017/2024 comparison. No late weights, extra
hypotheses, or replacement of the main period are introduced here.
"""
import hashlib
import json
from pathlib import Path
import pandas as pd
from analyze_monthly import ROOT,GOODS,choose_directions,run_case


def main():
    monthly=ROOT/'results/monthly'
    out=ROOT/'results/training_check'
    quality=json.loads((monthly/'data_quality.json').read_text())
    panel_path=ROOT/'data/monthly_panel_full.csv.gz'
    sha=hashlib.sha256(panel_path.read_bytes()).hexdigest()
    assert sha==quality['monthly_panel_sha256'],'Panel changed after quality control'
    requests=pd.read_csv(monthly/'request_checks.csv')
    requests=requests[requests.frequency.eq('M')&requests.period.between(201701,202012)]
    assert len(requests)==576 and requests.status.eq('ok').all(),'Training requests are incomplete'
    world=pd.read_csv(monthly/'product_world_reconciliation.csv')
    world=world[world.period.between(201701,202012)]
    assert len(world)==96 and world['pass'].all(),'Training product totals do not reconcile'
    partners=pd.read_csv(monthly/'product_partner_reconciliation.csv')
    partners=partners[partners.period.between(201701,202012)]
    assert len(partners)>0 and partners['pass'].all(),'Training partner totals do not reconcile'
    data=pd.read_csv(panel_path)
    data=data[data.period.between(201701,202012)].copy()
    directions,details=choose_directions(data,GOODS,8,2020,selection_end=2020)
    result=run_case(data,'temporal_2018_2020',end_year=2020,final_year=2020,
                    sigma_start=2018,sigma_end=2020,directions=directions)
    result['grid']=[dict(case='temporal_2018_2020',**row) for row in details]
    out.mkdir(parents=True,exist_ok=True)
    for name in ['states','summary','drivers','series','components','checks','grid']:
        pd.DataFrame(result[name]).to_csv(out/f'{name}.csv',index=False)
    metadata=dict(scope='Prespecified initial-window check only; not main 2017/2024 result',
        main_analysis_ready=quality['analysis_ready'],source_panel_sha256=sha,
        protocol_sha256=quality['protocol_sha256'],source_request_cells=576,
        complete_country_months=96,weight_years=[2017,2020],covariance_years=[2018,2020],
        bootstrap_intervals_computed=False,causal_identification=False,
        summary=result['summary'])
    (out/'validation.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
