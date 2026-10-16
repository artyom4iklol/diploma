"""Prespecified fixed-structure volatility comparisons; no causal claims."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/monthly'
GOODS=(854231,854232,854233,854239)
STATES=('initial','product_change','geography_change','final')
REPORTERS=(392,410)
NAMES={392:'Япония',410:'Республика Корея'}
SEED=20261016


def periods(end_year):
    return np.array([y*100+m for y in range(2017,end_year+1) for m in range(1,13)])


def cube(data,reporter,goods,directions,end_year):
    d=data[data.reporterCode.eq(reporter)&data.cmdCode.isin(goods)
           &data.period.le(end_year*100+12)&data.partnerCode.ne(0)].copy()
    d['geo']=d.partnerCode.where(d.partnerCode.isin(directions),-1)
    cols=pd.MultiIndex.from_product([goods,[*directions,-1]],names=['cmdCode','geo'])
    table=d.pivot_table(index='period',columns=['cmdCode','geo'],values='primaryValue',aggfunc='sum',fill_value=0)
    table=table.reindex(index=periods(end_year),columns=cols,fill_value=0).fillna(0)
    return table.to_numpy().reshape(len(table),len(goods),len(directions)+1)


def growth(x,lag,kind='symmetric'):
    current,previous=x[lag:],x[:-lag]
    denom=current+previous if kind=='symmetric' else previous
    numerator=2*(current-previous) if kind=='symmetric' else current-previous
    return np.divide(numerator,denom,out=np.full_like(numerator,np.nan,dtype=float),where=denom!=0)


def choose_directions(data,goods,k,end_year,selection_end=None):
    selection_end=end_year if selection_end is None else selection_end
    d=data[data.cmdCode.isin(goods)&data.partnerCode.ne(0)&data.refYear.between(2017,2020)]
    shares=[]
    for reporter in REPORTERS:
        part=d[d.reporterCode.eq(reporter)].groupby('partnerCode').primaryValue.sum()
        shares.append(part/part.sum())
    rank=pd.concat(shares,axis=1).fillna(0).mean(axis=1).drop(index=list(REPORTERS),errors='ignore').sort_values(ascending=False)
    candidates=[int(x) for x in rank.head(k).index]
    selected=[];details=[]
    for destination in candidates:
        failures=0
        for reporter in REPORTERS:
            x=cube(data,reporter,goods,[destination],selection_end)[:,:,0]
            failures+=int(np.isnan(growth(x,12)).sum())
        if not failures:selected.append(destination)
        details.append(dict(candidate=destination,baseline_mean_share=float(rank.loc[destination]),
                            retained=failures==0,unobserved_growth_cells=failures))
    for reporter in REPORTERS:
        x=cube(data,reporter,goods,selected,selection_end)
        if np.isnan(growth(x[:,:,-1],12)).any():
            raise ValueError('Unobserved residual-group growth')
    return selected,details


def weights(x,years,start_year,end_year):
    mats=[]
    for year in [start_year,end_year]:
        amounts=x[years==year].sum(axis=0)
        assert amounts.sum()>0
        w=amounts.sum(axis=1)/amounts.sum()
        assert np.all(w>0)
        p=amounts/amounts.sum(axis=1)[:,None]
        mats.append((w,p))
    (w0,p0),(w1,p1)=mats
    a=np.stack([(w0[:,None]*p0).ravel(),(w1[:,None]*p0).ravel(),
                (w0[:,None]*p1).ravel(),(w1[:,None]*p1).ravel()],axis=1)
    assert np.all(a>=0) and np.allclose(a.sum(axis=0),1,atol=1e-12)
    return a


def full_hhi_states(data,reporter,goods,initial_year,final_year):
    d=data[data.reporterCode.eq(reporter)&data.cmdCode.isin(goods)&data.partnerCode.ne(0)]
    destinations=sorted(d.partnerCode.unique())
    matrices=[]
    idx=pd.MultiIndex.from_product([goods,destinations],names=['cmdCode','partnerCode'])
    for year in [initial_year,final_year]:
        totals=d[d.refYear.eq(year)].groupby(['cmdCode','partnerCode']).primaryValue.sum().reindex(idx,fill_value=0)
        matrix=totals.to_numpy().reshape(len(goods),len(destinations))
        w=matrix.sum(axis=1)/matrix.sum()
        p=matrix/matrix.sum(axis=1)[:,None]
        matrices.append((w,p))
    (w0,p0),(w1,p1)=matrices
    return [float(np.square((w[:,None]*p).sum(axis=0)).sum())
            for w,p in [(w0,p0),(w1,p0),(w0,p1),(w1,p1)]]


def shapley(v):
    mix=.5*((v[...,1]-v[...,0])+(v[...,3]-v[...,2]))
    geo=.5*((v[...,2]-v[...,0])+(v[...,3]-v[...,1]))
    delta=v[...,3]-v[...,0]
    assert np.allclose(mix+geo,delta,rtol=1e-10,atol=1e-12)
    return delta,mix,geo


def bootstrap(y,block=12,repetitions=1999):
    rng=np.random.default_rng(SEED)
    n=len(y);nb=int(np.ceil(n/block))
    starts=rng.integers(0,n,size=(repetitions,nb))
    indices=((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
    v=np.var(y[indices],axis=1,ddof=1)
    delta,mix,geo=shapley(v)
    statistics=dict(delta_variance_pp2=delta*10000,mix_variance_pp2=mix*10000,
                    geography_variance_pp2=geo*10000,
                    delta_sd_pp=100*(np.sqrt(v[:,3])-np.sqrt(v[:,0])))
    result=[]
    for metric,values in statistics.items():
        low,high=np.quantile(values,[.025,.975])
        result.append(dict(metric=metric,block_months=block,repetitions=repetitions,
                           ci_low=float(low),ci_high=float(high),seed=SEED))
    for j,state in enumerate(STATES):
        low,high=np.quantile(100*np.sqrt(v[:,j]),[.025,.975])
        result.append(dict(metric=f'{state}_sd_pp',block_months=block,repetitions=repetitions,
                           ci_low=float(low),ci_high=float(high),seed=SEED))
    return result


def run_case(data,label,goods=GOODS,k=8,end_year=2024,initial_year=2017,final_year=2024,
             sigma_start=2018,sigma_end=2024,frequency='M',lag=12,kind='symmetric',
             merge_cn_hk=False,directions=None,selection_end=None,bootstrap_blocks=()):
    data=data.copy()
    if merge_cn_hk:data.loc[data.partnerCode.eq(344),'partnerCode']=156
    if directions is None:
        directions,details=choose_directions(data,goods,k,end_year,selection_end)
    else:details=[]
    state_rows=[];summaries=[];intervals=[];drivers=[];series=[];components=[];checks=[]
    for reporter in REPORTERS:
        monthly=cube(data,reporter,goods,directions,end_year)
        yyyymm=periods(end_year);annual_years=yyyymm//100
        a=weights(monthly,annual_years,initial_year,final_year)
        x=monthly
        if frequency=='Q':
            x=x.reshape(-1,3,len(goods),len(directions)+1).sum(axis=1)
            period_labels=yyyymm[2::3]
        else:period_labels=yyyymm
        g=growth(x,lag,kind).reshape(len(x)-lag,-1)
        dates=period_labels[lag:]
        window=(dates//100>=sigma_start)&(dates//100<=sigma_end)
        g=g[window];dates=dates[window]
        used=a.max(axis=1)>0
        if np.isnan(g[:,used]).any():
            summaries.append(dict(case=label,reporter=reporter,status='unobserved_growth',
                n=len(g),unobserved=int(np.isnan(g[:,used]).sum()),directions=';'.join(map(str,directions))))
            continue
        g=np.nan_to_num(g,nan=0)
        assert len(g)>=12
        covariance=np.cov(g,rowvar=False,ddof=1)
        y=g@a
        variances=np.einsum('ij,ik,kj->j',a,covariance,a)
        direct=np.var(y,axis=0,ddof=1)
        assert np.allclose(variances,direct,atol=1e-12,rtol=1e-10)
        eigenvalues=np.linalg.eigvalsh(covariance)
        assert eigenvalues.min()>-1e-9
        delta,mix,geo=shapley(variances)
        fine_hhi=full_hhi_states(data,reporter,goods,initial_year,final_year)
        for j,state in enumerate(STATES):
            ag=a[:,j].reshape(len(goods),len(directions)+1)
            hhi=float(np.square(ag.sum(axis=0)).sum())
            state_rows.append(dict(case=label,reporter=reporter,state=state,variance_pp2=float(variances[j]*10000),
                sd_pp=float(100*np.sqrt(variances[j])),hhi_matched_grid=hhi,hhi_all_destinations=fine_hhi[j],
                mean_growth_pp=float(100*y[:,j].mean()),residual_share=float(ag[:,-1].sum()),n=len(g)))
            weighted=covariance*a[:,j,None]*a[None,:,j]
            commodity=np.repeat(np.arange(len(goods)),len(directions)+1)
            destination=np.tile(np.arange(len(directions)+1),len(goods))
            same_g=commodity[:,None]==commodity[None,:]
            same_d=destination[:,None]==destination[None,:]
            values={'diagonal':np.trace(weighted),
                    'same_product_different_markets':weighted[same_g&~same_d].sum(),
                    'same_market_different_products':weighted[~same_g&same_d].sum(),
                    'different_products_and_markets':weighted[~same_g&~same_d].sum()}
            assert np.isclose(sum(values.values()),variances[j],rtol=1e-10,atol=1e-12)
            for component,value in values.items():
                components.append(dict(case=label,reporter=reporter,state=state,component=component,variance_pp2=float(value*10000)))
        summaries.append(dict(case=label,reporter=reporter,status='ok',n=len(g),
            initial_year=initial_year,final_year=final_year,sigma_start=sigma_start,sigma_end=sigma_end,
            product_count=len(goods),separate_directions=len(directions),grid_limited=len(directions)<3,
            directions=';'.join(map(str,directions)),delta_variance_pp2=float(delta*10000),
            mix_variance_pp2=float(mix*10000),geography_variance_pp2=float(geo*10000),
            delta_sd_pp=float(100*(np.sqrt(variances[3])-np.sqrt(variances[0]))),
            variance_change_pct=float(100*(variances[3]/variances[0]-1)),
            sd_change_pct=float(100*(np.sqrt(variances[3]/variances[0])-1)),
            hhi_full_change=fine_hhi[3]-fine_hhi[0],
            hhi_grid_change=state_rows[-1]['hhi_matched_grid']-state_rows[-4]['hhi_matched_grid'],
            min_cov_eigenvalue=float(eigenvalues.min())))
        # Symmetric exact attribution of a quadratic form, averaged over two orders.
        cell_mix=.5*((a[:,1]-a[:,0])*(covariance@(a[:,1]+a[:,0]))
                     +(a[:,3]-a[:,2])*(covariance@(a[:,3]+a[:,2])))
        cell_geo=.5*((a[:,2]-a[:,0])*(covariance@(a[:,2]+a[:,0]))
                     +(a[:,3]-a[:,1])*(covariance@(a[:,3]+a[:,1])))
        assert np.isclose(cell_mix.sum(),mix,rtol=1e-10,atol=1e-12)
        assert np.isclose(cell_geo.sum(),geo,rtol=1e-10,atol=1e-12)
        for index,(product,destination) in enumerate((g,d) for g in goods for d in [*directions,-1]):
            drivers.append(dict(case=label,reporter=reporter,cmdCode=product,destination=destination,
                                mix_variance_pp2=float(cell_mix[index]*10000),geography_variance_pp2=float(cell_geo[index]*10000)))
        for block in bootstrap_blocks:
            for row in bootstrap(y,block):intervals.append(dict(case=label,reporter=reporter,**row))
        for index,date in enumerate(dates):
            series.append(dict(case=label,reporter=reporter,period=int(date),**{state:float(y[index,j]) for j,state in enumerate(STATES)}))
        checks.append(dict(case=label,reporter=reporter,variance_identity_max_error=float(np.abs(variances-direct).max()),
                           shapley_add_up_error=float(abs(delta-mix-geo)),weight_sum_max_error=float(np.abs(a.sum(axis=0)-1).max())))
    return dict(states=state_rows,summary=summaries,intervals=intervals,drivers=drivers,
                series=series,components=components,checks=checks,
                grid=[dict(case=label,**row) for row in details],directions=directions)


def annual_and_observed(data,end_year=2025):
    annual=[];observed=[];identity_checks=[]
    for reporter in REPORTERS:
        for include_parts in [False,True]:
            goods=(*GOODS,854290) if include_parts else GOODS
            d=data[data.reporterCode.eq(reporter)&data.cmdCode.isin(goods)&data.partnerCode.ne(0)]
            d=d[d.refYear.le(end_year)]
            for year,group in d.groupby('refYear'):
                destinations=group.groupby('partnerCode').primaryValue.sum()
                products=group.groupby('cmdCode').primaryValue.sum()
                value=products.sum()
                annual.append(dict(reporter=reporter,year=int(year),include_parts=include_parts,
                    export_usd=float(value),hhi=float(np.square(destinations/value).sum()),
                    memory_share=float(products.loc[854232]/value),product_hhi=float(np.square(products/value).sum())))
            destinations=sorted(d.partnerCode.unique())
            x=cube(data,reporter,goods,destinations,end_year).reshape(12*(end_year-2016),-1)
            totals=x.sum(axis=1)
            for lag in [1,12]:
                aggregate=2*(totals[lag:]-totals[:-lag])/(totals[lag:]+totals[:-lag])
                denom=x[lag:]+x[:-lag]
                cell_growth=np.divide(2*(x[lag:]-x[:-lag]),denom,out=np.zeros_like(denom),where=denom!=0)
                midpoint_weights=denom/denom.sum(axis=1)[:,None]
                from_cells=(midpoint_weights*cell_growth).sum(axis=1)
                error=float(np.abs(from_cells-aggregate).max())
                assert error<1e-12
                identity_checks.append(dict(reporter=reporter,include_parts=include_parts,lag=lag,max_error=error))
                for i,p in enumerate(periods(end_year)[lag:]):
                    observed.append(dict(reporter=reporter,include_parts=include_parts,lag=lag,period=int(p),growth_pp=float(100*aggregate[i])))
    pd.DataFrame(annual).to_csv(OUT/'annual_indicators_from_months.csv',index=False)
    pd.DataFrame(observed).to_csv(OUT/'observed_growth.csv',index=False)
    pd.DataFrame(identity_checks).to_csv(OUT/'aggregate_growth_identity.csv',index=False)


def main():
    quality=json.loads((OUT/'data_quality.json').read_text())
    assert quality['analysis_ready'],'Quality gate failed'
    panel_sha256=hashlib.sha256((ROOT/'data/monthly_panel_full.csv.gz').read_bytes()).hexdigest()
    assert panel_sha256==quality['monthly_panel_sha256'],'Panel changed after quality control'
    data=pd.read_csv(ROOT/'data/monthly_panel_full.csv.gz')
    annual_and_observed(data,2025 if quality['complete_extension'] else 2024)
    results=[]
    primary=run_case(data,'primary',bootstrap_blocks=(12,6))
    results.append(primary)
    for k in [5,12]:results.append(run_case(data,f'top{k}',k=k))
    results.append(run_case(data,'include_parts',goods=(*GOODS,854290),directions=primary['directions']))
    results.append(run_case(data,'cn_hk_combined',merge_cn_hk=True))
    results.append(run_case(data,'monthly_lag1',directions=primary['directions'],lag=1,sigma_start=2017))
    results.append(run_case(data,'quarterly_yoy',directions=primary['directions'],frequency='Q',lag=4))
    results.append(run_case(data,'ordinary_pct_yoy',directions=primary['directions'],kind='ordinary'))
    for start,end in [(2018,2020),(2021,2024)]:
        results.append(run_case(data,f'sigma_{start}_{end}',directions=primary['directions'],sigma_start=start,sigma_end=end))
    # A temporal split with weights and grid fixed using initial-period data only.
    training_dirs,details=choose_directions(data,GOODS,8,2024,selection_end=2020)
    for start,end in [(2018,2020),(2021,2024)]:
        result=run_case(data,f'temporal_{start}_{end}',directions=training_dirs,
                        initial_year=2017,final_year=2020,sigma_start=start,sigma_end=end)
        result['grid']=[dict(case=f'temporal_{start}_{end}',**row) for row in details]
        results.append(result)
    if quality['complete_extension']:
        results.append(run_case(data,'extension_2025',end_year=2025,final_year=2025,sigma_end=2025))
    for name in ['states','summary','intervals','drivers','series','components','checks','grid']:
        rows=[row for result in results for row in result[name]]
        pd.DataFrame(rows).to_csv(OUT/f'risk_{name}.csv',index=False)
    output=dict(protocol_sha256=hashlib.sha256((ROOT/'monthly_analysis_protocol.md').read_bytes()).hexdigest(),
                monthly_panel_sha256=panel_sha256,
                analysis_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                primary=[row for row in primary['summary']],cases=len(results),
                statuses={status:sum(row['status']==status for r in results for row in r['summary'])
                          for status in ['ok','unobserved_growth']},
                causal_identification=False,real_time_vintages=False,
                uncertainty='Paired circular block bootstrap of historical growth; fixed weights and fixed grid')
    (OUT/'analysis_validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
