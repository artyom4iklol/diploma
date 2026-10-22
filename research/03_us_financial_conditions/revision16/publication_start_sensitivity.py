"""Score frozen forecasts after publication milestones. No historical-vintage claim."""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent
f=pd.read_csv(P.parent/'final_check/results/forecasts.csv');rows=[]
for label,start in [('after_NFCI_launch','2011Q2'),('after_daily_CISS_documented_not_real_time','2020Q2')]:
 for h in [1,4]:
  g=f[(f.variant=='expanding_lag1')&(f.h==h)&(f.origin>=start)]
  means=g.groupby('model').loss.mean()
  for m,v in means.items():rows.append(dict(period=label,start=start,h=h,model=m,n=int((g.model==m).sum()),loss=v,ratio_BASE=v/means.BASE,ratio_HIST=v/means.HIST))
pd.DataFrame(rows).to_csv(P/'results/publication_start_sensitivity.csv',index=False)
print('Saved publication start sensitivity; not a real-time correction.')
