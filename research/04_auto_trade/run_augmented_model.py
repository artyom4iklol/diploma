"""Finite model revision: broader benchmark, seasonality, trends, geography.

Keeps all baseline files unchanged. All outcomes and variants were fixed in
augmented_model_spec.json before fitting. No manuscript chapters generated.
"""
from pathlib import Path
import hashlib, json, pickle, sys, traceback
import numpy as np
import pandas as pd
from scipy import stats
from scipy.sparse.linalg import lsmr
import ppml_engine_augmented as engine
from run_full_model import load_panel

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/augmented';OUT.mkdir(exist_ok=True)
CACHE=ROOT/'data/augmented_cache';CACHE.mkdir(exist_ok=True)
FP=hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in ['augmented_model_spec.json','ppml_engine_augmented.py','run_augmented_model.py','results/full/panel.csv'])).hexdigest()

def panels():
    original=load_panel();original=original[original.reporter!='EU27_2020'].copy()
    for d in [original]:
        dates=pd.to_datetime(d.month);d['halfyear']=dates.dt.year.astype(str)+'H'+np.where(dates.dt.month<=6,'1','2')
        d['port_group']=np.where(d.reporter.isin(['BE','NL']),'ports','other')
    keys=['reporter','category','month'];cn=original[original.origin=='CN'].set_index(keys).sort_index()
    extra=original[original.origin=='EXT_EU27_2020'].set_index(keys).sort_index()
    assert cn.index.equals(extra.index)
    rest=extra.copy();rest['origin']='REST'
    for col in ['quantity','value_eur']:
        rest[col]=extra[col]-cn[col]
        assert rest[col].notna().all() and (rest[col]>=0).all()
        rest[col+'_raw']=extra[col+'_raw']-cn[col+'_raw']
        rest[col+'_provenance']='EXT_EU27_2020_minus_CN; source cells separately audited'
    rest['strictly_observed']=rest.quantity_raw.notna() & rest.value_eur_raw.notna()
    rest['paired_available']=True
    broad=pd.concat([cn.reset_index(),rest.reset_index()],ignore_index=True).sort_values(keys+['origin']).reset_index(drop=True)
    assert len(broad)==9720 and len(broad.drop_duplicates(keys+['origin']))==9720
    broad.to_csv(OUT/'panel_china_rest.csv',index=False)
    four=original[original.origin.isin(['CN','JP','KR','US'])].copy()
    audit={'rows':len(broad),'reporters':broad.reporter.nunique(),'origins':sorted(broad.origin.unique()),'months':broad.month.nunique(),
           'quantity_negative':int((broad.quantity<0).sum()),'value_negative':int((broad.value_eur<0).sum()),
           'unknown_indicators':int(broad[['quantity','value_eur']].isna().sum().sum()),
           'rest_quantity_zero_value_positive':int(((rest.quantity==0)&(rest.value_eur>0)).sum()),
           'rest_value_zero_quantity_positive':int(((rest.value_eur==0)&(rest.quantity>0)).sum()),
           'exact_reconstruction_quantity':bool(np.array_equal((cn.quantity+rest.quantity).to_numpy(),extra.quantity.to_numpy())),
           'exact_reconstruction_value':bool(np.array_equal((cn.value_eur+rest.value_eur).to_numpy(),extra.value_eur.to_numpy())),
           'CN_positive_rows':int((cn.quantity>0).sum()),'REST_positive_rows':int((rest.quantity>0).sum()),
           'strict_source_pair_rows':int(broad.strictly_observed.sum()),'fingerprint':FP,
           'benchmark_interpretation':'REST is a changing aggregate of all other origins. No claim that it is unaffected by EU policy; not a fifth observed country.'}
    (OUT/'data_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return broad,four

def estimate(name,d,outcome='quantity',kind='preferred'):
    cache=CACHE/(name+'.pkl');target=OUT/(name+'.json')
    if cache.exists() and target.exists():
        with cache.open('rb') as f:c=pickle.load(f)
        if c['fingerprint']==FP:return c['df'],c['result']
    print('START',name,len(d),flush=True)
    dd,sep=engine.trim_separation(d,outcome,kind)
    r=engine.fit(dd,outcome,kind);summary=engine.summarize(r)
    summary.update({'fingerprint':FP,'separation':sep,'outcome':outcome,'design':kind})
    if kind=='halfyear':
        indices=[j for j,n in enumerate(r['names']) if n.split('__')[1] in ['2021H1','2021H2','2023H1']]
        summary['joint_pre_investigation']={str(lag):engine.joint_test(r,indices,lag) for lag in [6,12]}
    if kind=='geographic':
        summary['definitive_other_minus_ports']=[]
        for cat in ['PHEV','HEV']:
            a=r['names'].index(cat+'__definitive__other');b=r['names'].index(cat+'__definitive__ports')
            diff=r['beta'][a]-r['beta'][b];row={'category':cat,'log_contrast':float(diff),'multiplier_ratio_other_to_ports':float(np.exp(diff))}
            for lag,V in r['covariance'].items():
                se=float(np.sqrt(max(V[a,a]+V[b,b]-2*V[a,b],0)));crit=stats.t.ppf(.975,r['n_months']-1)
                row['hac'+lag+'_ratio_ci95']=[float(np.exp(diff-crit*se)),float(np.exp(diff+crit*se))]
            summary['definitive_other_minus_ports'].append(row)
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    with cache.open('wb') as f:pickle.dump({'fingerprint':FP,'df':dd,'result':r},f)
    print('DONE',name,'n',len(dd),'seconds',round(r['elapsed_seconds'],2),'definitive',[(n,round(float(np.exp(b)),4)) for n,b in zip(r['names'],r['beta']) if '__definitive' in n],flush=True)
    return dd,r

def all_fits():
    broad,four=panels();cases=[]
    for outcome in ['quantity','value_eur']:
        suffix='quantity' if outcome=='quantity' else 'value'
        cases += [('rest_preferred_'+suffix,broad,outcome,'preferred'),
                  ('rest_no_trend_'+suffix,broad,outcome,'no_trend'),
                  ('rest_no_season_'+suffix,broad,outcome,'no_season'),
                  ('four_origin_augmented_'+suffix,four,outcome,'preferred'),
                  ('rest_since2022_'+suffix,broad[broad.month>='2022-01'],outcome,'preferred'),
                  ('rest_exclude_BE_NL_'+suffix,broad[broad.port_group!='ports'],outcome,'preferred'),
                  ('rest_observed_only_'+suffix,broad[broad.strictly_observed],outcome,'preferred'),
                  ('rest_geographic_'+suffix,broad,outcome,'geographic'),
                  ('rest_halfyear_'+suffix,broad,outcome,'halfyear')]
    errors={};rows=[]
    for name,d,outcome,kind in cases:
        try:
            estimate(name,d,outcome,kind);r=json.loads((OUT/(name+'.json')).read_text())
            for c in r['coefficients']:
                row={'model':name,'outcome':outcome,'n':r['n'],'term':c['term'],'beta':c['beta'],'multiplier':c['multiplier']}
                for lag in ['6','12']:
                    row['hac'+lag+'_lo'],row['hac'+lag+'_hi']=c['hac'+lag]['multiplier_ci95']
                rows.append(row)
        except Exception as e:
            errors[name]={'error':str(e),'traceback':traceback.format_exc()};print('FAILED',name,str(e),flush=True)
    (OUT/'fit_errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    pd.DataFrame(rows).to_csv(OUT/'coefficients.csv',index=False)
    print('ALL AUGMENTED FITS FINISHED',errors.keys(),flush=True)

def bootstrap():
    broad,_=panels();bases={}
    for outcome,suffix in [('quantity','quantity'),('value_eur','value')]:
        bases[outcome]=estimate('rest_preferred_'+suffix,broad,outcome)
    for outcome,(d,r) in bases.items():
        assert np.array_equal(d[['reporter','origin','category','month']].to_numpy(),bases['quantity'][0][['reporter','origin','category','month']].to_numpy())
    target=OUT/'paired_block_draws.json';draws=[]
    if target.exists():
        prior=json.loads(target.read_text())
        if prior['fingerprint']==FP:draws=prior['draws']
    done={(x['outcome'],x['draw']) for x in draws};T=60;L=12
    for draw in range(199):
        rng=np.random.default_rng(20261027+draw);offset=int(rng.integers(0,L));block=(np.arange(T)+offset)//L
        weights=rng.exponential(1,size=block.max()+1)[block];weights/=weights.mean()
        for outcome,(d,r) in bases.items():
            if (outcome,draw) in done:continue
            try:
                monthcodes=np.unique(d.month,return_inverse=True)[1]
                rb=engine.fit(d,outcome,weights=weights[monthcodes],warm=r,need_cov=False)
                item={'outcome':outcome,'draw':draw,'offset':offset,'beta':rb['beta'].tolist(),'iterations':rb['iterations'],
                      'elapsed_seconds':rb['elapsed_seconds'],'score_error':max(rb['max_fe_score_over_total_y'],rb['max_x_score_over_total_y']),'success':True}
            except Exception as e:item={'outcome':outcome,'draw':draw,'success':False,'error':str(e)}
            draws.append(item)
            target.write_text(json.dumps({'fingerprint':FP,'names':bases['quantity'][1]['names'],'draws':draws},indent=2)+'\n')
        if draw%10==0 or draw==198:print('PAIRED BLOCK',draw+1,'/199',[(x['outcome'],x['success'],x.get('elapsed_seconds'),x.get('error')) for x in draws if x['draw']==draw],flush=True)
    summary={'fingerprint':FP,'method':'199 random-offset exponential block-length12 likelihood multiplier draws; same month weights for quantity and value; all preferred PPML refitted. Percentile sensitivity intervals, not causal identification.','seed':20261027,'outcomes':{}}
    for outcome,(d,r) in bases.items():
        records=[x for x in draws if x['outcome']==outcome and x['success']];B=np.array([x['beta'] for x in records]);cs=[]
        for j,name in enumerate(r['names']):
            lo,median,hi=np.quantile(np.exp(B[:,j]),[.025,.5,.975]);cs.append({'term':name,'point_multiplier':float(np.exp(r['beta'][j])),'multiplier_ci95':[float(lo),float(hi)],'median':float(median)})
        summary['outcomes'][outcome]={'successful':len(records),'failed':199-len(records),'coefficients':cs}
    paired=[]
    for draw in range(199):
        a=[x for x in draws if x['draw']==draw and x['outcome']=='quantity' and x['success']]
        b=[x for x in draws if x['draw']==draw and x['outcome']=='value_eur' and x['success']]
        if a and b:paired.append(np.array(b[0]['beta'])-np.array(a[0]['beta']))
    B=np.array(paired);summary['paired_ratio_of_mean_indices']={'successful_pairs':len(paired),'interpretation':'Ratio of value- and quantity-model relative mean multipliers. Does not estimate E[value/quantity], constant-quality prices, retail prices, or tariff pass-through.','coefficients':[]}
    for j,name in enumerate(bases['quantity'][1]['names']):
        if '__definitive' not in name:continue
        lo,hi=np.quantile(np.exp(B[:,j]),[.025,.975]);point=np.exp(bases['value_eur'][1]['beta'][j]-bases['quantity'][1]['beta'][j])
        summary['paired_ratio_of_mean_indices']['coefficients'].append({'term':name,'point_ratio':float(point),'paired_block_ci95':[float(lo),float(hi)]})
    (OUT/'paired_block_summary.json').write_text(json.dumps(summary,indent=2)+'\n')

def validate():
    broad,four=panels();d,r=estimate('baseline_engine_equivalence',four,'quantity','verification')
    old=json.loads((ROOT/'results/full/primary_quantity.json').read_text());diff=float(np.max(np.abs(r['beta']-np.array([c['beta'] for c in old['coefficients']]))))
    assert diff<1e-7
    d=broad[broad.reporter.isin(['BE','DE'])].copy();d,sep=engine.trim_separation(d,'quantity');r=engine.fit(d,'quantity')
    X,names=engine.design(d);A=engine.dummy_matrix(engine.fe_codes(d),X);y=d.quantity.to_numpy(float);y/=y.mean()
    eta=np.zeros(len(y));theta=np.zeros(A.shape[1]);obj=lambda e:float(np.sum(y*e-np.exp(e)))
    for it in range(100):
        mu=np.exp(eta);z=eta+(y-mu)/mu;sw=np.sqrt(mu);ls=lsmr(A.multiply(sw[:,None]),sw*z,atol=1e-12,btol=1e-12,maxiter=20000)
        proposal=A@ls[0];step=1.
        while obj(eta+step*(proposal-eta))<obj(eta)-1e-8:
            step/=2
            if step<1e-8:raise RuntimeError('Independent validation line search failed')
        enew=eta+step*(proposal-eta);theta+=step*(ls[0]-theta);delta=np.max(np.abs(enew-eta));eta=enew
        if delta<1e-8:break
    error=float(np.max(np.abs(theta[:X.shape[1]]-r['beta'])));assert error<1e-6
    result={'fingerprint':FP,'baseline_equivalence_max_beta_difference':diff,'new_four_FE_independent_sparse_max_beta_difference':error,
            'independent_n':len(d),'independent_zero_observations':int((d.quantity==0).sum()),'sparse_iterations':it+1,
            'max_eta_difference':float(np.max(np.abs(eta-r['eta']))),'passed':True,'separation':sep}
    (OUT/'numerical_validation.json').write_text(json.dumps(result,indent=2)+'\n');print('NUMERICAL VALIDATION',result,flush=True)

if __name__=='__main__':
    if '--bootstrap' in sys.argv:bootstrap()
    elif '--validation' in sys.argv:validate()
    else:all_fits()
