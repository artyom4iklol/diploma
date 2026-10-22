"""Validate candidate dates against the GDP publication body, never navigation text."""
from pathlib import Path
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import urllib.request, json, re, hashlib
import pandas as pd

P = Path(__file__).resolve().parent
S = P / 'sources'
dates = {
 '2009Q4':'2010-03-04','2010Q1':'2010-06-04','2010Q2':'2010-09-02',
 '2010Q3':'2010-12-02','2010Q4':'2011-03-03','2011Q1':'2011-06-08',
 '2011Q2':'2011-09-06','2011Q3':'2011-12-06','2011Q4':'2012-03-06',
 '2012Q1':'2012-06-06','2012Q2':'2012-09-06','2012Q3':'2012-12-06',
 '2012Q4':'2013-03-06','2013Q1':'2013-06-05','2013Q2':'2013-09-04',
 '2013Q3':'2013-12-04','2013Q4':'2014-03-05','2014Q1':'2014-06-06',
 '2014Q2':'2014-09-05','2014Q3':'2014-12-05','2014Q4':'2015-03-06',
 '2015Q1':'2015-06-09','2015Q2':'2015-09-08','2015Q3':'2015-12-08',
 '2015Q4':'2016-03-08','2016Q1':'2016-06-07','2016Q2':'2016-09-06',
 '2016Q3':'2016-12-06','2016Q4':'2017-03-07','2017Q1':'2017-06-08'
}
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,x):self.parts.append(x)

def verify(item):
 q, dt = item; d = pd.Timestamp(dt)
 url = 'https://ec.europa.eu/eurostat/web/products-euro-indicators/-/2-'+d.strftime('%d%m%Y')+'-ap'
 f = S / ('gdp_verified_'+q+'.html')
 # Reuse a preserved response only if it is for the identical URL date.
 old = S / ('gdp_release_'+q+'.html')
 expected = '2-'+d.strftime('%d%m%Y')+'-AP'
 try:
  if f.exists():b=f.read_bytes()
  elif old.exists() and expected.lower() in old.read_text(errors='replace').lower():b=old.read_bytes()
  else:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:b=r.read()
  t=Text();t.feed(b.decode('utf-8',errors='replace'));txt=' '.join(' '.join(t.parts).split())
  start=txt.find('Publication Details');end=txt.find('Electronic format',start)
  body=txt[start:end] if start>=0 and end>start else ''
  ordinal=['first','second','third','fourth'][int(q[-1])-1]
  phrase=ordinal+' quarter of '+q[:4]
  ok=(body.startswith('Publication Details') and 'GDP' in body[:160] and phrase in body.lower() and expected.lower() in txt.lower())
  if ok:f.write_bytes(b)
  return dict(quarter=q,candidate_date=dt,url=url,evidence=f.name if ok else '',
   status='official_GDP_release_body_verified' if ok else 'not_verified',
   body=body,sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:return dict(quarter=q,candidate_date=dt,url=url,status='not_verified',error=str(e))

if __name__=='__main__':
 rows=[]
 with ThreadPoolExecutor(max_workers=2) as ex:
  for r in ex.map(verify,dates.items()):
   rows.append(r);print(r['quarter'],r['status'],r.get('error',''),flush=True)
 (S/'gdp_verified_releases.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print('Verified',sum(r['status']=='official_GDP_release_body_verified' for r in rows),'of',len(rows),flush=True)
