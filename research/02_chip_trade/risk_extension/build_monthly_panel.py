"""Build the exact monthly panel and quality tables from byte-verified responses."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from collect_panel import ROOT, CACHE, MANIFEST, restore_bundles, validate, task_id

OUT = ROOT / "results" / "monthly"
HS6 = (854231,854232,854233,854239,854290)


def read_manifest():
    CACHE.mkdir(parents=True,exist_ok=True)
    restore_bundles()
    manifest=json.loads(MANIFEST.read_text())
    return manifest


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=read_manifest()
    records=[];audits=[];bad=[]
    for meta in manifest:
        task=(meta['frequency'],int(meta['reporter']),int(meta['period']),int(meta['cmdCode']))
        key=task_id(*task)
        if 'sha256' not in meta:
            bad.append(key);continue
        raw=gzip.decompress((CACHE/f'{key}.json.gz').read_bytes())
        assert hashlib.sha256(raw).hexdigest()==meta['sha256'],key
        obj=json.loads(raw)
        check=validate(obj,*task,allowed_reporters=meta.get('response_reporters'))
        audits.append(dict(task_id=key,frequency=task[0],reporter=task[1],period=task[2],cmdCode=task[3],**check))
        if check['status']!='ok':
            bad.append(key);continue
        rows=[x for x in obj['data'] if int(x['reporterCode'])==task[1]]
        for x in rows:
            records.append({k:x.get(k) for k in ['freqCode','reporterCode','reporterISO','period','refYear',
                'cmdCode','cmdDesc','classificationCode','partnerCode','partnerISO','partnerDesc',
                'primaryValue','isReported','isAggregate']})
    audit=pd.DataFrame(audits)
    audit.to_csv(OUT/'request_checks.csv',index=False)
    panel=pd.DataFrame(records)
    for column in ['reporterCode','period','refYear','cmdCode','partnerCode']:
        panel[column]=pd.to_numeric(panel[column],errors='raise').astype(int)
    keys=['freqCode','reporterCode','period','cmdCode','partnerCode']
    assert not panel.duplicated(keys).any(),'Duplicate panel key'
    panel=panel.sort_values(keys).reset_index(drop=True)
    monthly=panel[panel.freqCode.eq('M')].copy()
    annual_new=panel[panel.freqCode.eq('A')].copy()
    monthly.to_csv(ROOT/'data/monthly_panel_full.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    annual_new.to_csv(ROOT/'data/annual_2025_collection.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    expected={(r,year*100+month,c) for r in [392,410] for year in range(2017,2026)
              for month in range(1,13) for c in [8542,*HS6]}
    found=set(monthly[['reporterCode','period','cmdCode']].itertuples(index=False,name=None))
    missing=sorted(expected-found)
    pd.DataFrame(missing,columns=['reporterCode','period','cmdCode']).to_csv(OUT/'missing_queries.csv',index=False)
    world=monthly[monthly.partnerCode.eq(0)].pivot(index=['reporterCode','period'],columns='cmdCode',values='primaryValue')
    available=world.dropna(subset=[8542,*HS6]).copy()
    available['leaf_sum_usd']=available[list(HS6)].sum(axis=1)
    available['parent_usd']=available[8542]
    available['absolute_gap_usd']=available.leaf_sum_usd-available.parent_usd
    available['relative_gap']=available.absolute_gap_usd/available.parent_usd
    available['pass']=available.relative_gap.abs().le(1e-6)
    available.reset_index()[['reporterCode','period','leaf_sum_usd','parent_usd','absolute_gap_usd','relative_gap','pass']].to_csv(OUT/'product_world_reconciliation.csv',index=False)
    leaf=monthly[monthly.cmdCode.isin(HS6)].groupby(['reporterCode','period','partnerCode']).primaryValue.sum().rename('leaf_usd')
    parent=monthly[monthly.cmdCode.eq(8542)].set_index(['reporterCode','period','partnerCode']).primaryValue.rename('parent_usd')
    partner=pd.concat([leaf,parent],axis=1).fillna(0)
    complete_months=set(available.index)
    partner=partner.loc[[idx[:2] in complete_months for idx in partner.index]].copy()
    partner['absolute_gap_usd']=partner.leaf_usd-partner.parent_usd
    denom=partner[['leaf_usd','parent_usd']].max(axis=1)
    partner['relative_gap']=partner.absolute_gap_usd/denom.replace(0,np.nan)
    partner['pass']=partner.absolute_gap_usd.abs().le(.05)|partner.relative_gap.abs().le(1e-6)|denom.eq(0)
    partner.reset_index().to_csv(OUT/'product_partner_reconciliation.csv',index=False)
    old=pd.read_csv(ROOT.parent/'data/trade_panel.csv.gz')
    official=pd.concat([old[['reporterCode','refYear','cmdCode','partnerCode','primaryValue']],
                        annual_new[['reporterCode','refYear','cmdCode','partnerCode','primaryValue']]],ignore_index=True)
    official=official[official.partnerCode.eq(0)].set_index(['reporterCode','refYear','cmdCode']).primaryValue.rename('official_annual_usd')
    by_year=monthly[monthly.partnerCode.eq(0)].groupby(['reporterCode','refYear','cmdCode'])
    summed=by_year.primaryValue.sum().rename('sum_months_usd')
    counts=by_year.period.nunique().rename('monthly_observations')
    bridge=pd.concat([summed,official,counts],axis=1)
    bridge['comparable']=bridge.monthly_observations.eq(12)&bridge.official_annual_usd.notna()
    bridge['relative_gap']=np.where(bridge.comparable,
        (bridge.sum_months_usd-bridge.official_annual_usd)/bridge.official_annual_usd,np.nan)
    bridge.reset_index().to_csv(OUT/'monthly_annual_bridge.csv',index=False)
    year_months=monthly[monthly.cmdCode.eq(8542)&monthly.partnerCode.eq(0)].groupby(['reporterISO','refYear']).period.nunique()
    year_months.name='months'
    year_months.rename('months').reset_index().to_csv(OUT/'year_coverage.csv',index=False)
    summary=dict(logical_request_checks=len(audit),unique_source_urls=len({m['url'] for m in manifest}),
        monthly_rows=len(monthly),annual_2025_rows=len(annual_new),invalid_requests=bad,
        missing_monthly_cells=len(missing),product_world_checks=len(available),
        product_world_all_pass=bool(available['pass'].all()),
        max_product_world_relative_gap=float(available.relative_gap.abs().max()),
        product_partner_checks=len(partner),product_partner_failures=int((~partner['pass']).sum()),
        max_request_world_relative_gap=float(audit.world_relative_gap.max()),
        max_monthly_official_annual_relative_gap=float(bridge.relative_gap.abs().max()),
        years=year_months.reset_index().to_dict(orient='records'),
        source_manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        protocol_sha256=hashlib.sha256((ROOT/'monthly_analysis_protocol.md').read_bytes()).hexdigest(),
        complete_primary=all(t in found for t in expected if t[1]<202500) and not any(k.startswith('M_') and int(k.split('_')[2])<202500 for k in bad),
        complete_extension=not missing and not bad)
    (OUT/'data_quality.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['years','invalid_requests']},indent=2))
    if not summary['complete_primary'] or not summary['product_world_all_pass']:
        raise SystemExit('Main analysis blocked: monthly completeness/product World gate failed. See data_quality.json')


if __name__=='__main__':main()
