"""Resolve historical BP product codes, keeping failed AP candidates separate."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib
import pandas as pd
from verify_gdp_releases import Text
P=Path(__file__).resolve().parent;S=P/'sources'
a=json.loads((S/'gdp_verified_releases.json').read_text())
def get(r):
 if r['status']=='official_GDP_release_body_verified':return r
 q=r['quarter'];dates=['2014-06-04','2014-06-06'] if q=='2014Q1' else [r['candidate_date']]
 logs=[]
 for dt in dates:
  for suffix in ['bp','ap'] if q=='2014Q1' else ['bp']:
   code='2-'+pd.Timestamp(dt).strftime('%d%m%Y')+'-'+suffix
   url='https://ec.europa.eu/eurostat/web/products-euro-indicators/-/'+code
   try:
    with urllib.request.urlopen(url,timeout=25) as res:b=res.read()
    t=Text();t.feed(b.decode(errors='replace'));txt=' '.join(' '.join(t.parts).split());st=txt.find('Publication Details');en=txt.find('Electronic format',st);body=txt[st:en] if st>=0 and en>st else ''
    phrase=['first','second','third','fourth'][int(q[-1])-1]+' quarter of '+q[:4]
    ok='GDP' in body[:160] and phrase in body.lower() and code in txt.lower()
    logs.append(dict(url=url,matched=ok,body=body))
    if ok:
     name='gdp_verified_'+q+'.html';(S/name).write_bytes(b)
     return dict(quarter=q,candidate_date=dt,url=url,evidence=name,status='official_GDP_release_body_verified',body=body,sha256=hashlib.sha256(b).hexdigest(),alternate_attempts=logs)
   except Exception as e:logs.append(dict(url=url,error=str(e)))
 r['alternate_attempts']=logs;return r
rows=[]
with ThreadPoolExecutor(max_workers=2) as ex:
 for r in ex.map(get,a):rows.append(r);print(r['quarter'],r['status'],flush=True)
(S/'gdp_verified_releases.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('Verified',sum(r['status']=='official_GDP_release_body_verified' for r in rows),'of',len(rows))
