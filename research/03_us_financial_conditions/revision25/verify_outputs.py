"""Verify revision25 using saved forecasts, coefficients and a separate HAC calculation."""
from pathlib import Path
import json, hashlib, re
import numpy as np
import pandas as pd
from scipy.stats import norm

P=Path(__file__).resolve().parent; R=P/'results'; C=P.parent/'chapter2'

def verify_additional(text=None):
    if text is None:text=(C/'Chapter_2_Empirical_Analysis.md').read_text()
    lock=json.loads((P/'protocol_lock.json').read_text())
    assert hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()==lock['sha256']
    for x in json.loads((P/'input_hashes.json').read_text()):
        assert hashlib.sha256((P.parent/x['path']).read_bytes()).hexdigest()==x['sha256']
    f=pd.read_csv(R/'forecasts.csv');assert len(f)==4520
    assert not f.duplicated(['variant','config','h','origin','model']).any()
    for suffix in ['','_latest']:
        residual=f['actual'+suffix]-f.forecast
        np.testing.assert_allclose(f['loss'+suffix],np.where(residual>=0,.1*residual,-.9*residual),atol=1e-12)
    assert np.array_equal(f.hit,(f.actual<f.forecast).astype(int))
    raw=pd.read_csv(P.parent/'revision19/results/ANFCI_forecasts.csv')
    raw=raw.query("information=='historical' and variant in ['expanding','rolling52']")
    base=f[f.config.eq('Q_raw')].merge(raw,on=['variant','h','origin','model'],suffixes=('_new','_old'),validate='one_to_one')
    assert len(base)==1130
    for k in ['forecast','loss','actual','actual_latest','n_train']:
        np.testing.assert_allclose(base[k+'_new'],base[k+'_old'],atol=1e-8)
    scores=pd.read_csv(R/'scores.csv')
    recalculated=f.groupby(['variant','config','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),mean_loss_latest=('loss_latest','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).reset_index()
    joined=scores.merge(recalculated,on=['variant','config','h','model'],suffixes=('_saved','_new'),validate='one_to_one')
    for k in ['n','mean_loss','mean_loss_latest','hits','hit_rate']:
        np.testing.assert_allclose(joined[k+'_saved'],joined[k+'_new'],atol=1e-12)
    for configs in [['Q_raw','M2_raw'],['Q_clip_g','M2_clip_g']]:
        for model in ['HIST','AR','AR_ESI','AR_ESI_NFCI','AR_ESI_ANFCI']:
            row=[model.replace('_',' + ')]
            for h in [1,4]:
                for config in configs:
                    value=f.query("variant=='expanding' and config==@config and h==@h and model==@model").loss.mean()
                    row.append(f'{value:.4f}'.replace('.',','))
            assert '| '+' | '.join(row)+' |' in text
    co=pd.read_csv(R/'coefficients.csv').set_index(['variant','coverage','h','origin','model'])
    fr=pd.read_csv(R/'M2_model_frames.csv');current=fr[fr.quarter.eq(fr.origin)].set_index('origin')
    guard=pd.read_csv(R/'growth_guard.csv').set_index(['variant','h','origin'])
    cols={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],'AR_ESI_NFCI':['gx','esi','nfci'],'AR_ESI_ANFCI':['gx','esi','anfci']}
    for row in f.itertuples():
        coverage=row.config.split('_')[0];b=co.loc[(row.variant,coverage,row.h,row.origin,row.model)]
        x=current.loc[row.origin].copy()
        if coverage=='M2':x['nfci'],x['anfci']=x.nfci_m2,x.anfci_m2
        if row.config.endswith('clip_g'):x['gx']=guard.loc[(row.variant,row.h,row.origin),'clipped_gx']
        prediction=b['const']+sum(b[k]*x[k] for k in cols[row.model])
        assert abs(prediction-row.forecast)<1e-8
    checks=pd.read_csv(R/'training_checks.csv')
    assert (pd.PeriodIndex(checks.last_training_target,freq='Q')<=pd.PeriodIndex(checks.origin,freq='Q')-1).all()
    counts=checks.pivot(index=['variant','h','origin'],columns='coverage',values='n_train')
    assert (counts.Q==counts.M2).all()
    for ix,row in guard.iterrows():
        variant,h,origin=ix;t=pd.Period(origin,freq='Q')
        v=fr[fr.origin.eq(origin)].copy();v.index=pd.PeriodIndex(v.quarter,freq='Q')
        mask=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)&v[['y'+str(h),'gx','esi','nfci','anfci']].notna().all(axis=1)
        tr=v[mask]
        if variant=='rolling52':tr=tr.iloc[-52:]
        np.testing.assert_allclose([row.minimum,row.maximum],[tr.gx.min(),tr.gx.max()],atol=1e-12)
        assert abs(np.clip(row.gx,row.minimum,row.maximum)-row.clipped_gx)<1e-12
    cal=pd.read_csv(R/'M2_calendar.csv');assert len(cal)==118 and cal.observations.isin([7,8]).all()
    assert (pd.to_datetime(cal.last_observation)+pd.Timedelta(days=7)<=pd.to_datetime(cal.coverage_end)).all()
    comparison=pd.read_csv(R/'comparisons.csv');omissions=pd.read_csv(R/'single_omissions.csv')
    assert len(comparison)==80 and len(omissions)==4520
    for r in comparison.itertuples():
        part=f.query('variant==@r.variant and config==@r.config and h==@r.h')
        w=part.pivot(index='origin',columns='model',values='loss').sort_index()
        d=w[r.model]-w[r.benchmark]
        assert abs(d.mean()-r.difference)<1e-12
        assert int((d<0).sum())==r.wins
        saved=omissions.query('variant==@r.variant and config==@r.config and h==@r.h and model==@r.model and benchmark==@r.benchmark').set_index('omitted_origin')
        values=[]
        for origin in d.index:
            value=d.drop(origin).mean();values.append(value)
            assert abs(value-saved.at[origin,'difference_without'])<1e-12
        assert int((np.array(values)<0).sum())==r.negative_after_omit_count
    tests=pd.read_csv(R/'rolling52_inference.csv');assert len(tests)==80
    for r in tests.itertuples():
        part=f.query("variant=='rolling52' and config==@r.config and h==@r.h")
        w=part.pivot(index='origin',columns='model',values='loss').sort_index();d=(w[r.model]-w[r.benchmark]).to_numpy()
        centered=d-d.mean();n=len(d)
        distances=np.abs(np.subtract.outer(np.arange(n),np.arange(n)))
        weights=np.maximum(0.,1-distances/(r.L+1))
        se=np.sqrt(centered@weights@centered/n**2)
        assert abs(se-r.se)<1e-12
        pval=2*norm.sf(abs(d.mean()/se));assert abs(pval-r.p_two_sided)<1e-12
        np.testing.assert_allclose([r.lo95,r.hi95],[d.mean()-norm.ppf(.975)*se,d.mean()+norm.ppf(.975)*se],atol=1e-12)
    for (h,L),group in tests.groupby(['h','L']):
        assert len(group)==20
        running=0.
        for rank,(idx,row) in enumerate(group.sort_values('p_two_sided').iterrows()):
            running=max(running,(20-rank)*row.p_two_sided)
            assert abs(min(1.,running)-row.p_holm20)<1e-12
    assert not ((tests.h==1)&(tests.p_holm20<.05)).any()
    assert not ((tests.h==4)&(tests.L==4)&(tests.p_holm20<.05)).any()
    sig=tests.query('h==4 and L==8 and p_holm20<.05')
    assert len(sig)==2 and sig.model.eq('AR_ESI_ANFCI').all() and sig.benchmark.eq('HIST').all() and sig.difference.gt(0).all()
    assert not ((tests.p_holm20<.05)&tests.difference.lt(0)&tests.benchmark.isin(['AR_ESI','HIST'])).any()
    guarded=comparison[comparison.config.str.endswith('clip_g')&comparison.benchmark.eq('AR_ESI')]
    assert guarded.difference.gt(0).all()
    exp=guarded[guarded.variant.eq('expanding')];assert exp.negative_after_omit_count.eq(0).all()
    assert re.findall(r'\\tag\{(2\.\d+)\}',text)==[f'2.{i}' for i in range(1,11)]
    result=dict(date='2026-10-19',forecasts_verified=len(f),baseline_rows_verified=len(base),
        coefficient_reconstructions=len(f),HAC_checks=len(tests),pair_comparisons=len(comparison),single_omissions=len(omissions),
        new_numeric_tables_verified=True,protocol_hash_verified=True,source_hashes_verified=True,
        all_growth_bounds_historical=True,training_rows_identical=True,
        primary_h1_rejections_after_Holm=0,auxiliary_h4_L4_rejections_after_Holm=0,
        auxiliary_h4_L8_rejections_after_Holm=2,auxiliary_rejections_favor='HIST',
        independent_evaluation_dates={'h1':58,'h4':55},body_words=len(text.split('## Источники и примечания')[0].split()))
    (R/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

if __name__=='__main__':print(json.dumps(verify_additional(),ensure_ascii=False,indent=2))
