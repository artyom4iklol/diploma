"""Auditable HDFE PPML: IRLS + weighted alternating projections.

No count-distribution assumption is used for uncertainty. Normalizing the
outcome only shifts an absorbed intercept. Separation is explicitly checked.
"""
import time
import numpy as np
from scipy import sparse, optimize, stats

def codes(values):
    return np.unique(np.asarray(values,dtype=str),return_inverse=True)[1]

def fe_codes(df):
    m=df['reporter'].astype(str);o=df['origin'].astype(str);p=df['category'].astype(str);t=df['month'].astype(str)
    return [codes(m+'|'+o+'|'+p),codes(m+'|'+p+'|'+t),codes(o+'|'+t)]

def design(df,kind='phase'):
    cn=(df.origin.to_numpy()=='CN').astype(float)
    month=df.month.to_numpy(); arrays=[];names=[]
    if kind=='dynamic':
        quarters=sorted(df.quarter.unique()); reference='2023Q2'
        for cat in ['PHEV','HEV']:
            catmask=(df.category.to_numpy()==cat)*cn
            for q in quarters:
                if q==reference:continue
                arrays.append(catmask*(df.quarter.to_numpy()==q));names.append(cat+'__'+q)
    elif kind=='pretrend':
        tt=df.t.to_numpy()/12
        for cat in ['PHEV','HEV']:
            arrays.append(cn*(df.category.to_numpy()==cat)*tt); names.append(cat+'__pretrend_per_year')
    else:
        phases=[('announcement','2024-06','2024-06'),('provisional','2024-07','2024-10'),('definitive','2024-11','2025-12')]
        if kind=='investigation':phases=[('investigation','2023-09','2024-05')]+phases
        for cat in ['PHEV','HEV']:
            catmask=(df.category.to_numpy()==cat)*cn
            for name,start,end in phases:
                arrays.append(catmask*((month>=start)&(month<=end)));names.append(cat+'__'+name)
        if kind=='trends':
            # US and BEV references remove collinear origin-time/product effects.
            tt=df.t.to_numpy()/12
            for origin in ['CN','JP','KR']:
                for cat in ['PHEV','HEV']:
                    arrays.append((df.origin.to_numpy()==origin)*(df.category.to_numpy()==cat)*tt)
                    names.append(origin+'_'+cat+'__trend_per_year')
    return np.column_stack(arrays).astype(float),names

def dummy_matrix(groups,X=None):
    n=len(groups[0]); offset=0;rr=[];cc=[]
    for g in groups:
        rr.append(np.arange(n));cc.append(g+offset);offset+=int(g.max())+1
    A=sparse.coo_matrix((np.ones(sum(len(r) for r in rr)),(np.concatenate(rr),np.concatenate(cc))),shape=(n,offset)).tocsr()
    return sparse.hstack([sparse.csr_matrix(X),A],format='csr') if X is not None else A

def trim_separation(df,outcome,kind='phase',linear_program=True):
    """Delete only separated zero-y rows, never positive trade.

    First all-zero FE groups, then bounded LP: A_positive d=0,
    A_zero d<=0, minimize sum(A_zero d). Any negative optimum certifies
    zero rows whose predictor can diverge negatively at no positive-y cost.
    """
    start=len(df); removed_fe=0;removed_lp=0; lp_records=[]
    df=df.copy().reset_index(drop=True)
    for outer in range(8):
        while True:
            y=df[outcome].to_numpy(float); groups=fe_codes(df);keep=np.ones(len(df),bool)
            for g in groups:
                sums=np.bincount(g,weights=y,minlength=g.max()+1)
                keep &= sums[g]>0
            if keep.all():break
            removed_fe+=int((~keep).sum());df=df.loc[keep].reset_index(drop=True)
        y=df[outcome].to_numpy(float)
        if not linear_program or not np.any(y==0):break
        X,names=design(df,kind);A=dummy_matrix(fe_codes(df),X);Az=A[y==0];Ap=A[y>0]
        c=np.asarray(Az.sum(axis=0)).ravel()
        result=optimize.linprog(c,A_ub=Az,b_ub=np.zeros(Az.shape[0]),A_eq=Ap,b_eq=np.zeros(Ap.shape[0]),bounds=(-1,1),method='highs',options={'time_limit':90,'dual_feasibility_tolerance':1e-8,'primal_feasibility_tolerance':1e-8})
        rec={'success':bool(result.success),'message':result.message,'objective':float(result.fun) if result.fun is not None else None,'n':len(df)}
        lp_records.append(rec)
        if not result.success:raise RuntimeError('Separation LP did not finish: '+str(rec))
        vals=np.asarray(Az@result.x).ravel();bad=vals < -1e-7
        if not bad.any():break
        idx=np.flatnonzero(y==0)[bad];keep=np.ones(len(df),bool);keep[idx]=False
        removed_lp+=len(idx);df=df.loc[keep].reset_index(drop=True)
    else:raise RuntimeError('Separation pruning exceeded 8 passes')
    return df,{'input_n':start,'retained_n':len(df),'all_zero_fe_removed':removed_fe,'other_separated_zero_rows':removed_lp,'positive_outcome_removed':0,'lp':lp_records}

def residualize(A,w,groups,tol=2e-10,max_cycles=2000):
    R=np.array(A,dtype=float,copy=True)
    sums=[np.bincount(g,weights=w,minlength=g.max()+1) for g in groups]
    for cycle in range(max_cycles):
        max_adjust=0.
        for g,den in zip(groups,sums):
            adj=np.column_stack([np.bincount(g,weights=w*R[:,j],minlength=len(den))/den for j in range(R.shape[1])])
            R-=adj[g];max_adjust=max(max_adjust,float(np.max(np.abs(adj))))
        if max_adjust<tol:return R,cycle+1
    raise RuntimeError('Weighted FE projections did not converge: '+str(max_adjust))

def fit(df,outcome,kind='phase',weights=None,warm=None,need_cov=True,maxiter=120):
    start=time.monotonic();yraw=df[outcome].to_numpy(float);scale=yraw.mean();y=yraw/scale
    X,names=design(df,kind);groups=fe_codes(df);n,k=X.shape
    ow=np.ones(n) if weights is None else np.asarray(weights,float)
    assert np.all(ow>0) and np.all(y>=0)
    eta=np.zeros(n) if warm is None else warm['eta'].copy()
    beta=np.zeros(k) if warm is None else warm['beta'].copy()
    def objective(e):
        if np.max(e)>700:return -np.inf
        return np.dot(ow,y*e-np.exp(e))
    obj=objective(eta);converged=False;hist=[]
    for it in range(maxiter):
        mu=np.exp(eta); w=ow*mu
        if np.min(w)<=0:raise RuntimeError('Underflow: unresolved separation')
        z=eta+(y-mu)/mu
        R,cycles=residualize(np.column_stack([X,z]),w,groups)
        Xt=R[:,:k];zt=R[:,k];H=Xt.T@(w[:,None]*Xt)
        if np.linalg.matrix_rank(H,tol=np.linalg.norm(H,2)*1e-11)<k:raise RuntimeError('Structural regressors unidentified/rank deficient')
        bnew=np.linalg.solve(H,Xt.T@(w*zt))
        proposed=z-(zt-Xt@bnew)
        step=1.
        while step>=1/1024:
            enew=eta+step*(proposed-eta);on=objective(enew)
            if on>=obj-1e-9*max(1,abs(obj)):break
            step/=2
        if step<1/1024:raise RuntimeError('PPML line search failed')
        db=float(np.max(np.abs(step*(bnew-beta))));de=float(np.max(np.abs(enew-eta)))
        hist.append({'iteration':it+1,'objective':float(on),'max_beta_change':db,'max_eta_change':de,'step':step,'projection_cycles':cycles})
        eta=enew;beta=beta+step*(bnew-beta);obj=on
        if db<2e-8 and de<2e-7:converged=True;break
    if not converged:raise RuntimeError('PPML did not converge: '+str(hist[-1]))
    mu=np.exp(eta);res=ow*(y-mu)
    fe_score=max(float(np.max(np.abs(np.bincount(g,weights=res,minlength=g.max()+1)))) for g in groups)
    structural_score=float(np.max(np.abs(X.T@res)))
    result={'names':names,'beta':beta,'eta':eta,'mu':mu*scale,'scale':scale,'n':n,'iterations':len(hist),'objective_normalized':float(obj),
            'max_fe_score_over_total_y':fe_score/np.dot(ow,y),'max_x_score_over_total_y':structural_score/np.dot(ow,y),
            'elapsed_seconds':time.monotonic()-start,'converged':True,'iteration_history':hist,'min_fitted':float(mu.min()*scale),
            'max_fitted':float(mu.max()*scale),'zero_observations':int((yraw==0).sum()),'n_months':int(df.month.nunique())}
    if need_cov:
        Xt,cycles=residualize(X,ow*mu,groups);H=Xt.T@((ow*mu)[:,None]*Xt);inv=np.linalg.inv(H)
        scores=Xt*res[:,None];months=codes(df.month.to_numpy());T=months.max()+1
        sm=np.column_stack([np.bincount(months,weights=scores[:,j],minlength=T) for j in range(k)])
        result['hessian']=H;result['month_scores']=sm;result['covariance']={}
        for lag in [6,12]:
            meat=sm.T@sm
            for ell in range(1,min(lag,T-1)+1):
                cross=sm[ell:].T@sm[:-ell];meat+=(1-ell/(lag+1))*(cross+cross.T)
            cov=inv@meat@inv*T/(T-k)
            result['covariance'][str(lag)]=cov
        result['hessian_condition']=float(np.linalg.cond(H));result['projection_cycles_final']=cycles
    return result

def summarize(result):
    skip={'eta','mu','hessian','month_scores','beta','covariance'}
    out={k:v for k,v in result.items() if k not in skip};out['coefficients']=[]
    crit=float(stats.t.ppf(.975,result['n_months']-1))
    for j,name in enumerate(result['names']):
        row={'term':name,'beta':float(result['beta'][j]),'multiplier':float(np.exp(result['beta'][j]))}
        for lag,cov in result.get('covariance',{}).items():
            se=float(np.sqrt(max(cov[j,j],0)));lo=result['beta'][j]-crit*se;hi=result['beta'][j]+crit*se
            row['hac'+lag]={'se_log':se,'beta_ci95':[float(lo),float(hi)],'multiplier_ci95':[float(np.exp(lo)),float(np.exp(hi))]}
        out['coefficients'].append(row)
    out['covariance']={k:v.tolist() for k,v in result.get('covariance',{}).items()}
    out['ci_method']='Synchronous month-score Bartlett HAC, T/(T-k structural parameters), t(T-1). Does not correct incidental-parameter bias or guarantee causal coverage.'
    return out

def joint_test(result,indices,lag=6):
    b=result['beta'][indices];V=result['covariance'][str(lag)][np.ix_(indices,indices)]
    rank=int(np.linalg.matrix_rank(V));q=float(b@np.linalg.pinv(V)@b)
    return {'chi2':q,'df_rank':rank,'p_asymptotic':float(stats.chi2.sf(q,rank)),'warning':'Many leads and only monthly time support; asymptotic diagnostic, not proof of parallel trends.'}
