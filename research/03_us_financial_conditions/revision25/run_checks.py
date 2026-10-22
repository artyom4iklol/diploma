"""Offline 2x2 sensitivity experiment, bounded by PROTOCOL.md."""
from pathlib import Path
import sys, json, hashlib, platform
import numpy as np
import pandas as pd
import scipy
from scipy.stats import norm

P=Path(__file__).resolve().parent; ROOT=P.parent; O=P/'results'
sys.path.insert(0,str(ROOT/'revision18'))
from fit_pilot import fit, loss, hac
MODELS={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],
        'AR_ESI_NFCI':['gx','esi','nfci'],'AR_ESI_ANFCI':['gx','esi','anfci']}
PAIRS=[('AR_ESI_NFCI','AR_ESI'),('AR_ESI_ANFCI','AR_ESI'),
       ('AR_ESI_NFCI','HIST'),('AR_ESI_ANFCI','HIST'),('AR_ESI_ANFCI','AR_ESI_NFCI')]

def weekly(path):
    a=pd.read_csv(path)
    n=pd.Series(pd.to_numeric(a.iloc[:,1],errors='coerce').to_numpy(),
                index=pd.to_datetime(a.iloc[:,0])).dropna().sort_index()
    assert not n.index.duplicated().any()
    return n

def aggregate_m2(n,q):
    end=(q.asfreq('M',how='start')+1).end_time
    a=n[(n.index>=q.start_time)&(n.index+pd.Timedelta(days=7)<=end)]
    return float(a.mean()),len(a),(str(a.index.max().date()) if len(a) else None),end

def prepare_frames():
    a=pd.read_csv(ROOT/'revision19/results/vintaged_model_frames_ANFCI.csv')
    a['q']=pd.PeriodIndex(a.quarter,freq='Q')
    cal=pd.read_csv(ROOT/'revision18/results/forecast_calendar_59.csv')
    outputs=[];calendar=[];inputs=[]
    for row in cal.itertuples():
        t=pd.Period(row.origin,freq='Q');v=a[a.origin.eq(row.origin)].copy().set_index('q')
        for series,folder in [('nfci','revision16/sources/nfci_vintages'),('anfci','revision19/sources/anfci_vintages')]:
            path=ROOT/folder/(series+'_'+row.nfci_vintage+'.csv');n=weekly(path)
            inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            values={}
            for q in v.index[v.index<=t]:
                value,count,last,end=aggregate_m2(n,q);values[q]=value
                if q==t:
                    assert count>=5 and pd.Timestamp(last)+pd.Timedelta(days=7)<=end
                    calendar.append(dict(origin=str(t),series=series,vintage=row.nfci_vintage,
                        observations=count,last_observation=last,coverage_end=str(end.date()),
                        value=value,quarter_value=float(v.at[t,series])))
            v[series+'_m2']=pd.Series(values)
            if str(t)=='2018Q4':
                changed=n.copy();cutoff=(t.asfreq('M',how='start')+1).end_time
                changed.loc[changed.index+pd.Timedelta(days=7)>cutoff]=123456.
                assert aggregate_m2(n,t)[0]==aggregate_m2(changed,t)[0]
        assert v.loc[t,['gx','esi','nfci_m2','anfci_m2']].notna().all()
        outputs.append(v.reset_index(drop=True))
    d=pd.concat(outputs,ignore_index=True);d.to_csv(O/'M2_model_frames.csv',index=False)
    pd.DataFrame(calendar).to_csv(O/'M2_calendar.csv',index=False)
    (P/'input_hashes.json').write_text(json.dumps(inputs,indent=2)+'\n')
    return d

def holm(values):
    values=np.asarray(values);ids=np.argsort(values);adjusted=np.empty(len(values))
    adjusted[ids]=np.minimum(1.,np.maximum.accumulate((len(values)-np.arange(len(values)))*values[ids]))
    return adjusted

def run():
    lock=json.loads((P/'protocol_lock.json').read_text())
    assert hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()==lock['sha256']
    O.mkdir(exist_ok=True);a=prepare_frames();a['q']=pd.PeriodIndex(a.quarter,freq='Q')
    targets=pd.read_csv(ROOT/'revision18/results/evaluation_targets.csv')
    records=[];coefficients=[];clipping=[];training=[];solver_checks=[]
    for variant in ['expanding','rolling52']:
        for h in [1,4]:
            for target in targets[targets.h.eq(h)].itertuples():
                t=pd.Period(target.origin,freq='Q')
                base=a[a.origin.eq(target.origin)].copy().set_index('q');base['target']=base['y'+str(h)]
                elig=(base.index>=pd.Period('1995Q3'))&(base.index+h<=t-1)
                original_mask=elig&base[['target','gx','esi','nfci','anfci']].notna().all(axis=1)
                for coverage in ['Q','M2']:
                    v=base.copy()
                    if coverage=='M2':v['nfci'],v['anfci']=v.nfci_m2,v.anfci_m2
                    mask=elig&v[['target','gx','esi','nfci','anfci']].notna().all(axis=1)
                    assert np.array_equal(mask,original_mask)
                    tr=v[mask]
                    if variant=='rolling52':tr=tr.iloc[-52:];assert len(tr)==52
                    assert tr.index.max()+h<=t-1
                    row=v.loc[t];low=float(tr.gx.min());high=float(tr.gx.max())
                    clipped_gx=float(np.clip(float(row.gx),low,high))
                    training.append(dict(variant=variant,coverage=coverage,h=h,origin=str(t),
                        n_train=len(tr),last_training_target=str(tr.index.max()+h)))
                    if coverage=='Q':
                        clipping.append(dict(variant=variant,h=h,origin=str(t),gx=float(row.gx),
                            minimum=low,maximum=high,clipped_gx=clipped_gx,changed=bool(clipped_gx!=row.gx)))
                    for model,cols in MODELS.items():
                        pred,b,qc=fit(tr,row,cols)
                        assert abs(pred-(b['const']+sum(b[k]*row[k] for k in cols)))<1e-8
                        if coverage=='M2' and model in ['AR_ESI_NFCI','AR_ESI_ANFCI'] and str(t) in ['2011Q2','2020Q4','2025Q3']:
                            p2,b2,c2=fit(tr,row,cols,'highs-ipm')
                            assert abs(qc['objective']-c2['objective'])<1e-6 and abs(pred-p2)<1e-6
                            solver_checks.append(dict(variant=variant,h=h,origin=str(t),model=model,
                                objective_difference=qc['objective']-c2['objective'],forecast_difference=pred-p2))
                        coefficients.append(dict(variant=variant,coverage=coverage,h=h,origin=str(t),model=model,**b))
                        for guard in ['raw','clip_g']:
                            prediction=pred if guard=='raw' else pred+b.get('gx',0.)*(clipped_gx-row.gx)
                            if clipped_gx==row.gx or model=='HIST':assert prediction==pred
                            episode='pre2020' if t+h<pd.Period('2020Q1') else ('2022_2025' if t+1>=pd.Period('2022Q1') else 'covid_overlap')
                            records.append(dict(variant=variant,config=coverage+'_'+guard,h=h,origin=str(t),
                                forecast_date=str((t.end_time.normalize()+pd.Timedelta(days=15)).date()),
                                model=model,episode=episode,n_train=len(tr),actual=float(target.actual),
                                actual_latest=float(target.actual_latest),forecast=float(prediction),
                                loss=float(loss(target.actual-prediction)),loss_latest=float(loss(target.actual_latest-prediction)),
                                hit=int(target.actual<prediction),objective=float(qc['objective'])))
            print(variant,'h='+str(h),'complete',flush=True)
    f=pd.DataFrame(records);assert len(f)==4520
    assert not f.duplicated(['variant','config','h','origin','model']).any()
    assert np.isfinite(f[['forecast','actual','loss']].to_numpy()).all()
    old=pd.read_csv(ROOT/'revision19/results/ANFCI_forecasts.csv')
    old=old[old.information.eq('historical')&old.variant.isin(['expanding','rolling52'])]
    j=f[f.config.eq('Q_raw')].merge(old,on=['variant','h','origin','model'],suffixes=('_new','_old'),validate='one_to_one')
    assert len(j)==1130
    diffs={k:float((j[k+'_new']-j[k+'_old']).abs().max()) for k in ['forecast','actual','loss','n_train']}
    assert max(diffs.values())<1e-8,diffs
    f.to_csv(O/'forecasts.csv',index=False)
    pd.DataFrame(coefficients).to_csv(O/'coefficients.csv',index=False)
    pd.DataFrame(clipping).to_csv(O/'growth_guard.csv',index=False)
    pd.DataFrame(training).to_csv(O/'training_checks.csv',index=False)
    scores=f.groupby(['variant','config','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),
        mean_loss_latest=('loss_latest','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).reset_index()
    scores.to_csv(O/'scores.csv',index=False)
    f.groupby(['variant','config','h','episode','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(O/'episode_scores.csv')
    comparisons=[];omissions=[];tests=[]
    for (variant,config,h),group in f.groupby(['variant','config','h']):
        w=group.pivot(index='origin',columns='model',values='loss').sort_index()
        for model,benchmark in PAIRS:
            d=w[model]-w[benchmark];without=(d.sum()-d)/(len(d)-1)
            comparisons.append(dict(variant=variant,config=config,h=int(h),model=model,benchmark=benchmark,n=len(d),
                difference=d.mean(),ratio=w[model].mean()/w[benchmark].mean(),wins=int((d<0).sum()),ties=int((d==0).sum()),
                minimum_difference_omit_one=without.min(),maximum_difference_omit_one=without.max(),
                negative_after_omit_count=int((without<0).sum()),difference_omit_2020Q4=float(without.loc['2020Q4'])))
            for origin in w.index:
                omissions.append(dict(variant=variant,config=config,h=int(h),model=model,benchmark=benchmark,
                    omitted_origin=origin,difference_without=float(without.loc[origin])))
            if variant=='rolling52':
                for L in [4,8]:
                    se=float(hac(d.to_numpy(),L));assert se>0;z=float(d.mean()/se)
                    tests.append(dict(config=config,h=int(h),model=model,benchmark=benchmark,L=L,n=len(d),
                        difference=d.mean(),se=se,z=z,p_two_sided=float(2*norm.sf(abs(z))),
                        lo95=d.mean()-norm.ppf(.975)*se,hi95=d.mean()+norm.ppf(.975)*se,
                        lo_family95=d.mean()-norm.ppf(1-.05/40)*se,hi_family95=d.mean()+norm.ppf(1-.05/40)*se))
    tests=pd.DataFrame(tests)
    for (h,L),group in tests.groupby(['h','L']):
        assert len(group)==20
        tests.loc[group.index,'p_holm20']=holm(group.p_two_sided.to_numpy())
    pd.DataFrame(comparisons).to_csv(O/'comparisons.csv',index=False)
    pd.DataFrame(omissions).to_csv(O/'single_omissions.csv',index=False)
    tests.to_csv(O/'rolling52_inference.csv',index=False)
    cl=pd.DataFrame(clipping)
    validation=dict(protocol_sha256=lock['sha256'],forecasts=len(f),baseline_reproduced=len(j),
        baseline_maximum_differences=diffs,all_training_rows_matched=True,all_source_files_read_only=True,
        third_month_mutation_no_effect=True,solver_checks=solver_checks,clipped_origins=cl[cl.changed].to_dict('records'),
        inference_family_size=20,main_horizon=1,auxiliary_horizon=4,special_expanding_nested_revision_test_implemented=False,
        versions={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__})
    (O/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(scores.query("variant=='expanding'")[['config','h','model','mean_loss','hit_rate']].to_string(index=False))
    print('Validated',len(f),'forecasts; clipped origins:',cl[cl.changed].to_dict('records'))

if __name__=='__main__':run()
