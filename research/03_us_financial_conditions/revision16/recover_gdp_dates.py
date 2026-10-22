from pathlib import Path
import urllib.request,concurrent.futures,json,re,html,datetime,time
from html.parser import HTMLParser
import pandas as pd
P=Path(__file__).resolve().parent;S=P/'sources';O=P/'results'
a=pd.read_csv(O/'forecast_calendar_all_origins.csv',keep_default_na=False);qs=a.loc[a.gdp_actual_regular_release.eq(''),'growth_observed_quarter'].tolist()
class Text(HTMLParser):
 def __init__(self):super().__init__();self.x=[]
 def handle_data(self,x):self.x.append(x)
def fetch(q):
 end=pd.Period(q,freq='Q').end_time.normalize();ord=['first','second','third','fourth'][pd.Period(q,freq='Q').quarter-1];phrase=f'{ord} quarter of {q[:4]}';logs=[]
 for offset in [0,-1,1,-2,2,-3,3,-4,4,5,6,-5,-6]:
  dt=end+pd.Timedelta(days=65+offset)
  if dt.weekday()>=5:continue
  url='https://ec.europa.eu/eurostat/web/products-euro-indicators/-/2-'+dt.strftime('%d%m%Y')+'-ap'
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=5) as r:b=r.read()
   t=Text();t.feed(b.decode('utf-8',errors='replace'));text=' '.join(' '.join(t.x).split());low=text.lower()
   # Exact quarter and GDP release product code required; generic error pages fail.
   code='2-'+dt.strftime('%d%m%Y')+'-AP';ok=phrase in low and 'gdp' in low and code.lower() in low
   logs.append(dict(url=url,matched=ok))
   if ok:
    name='gdp_release_'+q+'.html';(S/name).write_bytes(b)
    return dict(quarter=q,date=str(dt.date()),url=url,evidence=name,status='official_quarter_matched_release',snippet=text[max(0,low.find(phrase)-180):low.find(phrase)+450],attempts=logs)
  except Exception as e:logs.append(dict(url=url,error=str(e)))
 return dict(quarter=q,status='not_found',attempts=logs)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 rs=[]
 for r in ex.map(fetch,qs):rs.append(r);print(r['quarter'],r['status'],r.get('date',''),flush=True)
(S/'gdp_recovered_dates.json').write_text(json.dumps(rs,indent=2));print('matched',sum(r['status']!='not_found' for r in rs),'of',len(rs))
