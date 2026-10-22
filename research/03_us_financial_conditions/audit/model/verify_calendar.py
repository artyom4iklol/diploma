from pathlib import Path
import ast,json
import numpy as np,pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
P=Path(__file__).resolve().parent
mod=ast.parse((P/'compute.py').read_text());ns=globals();exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'fit_functions','exec'),ns)
es=pd.read_csv(P/'raw/esi_monthly.csv',index_col=0).iloc[:,0];es.index=pd.PeriodIndex(es.index,freq='M')
d=pd.read_csv(P/'results/model_data.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q')
f=pd.read_csv(P/'results/forecasts.csv');checks=[];features=[]
def agg(x,variant):
 if variant=='esi_first2':x=x[x.index.month%3!=0]
 if variant=='esi_drop_dec':x=x[x.index.month!=12]
 return x.groupby(x.index.asfreq('Q')).mean()
def pred(x,variant,t):
 v=d.copy();v['esi']=agg(x,variant)
 for name in ['ea','us','nfci']:v[name]=v[name+'_buffer7']
 v['target']=400*np.log(v.gdp_ea.shift(-1)/v.gdp_ea)
 train=v.loc[(v.index+1<=t-1)&v[['target','gx','ea','us','nfci','esi']].notna().all(axis=1)]
 return fitpred(train,v.loc[t],['gx','ea','esi','nfci'])[0]
for variant in ['esi_buffer7','esi_first2','esi_drop_dec']:
 a=agg(es,variant);features.extend({'variant':variant,'quarter':str(q),'esi':float(a.loc[q])} for q in d.index)
 for ts in ['2010Q4','2020Q4','2024Q4']:
  t=pd.Period(ts);x=es.copy();x.loc[f'{t.year}-12']+=1000
  p=pred(es,variant,t);changed=pred(x,variant,t)-p
  stored=f.query('variant==@variant and h==1 and model=="US_NFCI" and origin==@ts').forecast.iloc[0]
  assert abs(p-stored)<1e-7
  if variant!='esi_buffer7':assert abs(changed)<1e-10
  else:assert abs(changed)>1e-6
  checks.append({'variant':variant,'origin':ts,'forecast_change_if_unreleased_december_mutated':changed})
 # Future ESI perturbations must not alter selected origin forecast.
 t=pd.Period('2020Q4');x=es.copy();x.loc[x.index.asfreq('Q')>t]+=1000
 assert abs(pred(x,variant,t)-pred(es,variant,t))<1e-10
pd.DataFrame(features).to_csv(P/'results/esi_by_variant.csv',index=False)
json.dump({'unreleased_december_mutation_checks':checks,'future_ESI_mutation_passed':True,'limits':'Does not validate historical revisions or full historical release calendars.'},open(P/'results/calendar_validation.json','w'),indent=2)
# Check all baseline forecast values against the previous saved result if supplied.
import sys
if len(sys.argv)>1:
 old=pd.read_csv(sys.argv[1]);a=f.query('variant=="esi_buffer7"').sort_values(['h','origin','model']);b=old.query('variant=="esi_buffer7"').sort_values(['h','origin','model']);assert np.allclose(a.forecast,b.forecast,rtol=0,atol=1e-7)
print('Calendar checks passed; old calendar negative controls fail as expected.')
