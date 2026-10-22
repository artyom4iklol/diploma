import urllib.request,json,concurrent.futures
from pathlib import Path
r=json.load(open('stage10/previous/thesis_us_financial_conditions_09/catalog/registry.json'))
jobs=[(x['id'],x['full_text']['source_url']) for x in r if x['full_text']['status']=='unavailable']
jobs += [('S22','https://citeseerx.ist.psu.edu/document?doi=07b14f69099d1fdab8f09ff4e4155f379a5fcd8d&repid=rep1&type=pdf')]
def get(z):
 id,u=z;v={'id':id,'url':u,'date':'2026-10-02'}
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as f:b=f.read();v.update(http=f.status,bytes=len(b),resolved_url=f.url)
  if b.startswith(b'%PDF'):
   Path('stage10/'+id+'_retry.pdf').write_bytes(b);v['result']='PDF obtained'
  else:v['result']='Response is not PDF'
 except Exception as e:v['result']=str(e)
 return v
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex: out=list(ex.map(get,jobs))
Path('stage10/access_retry.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
