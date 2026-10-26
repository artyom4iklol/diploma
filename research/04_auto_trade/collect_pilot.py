"""Small, reproducible Eurostat feasibility sample. Missing cells remain missing."""
from pathlib import Path
import urllib.request,urllib.parse,json,csv,hashlib,itertools,datetime,sys

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data/raw';RAW.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'results';OUT.mkdir(parents=True,exist_ok=True)
BASE='https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409'
PRODUCTS=['87038010','87038090','87036010','87036090','87037000','87034010','87034090','87035000']
PARTNERS=['CN','JP','KR','US','EXT_EU27_2020']
INDICATORS=['VALUE_IN_EUROS','SUPPLEMENTARY_QUANTITY']
PARAMS=[('lang','EN'),('freq','M'),('reporter','EU27_2020'),('flow','1'),('sinceTimePeriod','2021-01'),('untilTimePeriod','2025-12')]
PARAMS += [('product',p)for p in PRODUCTS]+[('partner',p)for p in PARTNERS]+[('indicators',i)for i in INDICATORS]
url=BASE+'?'+urllib.parse.urlencode(PARAMS)
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
cached=RAW/'eurostat_pilot.json';request_record=RAW/'eurostat_request.json'
if cached.exists()and request_record.exists()and '--refresh'not in sys.argv:
 old=json.loads(request_record.read_text());assert old['source_url']==url,'Cached query differs; use --refresh explicitly'
 blob=cached.read_bytes();assert hashlib.sha256(blob).hexdigest()==old['response_sha256']
 stamp=old['retrieved_at_utc'];http=old['http_status'];headers=old['response_headers']
else:
 req=urllib.request.Request(url,headers={'User-Agent':'Academic feasibility study; Eurostat monthly automobile imports'})
 try:
  with urllib.request.urlopen(req,timeout=55)as r:blob=r.read();http=r.status;headers=dict(r.headers)
 except urllib.error.HTTPError as e:
  blob=e.read();(RAW/'request_error.txt').write_bytes(blob);raise
(RAW/'eurostat_pilot.json').write_bytes(blob)
(RAW/'eurostat_request.json').write_text(json.dumps({'source_url':url,'retrieved_at_utc':stamp,'http_status':http,'response_sha256':hashlib.sha256(blob).hexdigest(),'response_headers':headers},ensure_ascii=False,indent=2))
obj=json.loads(blob)
if obj.get('class')!='dataset':raise RuntimeError(obj)
ids=obj['id'];sizes=obj['size'];labels={};keys={}
for dim in ids:
 cat=obj['dimension'][dim]['category'];index=cat['index']
 keys[dim]=[k for k,v in sorted(index.items(),key=lambda kv:kv[1])]if isinstance(index,dict)else index
 labels[dim]=cat.get('label',{})
assert set(keys['product'])==set(PRODUCTS),(keys['product'],PRODUCTS)
assert set(keys['partner'])==set(PARTNERS),(keys['partner'],PARTNERS)
assert set(keys['indicators'])==set(INDICATORS)
assert len(keys['time'])==60,keys['time']
values=obj.get('value',{});status=obj.get('status',{});rows=[]
def get(arr,i):return arr.get(str(i))if isinstance(arr,dict)else (arr[i]if i<len(arr)else None)
for index,coords in enumerate(itertools.product(*(keys[d]for d in ids))):
 row=dict(zip(ids,coords));row['value']=get(values,index);row['status']=get(status,index);rows.append(row)
with open(OUT/'pilot_panel.csv','w',newline='')as f:
 w=csv.DictWriter(f,fieldnames=ids+['value','status']);w.writeheader();w.writerows(rows)
audit={'source_url':url,'retrieved_at_utc':stamp,'http_status':http,'sha256':hashlib.sha256(blob).hexdigest(),'source_updated':obj.get('updated'),'dimensions':{k:len(v)for k,v in keys.items()},'cells_expected':len(rows),'cells_observed':sum(r['value']is not None for r in rows),'explicit_zero_cells':sum(r['value']==0 for r in rows),'missing_not_zero':True,'product_labels':labels['product'],'partner_labels':labels['partner']}
counts=[]
for partner,product,indicator in itertools.product(PARTNERS,PRODUCTS,INDICATORS):
 rr=[r for r in rows if(r['partner'],r['product'],r['indicators'])==(partner,product,indicator)]
 counts.append({'partner':partner,'product':product,'indicator':indicator,'observed_months':sum(r['value']is not None for r in rr),'missing_months':[r['time']for r in rr if r['value']is None]})
audit['coverage']=counts
(OUT/'data_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
annual=[]
for partner,product,indicator,year in itertools.product(PARTNERS,PRODUCTS,INDICATORS,['2021','2022','2023','2024','2025']):
 rr=[r for r in rows if r['partner']==partner and r['product']==product and r['indicators']==indicator and r['time'].startswith(year)]
 complete=len(rr)==12 and all(r['value']is not None for r in rr)
 annual.append({'partner':partner,'product':product,'indicator':indicator,'year':year,'observed_months':sum(r['value']is not None for r in rr),'total':sum(r['value']for r in rr)if complete else None})
with open(OUT/'annual_pilot.csv','w',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(annual[0]));w.writeheader();w.writerows(annual)
print(json.dumps({k:v for k,v in audit.items()if k not in ['coverage','product_labels','partner_labels']},ensure_ascii=False),flush=True)
print('PRODUCT LABELS',json.dumps(labels['product'],ensure_ascii=False),flush=True)
print('CHINA ANNUAL, ONLY NEW PETROL HYBRIDS AND NEW BEVS',flush=True)
for r in annual:
 if r['partner']=='CN'and r['product']in ['87038010','87036010','87034010']and r['indicator']=='SUPPLEMENTARY_QUANTITY':print(r,flush=True)
