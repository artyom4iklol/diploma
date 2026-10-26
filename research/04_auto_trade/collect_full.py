"""Full EU member panel. Uses cached response unless --refresh is explicit.

Absent observations stay unknown except algebraically identified zeros under
an exhaustive, exact EU27 adding-up check. Raw flags and provenance are retained.
"""
from pathlib import Path
import csv, datetime, hashlib, itertools, json, sys, urllib.parse, urllib.request
import numpy as np

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data/full_raw'; RAW.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'results/full'; OUT.mkdir(parents=True,exist_ok=True)
SPEC=json.loads((ROOT/'full_model_spec.json').read_text())
REPORTERS=SPEC['reporters']; PARTNERS=SPEC['origins']+['EXT_EU27_2020']
PRODUCTS=list(SPEC['products'].values()); INDS=SPEC['outcomes']
params=[('lang','EN'),('freq','M'),('flow','1'),('sinceTimePeriod','2021-01'),('untilTimePeriod','2025-12')]
for dim,values in [('reporter',REPORTERS+['EU27_2020']),('partner',PARTNERS),('product',PRODUCTS),('indicators',INDS)]:
    params.extend((dim,v) for v in values)
url='https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409?'+urllib.parse.urlencode(params)
path=RAW/'eurostat_full.json'; meta=RAW/'request.json'
if path.exists() and meta.exists() and '--refresh' not in sys.argv:
    record=json.loads(meta.read_text()); blob=path.read_bytes()
    assert record['source_url']==url
    assert hashlib.sha256(blob).hexdigest()==record['response_sha256']
else:
    req=urllib.request.Request(url,headers={'User-Agent':'Academic automobile trade research; reproducible Eurostat query'})
    with urllib.request.urlopen(req,timeout=55) as response:
        blob=response.read(); status=response.status
        headers={k:v for k,v in response.headers.items() if k.lower() in ['content-type','content-length','last-modified','etag','date']}
    record={'source_url':url,'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'http_status':status,'response_sha256':hashlib.sha256(blob).hexdigest(),'response_headers':headers}
    path.write_bytes(blob); meta.write_text(json.dumps(record,indent=2)+'\n')
obj=json.loads(blob)
assert obj.get('class')=='dataset',str(obj)[:2000]
ids=obj['id']; keys={}
for dim in ids:
    index=obj['dimension'][dim]['category']['index']
    keys[dim]=[k for k,v in sorted(index.items(),key=lambda x:x[1])] if isinstance(index,dict) else index
for dim,expected in [('reporter',REPORTERS+['EU27_2020']),('partner',PARTNERS),('product',PRODUCTS),('indicators',INDS)]:
    assert set(keys[dim])==set(expected),(dim,keys[dim],expected)
assert len(keys['time'])==60
def at(arr,i):
    return arr.get(str(i)) if isinstance(arr,dict) else (arr[i] if i<len(arr) else None)
values=obj.get('value',{}); flags=obj.get('status',{}); cells={}
for i,coord in enumerate(itertools.product(*(keys[d] for d in ids))):
    row=dict(zip(ids,coord)); key=tuple(row[d] for d in ['reporter','partner','product','time','indicators'])
    value=at(values,i); flag=at(flags,i)
    assert value is None or value>=0,(key,value)
    cells[key]={'raw_value':value,'value':value,'status':flag,'provenance':'observed' if value is not None else 'unknown'}

groups=[]
for partner,product,month,indicator in itertools.product(PARTNERS,PRODUCTS,keys['time'],INDS):
    group=[cells[(r,partner,product,month,indicator)] for r in REPORTERS]
    total=cells[('EU27_2020',partner,product,month,indicator)]
    missing=[i for i,c in enumerate(group) if c['raw_value'] is None]
    known=sum(c['raw_value'] for c in group if c['raw_value'] is not None)
    residual=total['raw_value']-known if total['raw_value'] is not None else None
    flagged=bool(total['status']) or any(bool(c['status']) for c in group)
    identified=bool(missing) and residual==0 and not flagged
    if identified:
        for i in missing:
            group[i]['value']=0; group[i]['provenance']='zero_from_exact_exhaustive_EU27_sum'
    groups.append({'partner':partner,'product':product,'month':month,'indicator':indicator,
                   'aggregate':total['raw_value'],'observed_members_sum':known,'raw_missing_members':len(missing),
                   'residual':residual,'any_status_flag':flagged,'zero_identified_count':len(missing) if identified else 0})

def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write_csv(OUT/'adding_up_audit.csv',groups)
panel=[]
for reporter,partner,product,month in itertools.product(REPORTERS+['EU27_2020'],PARTNERS,PRODUCTS,keys['time']):
    row={'reporter':reporter,'origin':partner,'product':product,'category':next(k for k,v in SPEC['products'].items() if v==product),'month':month}
    for indicator,name in [('SUPPLEMENTARY_QUANTITY','quantity'),('VALUE_IN_EUROS','value_eur')]:
        cell=cells[(reporter,partner,product,month,indicator)]
        row[name]=cell['value'];row[name+'_raw']=cell['raw_value'];row[name+'_status']=cell['status'];row[name+'_provenance']=cell['provenance']
    row['paired_available']=row['quantity'] is not None and row['value_eur'] is not None
    row['strictly_observed']=row['quantity_raw'] is not None and row['value_eur_raw'] is not None
    panel.append(row)
write_csv(OUT/'panel.csv',panel)
national=[r for r in panel if r['reporter']!='EU27_2020' and r['origin'] in SPEC['origins']]
coverage=[]
for year,origin,category in itertools.product(range(2021,2026),SPEC['origins'],SPEC['products']):
    rr=[r for r in national if r['month'].startswith(str(year)) and r['origin']==origin and r['category']==category]
    aa=[r for r in panel if r['reporter']=='EU27_2020' and r['month'].startswith(str(year)) and r['origin']==origin and r['category']==category]
    coverage.append({'year':year,'origin':origin,'category':category,'expected_rows':len(rr),'paired_available':sum(r['paired_available'] for r in rr),
                     'strictly_observed':sum(r['strictly_observed'] for r in rr),
                     'quantity_mass_covered':sum(r['quantity'] or 0 for r in rr if r['paired_available'])/sum(r['quantity'] for r in aa),
                     'value_mass_covered':sum(r['value_eur'] or 0 for r in rr if r['paired_available'])/sum(r['value_eur'] for r in aa)})
write_csv(OUT/'coverage.csv',coverage)
audit={'retrieval':record,'source_updated':obj.get('updated'),'dimensions':{d:len(keys[d]) for d in ids},
       'raw_indicator_cells':len(cells),'raw_observed':sum(c['raw_value'] is not None for c in cells.values()),
       'raw_zero':sum(c['raw_value']==0 for c in cells.values()),'status_counts':{},
       'national_model_grid_rows':len(national),'national_paired_available':sum(r['paired_available'] for r in national),
       'national_strictly_observed':sum(r['strictly_observed'] for r in national),
       'identified_zero_indicators':sum(c['provenance']=='zero_from_exact_exhaustive_EU27_sum' for c in cells.values()),
       'unknown_indicators':sum(c['value'] is None for c in cells.values()),
       'complete_adding_up_groups':sum(g['raw_missing_members']==0 for g in groups),
       'complete_groups_with_discrepancy':sum(g['raw_missing_members']==0 and g['residual']!=0 for g in groups),
       'groups_negative_residual':sum(g['residual'] is not None and g['residual']<0 for g in groups),
       'max_absolute_residual':max(abs(g['residual']) for g in groups if g['residual'] is not None),
       'missing_not_automatically_zero':True,'zero_reconstruction_assumption':'Same-response EU27 aggregate equals exhaustive member sum; nonnegative indicators, exact equality, all flags empty.',
       'quantity_integer_check':all(r['quantity'] is None or r['quantity']==int(r['quantity']) for r in panel),
       'duplicate_keys':len(panel)-len({tuple(r[k] for k in ['reporter','origin','product','month']) for r in panel})}
for c in cells.values():
    s=str(c['status']);audit['status_counts'][s]=audit['status_counts'].get(s,0)+1
(OUT/'data_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(audit,ensure_ascii=False),flush=True)
