from pathlib import Path
import urllib.request,json,concurrent.futures
P=Path('stage11/work/sources');P.mkdir(exist_ok=True)
urls={'esi_releases':'https://economy-finance.ec.europa.eu/economic-forecast-and-surveys/business-and-consumer-surveys/download-business-and-consumer-survey-data/press-releases_en','esi_archive':'https://ec.europa.eu/economy_finance/db_indicators/surveys/archive_publications/index_en.htm','nfci_about':'https://www.chicagofed.org/research/data/nfci/about','nfci_faq':'https://www.chicagofed.org/-/media/publications/nfci/nfci-faqs-pdf.pdf','gdp_revisions':'https://ec.europa.eu/eurostat/web/national-accounts/database/data-revisions','ciss_meta':'https://data.ecb.europa.eu/data/datasets/CISS/data-information'}
def get(z):
 name,u=z;r={'id':name,'url':u,'retrieved':'2026-10-02'}
 try:
  with urllib.request.urlopen(u,timeout=25) as f:b=f.read();r['final_url']=f.url;r['status']=f.status
  ext='.pdf' if b.startswith(b'%PDF') else '.html';(P/(name+ext)).write_bytes(b);r.update(bytes=len(b),file=name+ext)
 except Exception as e:r['error']=str(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:r=list(pool.map(get,urls.items()))
(P/'log.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
