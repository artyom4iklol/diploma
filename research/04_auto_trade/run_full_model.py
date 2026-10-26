"""Run finite, frozen full-model checks. No manuscript text is generated.

Usage: python run_full_model.py [--bootstrap] [--validation]
Existing results are a versioned cache of this exact input/spec/engine hash.
"""
from pathlib import Path
import hashlib, json, os, pickle, sys, time, traceback
import numpy as np
import pandas as pd
from scipy import sparse, stats
from scipy.sparse.linalg import lsmr
from ppml_engine import fit, summarize, trim_separation, design, fe_codes, dummy_matrix, joint_test

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/full';OUT.mkdir(exist_ok=True)
CACHE=ROOT/'data/model_cache';CACHE.mkdir(exist_ok=True)
spec=json.loads((ROOT/'full_model_spec.json').read_text())
fingerprint=hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in ['full_model_spec.json','ppml_engine.py'])+(OUT/'panel.csv').read_bytes()).hexdigest()

def load_panel():
    d=pd.read_csv(OUT/'panel.csv',keep_default_na=False)
    for col in ['quantity','value_eur','quantity_raw','value_eur_raw']:d[col]=pd.to_numeric(d[col],errors='coerce')
    d['t']=pd.to_datetime(d.month).dt.year*12+pd.to_datetime(d.month).dt.month-2021*12-1
    d['quarter']=pd.to_datetime(d.month).dt.to_period('Q').astype(str)
    return d

def estimate(name,d,outcome='quantity',kind='phase'):
    cache=CACHE/(name+'.pkl');target=OUT/(name+'.json')
    if cache.exists() and target.exists():
        with cache.open('rb') as f:c=pickle.load(f)
        if c['fingerprint']==fingerprint:return c['df'],c['result']
    print('START',name,len(d),flush=True)
    d=d[d.quantity.notna() & d.value_eur.notna()].copy()
    d,sep=trim_separation(d,outcome,kind)
    result=fit(d,outcome,kind)
    summary=summarize(result);summary['separation']=sep;summary['fingerprint']=fingerprint
    summary['outcome']=outcome;summary['design']=kind
    if kind=='dynamic':
        indices=[j for j,n in enumerate(result['names']) if n.split('__')[1]<='2023Q1']
        summary['joint_pre_2023Q2']={str(lag):joint_test(result,indices,lag) for lag in [6,12]}
    if kind=='pretrend':summary['joint_pretrend']={str(lag):joint_test(result,list(range(2)),lag) for lag in [6,12]}
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    with cache.open('wb') as f:pickle.dump({'df':d,'result':result,'fingerprint':fingerprint},f)
    print('DONE',name,'n',len(d),'seconds',round(result['elapsed_seconds'],2),[(n,round(float(np.exp(b)),4)) for n,b in zip(result['names'],result['beta']) if 'definitive' in n],flush=True)
    return d,result

def main_fits():
    panel=load_panel();d=panel[(panel.reporter!='EU27_2020') & panel.origin.isin(spec['origins'])].copy()
    cases=[('primary_quantity',d,'quantity','phase'),('primary_value',d,'value_eur','phase')]
    for outcome in ['quantity','value_eur']:
        suffix='quantity' if outcome=='quantity' else 'value'
        cases += [('since2022_'+suffix,d[d.month>='2022-01'],outcome,'phase'),
                  ('exclude_BE_NL_'+suffix,d[~d.reporter.isin(['BE','NL'])],outcome,'phase'),
                  ('observed_only_'+suffix,d[d.strictly_observed],outcome,'phase')]
    for origin in ['JP','KR','US']:cases.append(('omit_'+origin,d[d.origin!=origin],'quantity','phase'))
    units=d.groupby(['reporter','origin','category']).strictly_observed.transform('sum')==60
    cases.append(('balanced_observed',d[units],'quantity','phase'))
    cases += [('origin_product_trends',d,'quantity','trends'),('investigation_phase',d,'quantity','investigation'),
              ('dynamic_quantity',d,'quantity','dynamic'),('dynamic_value',d,'value_eur','dynamic'),
              ('pretrend_quantity',d[d.month<='2023-08'],'quantity','pretrend'),
              ('pretrend_value',d[d.month<='2023-08'],'value_eur','pretrend')]
    errors={}
    for name,dd,outcome,kind in cases:
        try:estimate(name,dd,outcome,kind)
        except Exception as e:
            errors[name]={'error':str(e),'traceback':traceback.format_exc()};print('FAILED',name,str(e),flush=True)
    (OUT/'fit_errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    rows=[]
    for name,_,_,_ in cases:
        path=OUT/(name+'.json')
        if not path.exists():continue
        r=json.loads(path.read_text())
        for c in r['coefficients']:
            row={'model':name,'outcome':r['outcome'],'n':r['n'],'term':c['term'],'beta':c['beta'],'multiplier':c['multiplier']}
            for lag in ['6','12']:
                ci=c['hac'+lag]['multiplier_ci95'];row['hac'+lag+'_lo']=ci[0];row['hac'+lag+'_hi']=ci[1]
            rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'model_coefficients.csv',index=False)
    print('ALL MODEL FITS FINISHED',errors.keys(),flush=True)

def block_bootstrap():
    d=load_panel();d=d[(d.reporter!='EU27_2020') & d.origin.isin(spec['origins'])]
    d,r=estimate('primary_quantity',d)
    monthcodes=np.unique(d.month,return_inverse=True)[1];T=d.month.nunique()
    records=[];target=OUT/'block_bootstrap_draws.json'
    if target.exists():
        prior=json.loads(target.read_text())
        if prior['fingerprint']==fingerprint:records=prior['draws']
    complete={(x['block_length'],x['draw']) for x in records}
    for L in [6,12]:
        for draw in range(199):
            rng=np.random.default_rng(20261026+L*10000+draw)
            offset=int(rng.integers(0,L));blocks=(np.arange(T)+offset)//L
            bw=rng.exponential(1,size=blocks.max()+1);wt=bw[blocks];wt/=wt.mean()
            if (L,draw) in complete:continue
            try:
                rb=fit(d,'quantity',weights=wt[monthcodes],warm=r,need_cov=False)
                item={'block_length':L,'draw':draw,'offset':offset,'beta':rb['beta'].tolist(),'iterations':rb['iterations'],
                      'elapsed_seconds':rb['elapsed_seconds'],'score_error':max(rb['max_fe_score_over_total_y'],rb['max_x_score_over_total_y']),'success':True}
            except Exception as e:item={'block_length':L,'draw':draw,'success':False,'error':str(e)}
            records.append(item)
            target.write_text(json.dumps({'fingerprint':fingerprint,'names':r['names'],'draws':records},indent=2)+'\n')
            if draw%10==0 or draw==198:print('BOOTSTRAP',L,draw+1,'/199',item.get('elapsed_seconds'),item.get('error'),flush=True)
    summary={'method':'Positive block-multiplier weighted-likelihood PPML refits; synchronized months; random-offset non-circular contiguous blocks; exponential weights with mean normalized to one; percentile intervals. Finite descriptive time-dependence sensitivity, not randomization inference.','seed':20261026,'fingerprint':fingerprint,'blocks':{}}
    for L in [6,12]:
        ok=[x for x in records if x['block_length']==L and x['success']]
        B=np.array([x['beta'] for x in ok]);coeff=[]
        for j,name in enumerate(r['names']):
            q=np.quantile(np.exp(B[:,j]),[.025,.5,.975])
            coeff.append({'term':name,'point_multiplier':float(np.exp(r['beta'][j])),'multiplier_percentile_ci95':[float(q[0]),float(q[2])],'bootstrap_median':float(q[1])})
        summary['blocks'][str(L)]={'requested':199,'successful':len(ok),'failed':199-len(ok),'coefficients':coeff}
    (OUT/'block_bootstrap_summary.json').write_text(json.dumps(summary,indent=2)+'\n')

def validate(national=False):
    p=load_panel();mask=p.reporter.isin(['BE','DE']) if national else p.reporter=='EU27_2020'
    d=p[mask & p.origin.isin(spec['origins'])].copy()
    d,sep=trim_separation(d,'quantity');r=fit(d,'quantity')
    X,names=design(d);A=dummy_matrix(fe_codes(d),X);y=d.quantity.to_numpy(float);y/=y.mean()
    eta=np.zeros(len(y));theta=np.zeros(A.shape[1]);obj=lambda e:float(np.sum(y*e-np.exp(e)))
    for it in range(80):
        mu=np.exp(eta);z=eta+(y-mu)/mu;sw=np.sqrt(mu)
        ls=lsmr(A.multiply(sw[:,None]),sw*z,atol=1e-12,btol=1e-12,maxiter=15000)
        proposal=A@ls[0];step=1.
        while obj(eta+step*(proposal-eta))<obj(eta)-1e-9:step/=2
        enew=eta+step*(proposal-eta);theta=theta+step*(ls[0]-theta)
        delta=np.max(np.abs(enew-eta));eta=enew
        if delta<1e-8:break
    diff=float(np.max(np.abs(theta[:X.shape[1]]-r['beta'])))
    scaled=d.copy();scaled['quantity']=scaled.quantity*1000;rs=fit(scaled,'quantity')
    scalediff=float(np.max(np.abs(rs['beta']-r['beta'])))
    audit={'independent_sparse_IRLS':{'n':len(d),'explicit_design_columns':A.shape[1],'iterations':it+1,'lsmr_stop_code':ls[1],
           'max_abs_beta_difference':diff,'max_abs_eta_difference':float(np.max(np.abs(eta-r['eta']))),'passed':diff<1e-6},
           'outcome_times1000_max_beta_difference':scalediff,'scale_invariance_passed':scalediff<1e-9,
           'subpanel_separation':sep,'subpanel':'BE and DE member countries' if national else 'EU27 aggregate',
           'retained_zero_observations':int((d.quantity==0).sum()),'engine':'Independent explicit sparse dummy IRLS with SciPy LSMR versus weighted alternating projection IRLS.',
           'solver':'Custom implementation; no claim of running the Stata ppmlhdfe package.'}
    for name in ['primary_quantity','primary_value']:
        rj=json.loads((OUT/(name+'.json')).read_text());audit[name]={'converged':rj['converged'],'max_fe_relative_score':rj['max_fe_score_over_total_y'],'max_structural_relative_score':rj['max_x_score_over_total_y'],'hessian_condition':rj['hessian_condition'],'lp_separation_checked':all(x['success'] for x in rj['separation']['lp'])}
    assert audit['independent_sparse_IRLS']['passed'] and audit['scale_invariance_passed'],audit
    target='numerical_validation_national.json' if national else 'numerical_validation.json'
    (OUT/target).write_text(json.dumps(audit,indent=2)+'\n');print('VALIDATION',audit,flush=True)

if __name__=='__main__':
    if '--bootstrap' in sys.argv:block_bootstrap()
    elif '--national-validation' in sys.argv:validate(national=True)
    elif '--validation' in sys.argv:validate()
    else:main_fits()
