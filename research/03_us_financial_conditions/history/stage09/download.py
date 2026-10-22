import json, pathlib, urllib.request, concurrent.futures, hashlib, shutil
from pypdf import PdfReader
ROOT=pathlib.Path(__file__).resolve().parent

def download(item):
 id,url,version=item
 p=ROOT/'papers'/f'{id}.pdf'
 r={'id':id,'source_url':url,'version':version,'retrieved_at':'2026-10-01'}
 try:
  if not p.exists():
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as f: b=f.read();r['resolved_url']=f.url
   if not b.startswith(b'%PDF'): raise ValueError('Response is not a PDF')
   p.write_bytes(b)
  pdf=PdfReader(p);r.update(status='downloaded',file='papers/'+p.name,pages=len(pdf.pages),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),first_page=(pdf.pages[0].extract_text() or '')[:1800])
 except Exception as e:r.update(status='unavailable',error=str(e))
 return r
if __name__=='__main__':
 import sys
 a=json.load(open(sys.argv[1]));out=list(concurrent.futures.ThreadPoolExecutor(8).map(download,a))
 (ROOT/'catalog'/(pathlib.Path(sys.argv[1]).stem+'_results.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
 for r in out: print(r['id'],r['status'],r.get('pages',r.get('error')))
