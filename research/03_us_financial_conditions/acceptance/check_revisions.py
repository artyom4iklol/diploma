from pathlib import Path
import json,pandas as pd
p=Path(__file__).resolve().parent
a=pd.read_csv(p/'sources/nfci_vintage_2020.csv',index_col=0).iloc[:,0]
b=pd.read_csv(p.parent/'robustness/model/raw/fred_nfci.csv',index_col=0).NFCI
w=pd.concat([a.rename('vintage_20201231'),b.rename('project_snapshot')],axis=1).dropna()
w['difference']=w.project_snapshot-w.vintage_20201231;w.to_csv(p/'nfci_revision_comparison.csv')
s={'n':len(w),'start':w.index.min(),'end':w.index.max(),'mean_abs_revision':float(w.difference.abs().mean()),'max_abs_revision':float(w.difference.abs().max()),'correlation':float(w.iloc[:,:2].corr().iloc[0,1]),'note':'one vintage and 2019-2020 observations only; not model real-time backtest; units index points'}
(p/'nfci_revision_summary.json').write_text(json.dumps(s,indent=2))
