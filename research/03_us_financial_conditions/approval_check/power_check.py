from pathlib import Path
import json
import numpy as np
from scipy.stats import binomtest,binom
r=[]
for n in [16,63]:
 k=np.arange(n+1);reject=np.array([binomtest(int(x),n,.1).pvalue<=.05 for x in k])
 r.append({'n':n,'expected_hits_under_null':n*.1,'reject_counts':k[reject].tolist(),'size':float(binom.pmf(k,n,.1)[reject].sum()),'power':{str(p):float(binom.pmf(k,n,p)[reject].sum()) for p in [.15,.20,.25]},'assumptions':'Independent Bernoulli hits; illustrative exact calculation, not actual power of estimated models.'})
Path(__file__).with_name('power_check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
