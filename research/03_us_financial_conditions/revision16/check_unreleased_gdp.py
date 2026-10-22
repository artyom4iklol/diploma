"""Future/current unreleased GDP cannot change a forecast at the current origin."""
from pathlib import Path
import ast,json
import numpy as np,pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,eye,hstack
P=Path(__file__).resolve().parent;R=P.parent
tree=ast.parse((R/'audit/model/compute.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'lp_functions','exec'))
d=pd.read_csv(R/'final_check/results/model_data.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q');rows=[]
for t in [pd.Period(x) for x in ['2010Q1','2018Q4','2020Q4','2024Q4']]:
 for h in [1,4]:
  for model,cols in [('BASE',['gx','ea','esi']),('US_CISS',['gx','ea','esi','us']),('US_NFCI',['gx','ea','esi','nfci'])]:
   preds=[]
   for mutate in [False,True]:
    v=d.copy()
    if mutate:v.loc[v.index>=t,'gdp_ea']*=1.7
    v['gx']=400*np.log(v.gdp_ea).diff().shift(1);v['gx2']=400*np.log(v.gdp_ea).diff().shift(2)
    v['target']=400/h*np.log(v.gdp_ea.shift(-h)/v.gdp_ea)
    tr=v.loc[(v.index+h<=t-1)&v[['target','gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)]
    preds.append(fitpred(tr,v.loc[t],cols)[0])
   diff=preds[1]-preds[0];assert abs(diff)<1e-10
   rows.append(dict(origin=str(t),h=h,model=model,difference=diff,passed=True))
(P/'results/unreleased_gdp_mutation.json').write_text(json.dumps(dict(checks=rows,n_checks=len(rows),all_passed=True,scope='Tests computation only; does not certify historical data vintages.'),indent=2))
print('Passed',len(rows),'current/future unreleased GDP mutation checks')
