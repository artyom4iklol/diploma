from pathlib import Path
import json,shutil,hashlib,platform
import numpy as np,pandas as pd,scipy
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
P=Path(__file__).resolve().parent
OLD=P.parent/'gar_stage07/previous/growth_at_risk_06/03_data/current_snapshot'
for f in ['processed/quarterly.csv','raw/ecb_ciss_ea.csv','raw/ecb_ciss_us.csv','raw/fred_nfci.csv']:
 if not (P/'raw'/Path(f).name).exists(): shutil.copy2(OLD/f,P/'raw'/Path(f).name)
config={'date':'2026-10-02','question':'CISS US versus NFCI incremental forecast information conditional on EA CISS, lagged GDP growth and ESI EA20','tau':0.1,'horizons':[1,4],'sample':['1995Q1','2025Q4'],'first_origin':'2010Q1','variants':['esi_buffer7','esi_first2','esi_drop_dec'],'main':'esi_first2','main_delay_calendar_days':7,'shortbuffer':'CISS +1 business day; NFCI +6 calendar days (conservative Thursday assumption)','esi':'main first two months every quarter; diagnostic drop December only; old esi_buffer7 infeasible calendar retained for comparison; current vintages; no complete historical calendar reconstructed','train':'label end <= origin-1','periods':'target intervals: pre2020, COVID overlap2020Q1..2021Q4, wholly2022Q1..2025Q4','bootstrap':{'replications':5000,'block_lengths':[4,8],'seed':30092026,'type':'circular block resampling fixed paired forecast losses, no refit; descriptive percentile intervals; no multiplicity adjustment'},'status':'stage11 calendar correction specified before corrected runs; old outcomes known; not preregistered; first2 conservative assumption, not certified real time','not_real_time':True}
(P/'PROTOCOL.json').write_text(json.dumps(config,indent=2))
j=json.loads((P/'raw/esi.json').read_text());times=j['dimension']['time']['category']['index'];es=pd.Series({pd.Period(t,freq='M'):j['value'].get(str(i),np.nan) for t,i in times.items()}).sort_index();es.name='esi';es.to_csv(P/'raw/esi_monthly.csv')
sub=es.loc['1995-01':'2025-12'];assert len(sub)==372 and sub.notna().all()
esq=es.groupby(es.index.asfreq('Q')).agg(['mean','count']);assert esq.loc['1995Q1':'2025Q4','count'].eq(3).all()
d=pd.read_csv(P/'raw/quarterly.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q');d['esi']=esq['mean'];d['gx']=(400*np.log(d.gdp_ea).diff()).shift(1)
raw={}
for name,file,col,dat in [('ea','ecb_ciss_ea.csv','OBS_VALUE','TIME_PERIOD'),('us','ecb_ciss_us.csv','OBS_VALUE','TIME_PERIOD'),('nfci','fred_nfci.csv','NFCI','observation_date')]:
 x=pd.read_csv(P/'raw'/file);raw[name]=pd.Series(pd.to_numeric(x[col],errors='coerce').values,index=pd.to_datetime(x[dat])).sort_index().dropna();assert not raw[name].index.duplicated().any()
availability=[]
for mode in ['buffer7','shortbuffer']:
 for name,x in raw.items():
  assumed=x.index+pd.Timedelta(days=7) if mode=='buffer7' else x.index+pd.Timedelta(days=6) if name=='nfci' else x.index+pd.offsets.BDay(1)
  vals=[]
  for q in d.index:
   take=(x.index>=q.start_time)&(x.index<=q.end_time)&(assumed<=q.end_time)
   xx=x[take];assert len(xx)>0
   vals.append(xx.mean());availability.append({'mode':mode,'series':name,'quarter':str(q),'n':len(xx),'last_observation':str(xx.index.max().date()),'last_assumed_available':str(assumed[take].max().date()),'forecast_deadline':str(q.end_time.date())})
  d[name+'_'+mode]=vals
pd.DataFrame(availability).to_csv(P/'results/availability.csv',index=False);d.to_csv(P/'results/model_data.csv')
assert d[['esi','ea_buffer7','us_buffer7','nfci_buffer7']].notna().all().all()
(P/'results/data_audit.json').write_text(json.dumps({'esi_source':'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ei_bssi_m_r2?lang=en&geo=EA20&indic=BS-ESI-I&freq=M&s_adj=SA','esi_updated':j['updated'],'esi_selected_months':len(sub),'esi_missing':int(sub.isna().sum()),'quarters':len(d),'ESI_geo':j['dimension']['geo']['category']['label'],'vintages':'ESI September29 downloadSeptember30; GDP/CISS/NFCI prior stage06 snapshots retained','CISS_geo':'U2 changing composition; mismatch with fixed EA20 remains','not_actual_release_dates':True},indent=2))
def loss(u):return np.maximum(.1*u,-.9*u)
def fitpred(train,test,cols,method='highs'):
 y=train.target.to_numpy();mu=train[cols].mean().to_numpy();sd=train[cols].std(ddof=0).to_numpy();assert (sd>0).all();X=np.c_[np.ones(len(y)),(train[cols].to_numpy()-mu)/sd];xp=np.r_[1,(test[cols].to_numpy(dtype=float)-mu)/sd];n,k=X.shape
 r=linprog(np.r_[np.zeros(k),np.full(n,.1),np.full(n,.9)],A_eq=hstack([csr_matrix(X),eye(n),-eye(n)],format='csr'),b_eq=y,bounds=[(None,None)]*k+[(0,None)]*(2*n),method=method)
 assert r.success,r.message
 b=r.x[:k];assert abs(loss(y-X@b).sum()-r.fun)<1e-6
 return float(xp@b),float(r.fun),dict(zip(['const']+cols,np.r_[b[0]-(b[1:]*mu/sd).sum(),b[1:]/sd]))
F=[];G=[];checks=[]
for variant in config['variants']:
 v=d.copy()
 if variant=='esi_first2':v['esi']=es[es.index.month%3!=0].groupby(es[es.index.month%3!=0].index.asfreq('Q')).mean()
 if variant=='esi_drop_dec':v['esi']=es[es.index.month!=12].groupby(es[es.index.month!=12].index.asfreq('Q')).mean()
 mode='shortbuffer' if variant=='esi_shortbuffer' else 'buffer7'
 for name in raw:v[name]=v[name+'_'+mode]
 for h in [1,4]:
  v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea)
  base=['gx','ea']+([] if variant=='noesi_buffer7' else ['esi'])
  models={'HIST':[],'AR':['gx'],'BASE':base,'US_CISS':base+['us'],'US_NFCI':base+['nfci']}
  for t in v.index[v.index>=pd.Period('2010Q1')]:
   if pd.isna(v.at[t,'target']):continue
   mask=(v.index+h<=t-1)&v[['target','gx','ea','us','nfci','esi']].notna().all(axis=1)
   if variant=='esi_no_covid_train':mask &= ~((v.index+1<=pd.Period('2021Q4'))&(v.index+h>=pd.Period('2020Q1')))
   train=v.loc[mask];assert len(train)>=35
   episode='pre2020' if t+h<pd.Period('2020Q1') else '2022_2025' if t+1>=pd.Period('2022Q1') else 'covid_overlap'
   for m,cols in models.items():
    pred=float(np.quantile(train.target,.1,method='inverted_cdf')) if not cols else fitpred(train,v.loc[t],cols)[0]
    if cols:
     # Selected independent solver checks; no future observations supplied to estimation.
     if variant=='esi_buffer7' and m=='US_CISS' and str(t) in ['2010Q1','2020Q4','2025Q1']:
      p2,o2,_=fitpred(train,v.loc[t],cols,'highs-ipm');p1,o1,_=fitpred(train,v.loc[t],cols);assert abs(o1-o2)<1e-6;checks.append({'h':h,'origin':str(t),'objective_difference':o2-o1,'prediction_difference':p2-p1})
     _,_,b=fitpred(train,v.loc[t],cols);G.append({'variant':variant,'h':h,'origin':str(t),'model':m,**b,'growth_outside_train':bool(v.at[t,'gx']<train.gx.min() or v.at[t,'gx']>train.gx.max()),'esi_outside_train':bool(v.at[t,'esi']<train.esi.min() or v.at[t,'esi']>train.esi.max())})
    actual=float(v.at[t,'target']);F.append({'variant':variant,'h':h,'origin':str(t),'target_end':str(t+h),'episode':episode,'model':m,'n_train':len(train),'last_train_target':str(max(train.index+h)),'actual':actual,'forecast':pred,'loss':float(loss(actual-pred)),'hit':int(actual<pred)})
 print(variant,'done',flush=True)
f=pd.DataFrame(F);f.to_csv(P/'results/forecasts.csv',index=False);pd.DataFrame(G).to_csv(P/'results/coefficients.csv',index=False)
f.groupby(['variant','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(P/'results/scores.csv')
f.groupby(['variant','h','episode','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),hit_rate=('hit','mean')).to_csv(P/'results/episode_scores.csv')
rng=np.random.default_rng(30092026);C=[];LO=[]
for (variant,h),grp in f.groupby(['variant','h']):
 w=grp.pivot(index='origin',columns='model',values='loss');n=len(w)
 for a,b in [('US_CISS','BASE'),('US_NFCI','BASE'),('US_NFCI','US_CISS'),('US_CISS','HIST'),('US_NFCI','HIST'),('BASE','HIST')]:
  va=w[a].to_numpy();vb=w[b].to_numpy();row={'variant':variant,'h':h,'comparison':a+'/'+b,'n':n,'ratio':va.mean()/vb.mean(),'difference':(va-vb).mean()}
  for L in [4,8]:
   ix=((rng.integers(0,n,size=(5000,int(np.ceil(n/L))))[:,:,None]+np.arange(L))%n).reshape(5000,-1)[:,:n];rr=va[ix].mean(axis=1)/vb[ix].mean(axis=1)
   row[f'lo_L{L}'],row[f'hi_L{L}']=np.quantile(rr,[.025,.975])
  C.append(row)
  for i,t in enumerate(w.index):LO.append({'variant':variant,'h':h,'comparison':a+'/'+b,'omitted_origin':t,'ratio_without':(va.sum()-va[i])/(vb.sum()-vb[i]),'gain_at_origin':vb[i]-va[i],'net_gain_share':(vb[i]-va[i])/(vb-va).sum() if abs((vb-va).sum())>1e-10 else np.nan})
pd.DataFrame(C).to_csv(P/'results/comparisons.csv',index=False);pd.DataFrame(LO).to_csv(P/'results/influence.csv',index=False)
assert f.groupby(['variant','h','origin']).model.nunique().eq(5).all()
assert all(pd.Period(r.last_train_target)<=pd.Period(r.origin)-1 for r in f.itertuples())
assert f.query('h==1').groupby(['variant','model']).size().eq(63).all();assert f.query('h==4').groupby(['variant','model']).size().eq(60).all()
(P/'results/validation.json').write_text(json.dumps({'solver_checks':checks,'all_lp_solved':True,'training_labels_cutoff_passed':True,'common_dates_passed':True,'rows':len(f),'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__},'protocol_sha256':hashlib.sha256((P/'PROTOCOL.json').read_bytes()).hexdigest()},indent=2))
print(pd.DataFrame(C).query("variant=='esi_buffer7'").to_string(index=False))
