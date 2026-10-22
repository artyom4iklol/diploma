"""Validate the chapter against frozen forecasts. No model fitting or downloads."""
from pathlib import Path
import json, re, hashlib
import numpy as np
import pandas as pd

P=Path(__file__).resolve().parent
R=P.parent/'revision19/results'
E=P/'evidence'; E.mkdir(exist_ok=True)
text=(P/'Chapter_2_Empirical_Analysis.md').read_text()
f=pd.read_csv(R/'ANFCI_forecasts.csv')
assert len(f)==2373 and not f.duplicated(['variant','information','h','origin','model']).any()
for suffix in ['','_latest']:
 u=f['actual'+suffix]-f.forecast
 np.testing.assert_allclose(f['loss'+suffix],np.maximum(.1*u,-.9*u),atol=1e-12)
 assert np.array_equal(f['hit'+suffix],(u<0).astype(int))
s=f.groupby(['variant','information','h','model']).agg(n=('loss','size'),mean_loss=('loss','mean'),mean_loss_latest=('loss_latest','mean'),hits=('hit','sum'),hit_rate=('hit','mean')).reset_index()
old=pd.read_csv(R/'ANFCI_scores.csv');j=s.merge(old,on=['variant','information','h','model'],suffixes=('_new','_old'),validate='one_to_one')
for col in ['n','mean_loss','mean_loss_latest','hits','hit_rate']:np.testing.assert_allclose(j[col+'_new'],j[col+'_old'],atol=1e-12)
order=['HIST','AR','AR_ESI','AR_ESI_NFCI','AR_ESI_ANFCI']
names={m:m.replace('_',' + ') for m in order}
def dec(x,n=4):return f'{x:.{n}f}'.replace('.',',')
main=s.query("variant=='expanding' and information=='historical'")
main.to_csv(E/'main_scores.csv',index=False)
for m in order:
 a=main[main.model.eq(m)].set_index('h');vals=[names[m]]
 for h in [1,4]:
  r=a.loc[h];vals += [dec(r.mean_loss),f'{int(r.hits)}/{int(r.n)}; {dec(100*r.hit_rate,1)}%']
 assert '| '+' | '.join(vals)+' |' in text
labels={'expanding':'Основное расширяющееся окно','rolling52':'Скользящее окно, 52 наблюдения','no_covid_training':'Без пандемийных целей в обучении','omit_origin_2020Q4':'Основные прогнозы без 2020Q4 в оценке'}
ratios=[];dominance=[]
for (variant,h),g in f[f.information.eq('historical')].groupby(['variant','h']):
 w=g.pivot(index='origin',columns='model',values='loss')
 options=[(variant,w)]
 if variant=='expanding':
  options.append(('omit_origin_2020Q4',w.drop('2020Q4')))
  for m in ['AR_ESI_NFCI','AR_ESI_ANFCI']:
   r=(w[m].sum()-w[m])/(w.HIST.sum()-w.HIST);assert (r>1).all()
   dominance.append(dict(h=int(h),model=m,n=len(w),HIST_better_count=int((r>1).sum()),minimum_ratio=float(r.min())))
 for label,a in options:
  r=[a.AR_ESI_ANFCI.mean()/a[b].mean() for b in ['AR_ESI','AR_ESI_NFCI','HIST']]
  assert '| '+' | '.join([labels[label],str(h),str(len(a))]+[dec(x) for x in r])+' |' in text
  ratios.append(dict(variant=label,h=int(h),n=len(a),ratio_AR_ESI=r[0],ratio_NFCI=r[1],ratio_HIST=r[2]))
pd.DataFrame(ratios).to_csv(E/'relative_scores.csv',index=False)
vintages=[]
for m in ['AR_ESI_NFCI','AR_ESI_ANFCI']:
 vals=[names[m]]
 for h in [1,4]:
  a=f[f.variant.eq('expanding')&f.h.eq(h)&f.model.eq(m)]
  hist=a[a.information.eq('historical')].loss.mean();late=a[a.information.ne('historical')].loss.mean()
  vals += [dec(hist),dec(late)];vintages.append(dict(model=m,h=h,historical_loss=hist,late_index_loss=late))
 assert '| '+' | '.join(vals)+' |' in text
pd.DataFrame(vintages).to_csv(E/'index_vintages.csv',index=False)
v=pd.read_csv(R/'vintaged_model_frames_ANFCI.csv');v=v[v.origin.eq('2020Q4')].copy();v.index=pd.PeriodIndex(v.quarter,freq='Q');t=pd.Period('2020Q4')
c=pd.read_csv(R/'ANFCI_coefficients.csv');c=c.query("variant=='expanding' and information=='historical' and origin=='2020Q4'")
cols={'HIST':[],'AR':['gx'],'AR_ESI':['gx','esi'],'AR_ESI_NFCI':['gx','esi','nfci'],'AR_ESI_ANFCI':['gx','esi','anfci']}
d={'origin':str(t),'forecast_date':'2021-01-15','predictors':{k:float(v.at[t,k]) for k in ['gx','esi','nfci','anfci']},'horizons':[]}
for h in [1,4]:
 mask=(v.index>=pd.Period('1995Q3'))&(v.index+h<=t-1)&v[['y'+str(h),'gx','esi','nfci','anfci']].notna().all(axis=1)
 z={'h':h,'n_train':int(mask.sum()),'training_gx_min':float(v.loc[mask,'gx'].min()),'training_gx_max':float(v.loc[mask,'gx'].max()),'models':[]}
 for m in order:
  b=c[c.h.eq(h)&c.model.eq(m)].iloc[0];a=f.query("variant=='expanding' and information=='historical' and origin=='2020Q4' and h==@h and model==@m").iloc[0]
  parts={'const':float(b['const'])};parts.update({k:float(b[k]*v.at[t,k]) for k in cols[m]})
  assert abs(sum(parts.values())-a.forecast)<1e-10
  z['models'].append(dict(model=m,forecast=float(a.forecast),actual=float(a.actual),loss=float(a.loss),coefficients={k:float(b[k]) for k in ['const']+cols[m]},forecast_addends=parts))
 d['horizons'].append(z)
(E/'forecast_2021_01_15_diagnostic.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert f.query("variant=='expanding' and information=='historical' and episode=='2022_2025'").hit.sum()==0
body21=(P/'Chapter_2_1_Data_and_Information_Set.md').read_text().split('## Источники к параграфу 2.1')[0].strip();assert text.startswith(body21)
defs=re.findall(r'^\[\^(\d+)\]:',text,re.M);uses=re.findall(r'\[\^(\d+)\](?!:)',text)
assert len(defs)==22 and len(set(defs))==22 and set(uses)==set(defs)
assert re.findall(r'\\tag\{(2\.\d+)\}',text)==[f'2.{i}' for i in range(1,10)]
assert len(re.findall(r'^Таблица 2\.[1-4]\.',text,re.M))==4
assert len(re.findall(r'^\$\$$',text,re.M))==18
assert not any(x in text for x in ['TODO','TBD','{{S','ВСТАВИТЬ'])
check={'date':'2026-10-18','model_refit':False,'frozen_forecasts_verified':len(f),'all_numeric_tables_checked':True,'original_2_1_body_preserved':True,'reconstructed_forecasts':10,'HIST_single_omission_comparisons':dominance,'body_words':len(re.findall(r'\S+',text.split('## Источники и примечания')[0])),'formulas':9,'tables':4,'footnotes':22,'chapter_sha256':hashlib.sha256(text.encode()).hexdigest()}
(E/'verification.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(check,ensure_ascii=False,indent=2))
