"""Independent full-panel check: profile two-origin PPML as weighted logit.

For each importer-product-month pair, profiling out its shared Poisson FE
sets the fitted total equal to the observed total. The remaining objective
is the binomial/quasi-binomial kernel for China's share, with total weights.
This is an equivalent estimator, not an additional model or new theory.
For euro values the kernel is pseudo-likelihood, not a literal count law.
"""
from pathlib import Path
import json, pickle
import numpy as np
from scipy import linalg, special
from ppml_engine_augmented import design, codes, dummy_matrix

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/augmented';results={}
for outcome,suffix in [('quantity','quantity'),('value_eur','value')]:
    with (ROOT/'data/augmented_cache'/('rest_preferred_'+suffix+'.pkl')).open('rb') as f:cache=pickle.load(f)
    d=cache['df'].copy();r=cache['result'];X,names=design(d)
    for j,name in enumerate(names):d['x'+str(j)]=X[:,j]
    d['fitted_mu']=r['mu'];keys=['reporter','category','month']
    pair=d.groupby(keys).origin.transform('nunique')==2;d=d[pair]
    cn=d[d.origin=='CN'].set_index(keys).sort_index();rest=d[d.origin=='REST'].set_index(keys).reindex(cn.index)
    xcols=['x'+str(j) for j in range(len(names))];X=cn[xcols].to_numpy()-rest[xcols].to_numpy();k=X.shape[1]
    mp=[m+'|'+p for m,p,t in cn.index];tt=[t for m,p,t in cn.index];pc=[p+'|'+t[-2:] for m,p,t in cn.index]
    D=dummy_matrix([codes(mp),codes(tt),codes(pc)]).toarray()
    _,R,piv=linalg.qr(D,mode='economic',pivoting=True);rank=int((np.abs(np.diag(R))>1e-9).sum())
    A=np.column_stack([X,D[:,piv[:rank]]]);assert np.linalg.matrix_rank(A)==A.shape[1]
    y0=cn[outcome].to_numpy(float);n0=y0+rest[outcome].to_numpy(float);scale=n0.mean();y=y0/scale;n=n0/scale
    theta=np.zeros(A.shape[1]);eta=A@theta
    obj=lambda e:float(np.sum(y*e-n*np.logaddexp(0,e)))
    for it in range(100):
        p=special.expit(eta);w=n*p*(1-p);assert (w>0).all()
        score=A.T@(y-n*p);H=A.T@(w[:,None]*A);delta=linalg.solve(H,score,assume_a='pos')
        step=1.
        while obj(eta+step*(A@delta))<obj(eta)-1e-9:
            step/=2
            if step<1e-8:raise RuntimeError('Share verification line search failed')
        theta+=step*delta;eta=A@theta
        if np.max(np.abs(step*delta))<1e-9:break
    else:raise RuntimeError('Independent share fit failed to converge')
    p=special.expit(eta);score=A*(y-n*p)[:,None];month=codes(tt);T=month.max()+1
    S=np.column_stack([np.bincount(month,weights=score[:,j],minlength=T) for j in range(A.shape[1])])
    H=A.T@((n*p*(1-p))[:,None]*A);inv=linalg.inv(H);covdiff={}
    for lag in [6,12]:
        meat=S.T@S
        for ell in range(1,lag+1):
            cross=S[ell:].T@S[:-ell];meat+=(1-ell/(lag+1))*(cross+cross.T)
        V=inv@meat@inv*T/(T-k)
        covdiff[str(lag)]=float(np.max(np.abs(V[:k,:k]-r['covariance'][str(lag)])))
    beta_error=float(np.max(np.abs(theta[:k]-r['beta'])))
    fitted_share=cn.fitted_mu.to_numpy()/(cn.fitted_mu.to_numpy()+rest.fitted_mu.to_numpy())
    share_error=float(np.max(np.abs(p-fitted_share)))
    results[outcome]={'flow_pairs':len(cn),'paired_flow_rows':len(cn)*2,'uninformative_singleton_rows_excluded':r['n']-len(cn)*2,
                      'nuisance_rank_after_profiling':rank,'structural_parameters':k,'iterations':it+1,
                      'max_beta_difference':beta_error,'max_fitted_share_difference':share_error,'max_HAC_covariance_difference':covdiff,
                      'passed':beta_error<1e-6 and share_error<1e-7 and max(covdiff.values())<1e-6,
                      'fingerprint':cache['fingerprint']}
    assert results[outcome]['passed'],results[outcome]
result={'passed':all(x['passed'] for x in results.values()),'method':'Independent dense Newton weighted-share quasi-logit; FE profiled analytically; nuisance collinearity removed by pivoted QR. This is identical to the preferred two-origin PPML, not a different hypothesis test.','outcomes':results,
        'references':['https://doi.org/10.2307/2348134','https://doi.org/10.1177/1536867X0400400304'],
        'limits':'Equality is algebraic for the fitted objective and robust scores. It does not establish a binomial count distribution, remove time-dependence issues or create causal identification.'}
(OUT/'conditional_share_equivalence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
