"""Firth logistic estimates with FLIC correction; no tuned hyperparameters.

References: Firth (1993), DOI 10.1093/biomet/80.1.27;
Puhr et al. (2017), DOI 10.1002/sim.7273.
Independent generic-optimizer verification is in validate.py.
"""
import numpy as np
from scipy.special import expit,logit
from scipy.optimize import brentq,minimize

def objective_score(beta,Z,y):
 eta=Z@beta;p=expit(eta);w=np.maximum(p*(1-p),1e-15);I=Z.T@(w[:,None]*Z)
 sign,ld=np.linalg.slogdet(I)
 if sign<=0:raise np.linalg.LinAlgError('Information is not positive definite')
 inv=np.linalg.inv(I);hat=w*np.sum((Z@inv)*Z,axis=1)
 score=Z.T@(y-p+hat*(.5-p))
 val=float(np.sum(y*eta-np.logaddexp(0,eta))+.5*ld)
 return val,score,I

def fit(x,y,max_iter=150,tol=1e-8):
 x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
 if x.ndim==1:x=x[:,None]
 if not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Nonfinite training values')
 if set(np.unique(y))!={0.,1.}:raise ValueError('Both outcome classes required')
 mean=x.mean(0);scale=x.std(0)
 if np.any(scale<1e-12):raise ValueError('Constant predictor')
 Z=np.column_stack([np.ones(len(y)),(x-mean)/scale]);rank=np.linalg.matrix_rank(Z)
 if rank!=Z.shape[1]:raise ValueError('Rank deficient design')
 beta=np.zeros(Z.shape[1]);beta[0]=logit((y.sum()+.5)/(len(y)+1));fallback=False
 for it in range(max_iter):
  val,score,I=objective_score(beta,Z,y)
  if np.max(np.abs(score))<tol:break
  step=np.linalg.solve(I,score)
  if np.max(np.abs(step))>5:step*=5/np.max(np.abs(step))
  accepted=False
  for j in range(35):
   candidate=beta+step*(.5**j)
   try:v=objective_score(candidate,Z,y)[0]
   except np.linalg.LinAlgError:continue
   if v>=val-1e-12:accepted=True;break
  if not accepted:break
  if np.max(np.abs(candidate-beta))<tol*.1:
   beta=candidate;break
  beta=candidate
 val,score,I=objective_score(beta,Z,y)
 if np.max(np.abs(score))>1e-6:
  fallback=True
  opt=minimize(lambda b:-objective_score(b,Z,y)[0],beta,jac=lambda b:-objective_score(b,Z,y)[1],method='BFGS',options={'gtol':1e-8,'maxiter':500})
  beta=opt.x;val,score,I=objective_score(beta,Z,y)
 if np.max(np.abs(score))>1e-5:raise RuntimeError(f'Firth score not converged: {np.max(np.abs(score))}')
 eta=Z@beta
 alpha=brentq(lambda a:float(expit(eta+a).sum()-y.sum()),-80,80,xtol=1e-13)
 raw=np.r_[beta[0]+alpha-np.dot(beta[1:]/scale,mean),beta[1:]/scale]
 return {'coef':raw,'firth_standardized':beta,'flic_shift':alpha,'mean':mean,'scale':scale,'objective':val,'score_max':float(np.max(np.abs(score))),'train_mean_probability':float(expit(eta+alpha).mean()),'train_event_rate':float(y.mean()),'n_train':len(y),'positives':int(y.sum()),'iterations':it+1,'optimizer_fallback':fallback,'condition':float(np.linalg.cond(I))}

def predict(model,x):
 return expit(np.column_stack([np.ones(len(np.atleast_2d(x))),np.atleast_2d(x)])@model['coef'])

def metrics(y,p):
 from sklearn.metrics import roc_auc_score
 y=np.asarray(y,dtype=float);p=np.asarray(p,dtype=float);q=np.clip(p,1e-12,1-1e-12);alarm=p>=.2
 n=len(y);pos=int(y.sum());tp=int(np.sum(alarm&(y==1)));fp=int(np.sum(alarm&(y==0)));fn=pos-tp;tn=n-pos-fp
 return {'n':n,'events':pos,'brier':float(np.mean((p-y)**2)),'log_loss':float(-np.mean(y*np.log(q)+(1-y)*np.log1p(-q))),'auc':float(roc_auc_score(y,p)) if 0<pos<n else np.nan,'mean_probability':float(p.mean()),'event_rate':float(y.mean()),'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,'recall':tp/pos if pos else np.nan,'precision':tp/(tp+fp) if tp+fp else np.nan,'false_alarm_rate':fp/(n-pos) if n>pos else np.nan}
