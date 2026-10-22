"""Extract documented ESI/GDP blocks, retaining each vintage's definition.

Select by block heading and validate key/description. Renamed SDMX keys are
retained rather than treating a key change as a missing economic variable.
"""
from pathlib import Path
from datetime import datetime
import csv,io,re,json,zipfile
import pandas as pd
P=Path(__file__).resolve().parent;O=P/'extracted';O.mkdir(exist_ok=True)
summary=[]
for kind,fn in [('esi','rtd_monthly_pre2015.zip'),('gdp','rtd_quarterly_pre2015.zip')]:
 rows_out=[];coverage=[]
 with zipfile.ZipFile(P/fn) as z:
  assert z.testzip() is None
  for name in sorted(z.namelist()):
   rows=list(csv.reader(io.StringIO(z.read(name).decode('utf-8-sig',errors='replace'))))
   headings=rows[0];keys=rows[1];descs=rows[2]
   blocks=[i for i,h in enumerate(headings) if ('Confidence indicators:' in h if kind=='esi' else h.startswith('GDP: by expenditure components at constant prices'))]
   assert len(blocks)==1,(name,blocks)
   j=blocks[0];key=keys[j];description=descs[j] if j<len(descs) else ''
   assert ('ECOSEN' in key or '.ESI000.' in key) if kind=='esi' else ('B1QG00' in key or '.B1GQ.' in key),(name,key)
   local=[]
   for row in rows[9:]:
    if len(row)<=j:continue
    try:value=float(row[j].strip().replace('D','E'))
    except ValueError:continue
    token=row[0].strip()
    if kind=='esi':
     d=None
     for fmt in ['%b-%Y','%b-%y']:
      try:d=datetime.strptime(token,fmt);break
      except ValueError:pass
     if d is None:continue
     period=f'{d.year}-{d.month:02d}'
    else:
     m=re.fullmatch(r'Q([1-4])-(\d{4})',token)
     if not m:continue
     period=m[2]+'Q'+m[1]
    local.append(dict(vintage_month=re.search(r'_(\d{6})',name)[1],period=period,source_key=key,value=value))
   rows_out.extend(local);coverage.append(dict(vintage_file=name,vintage_month=re.search(r'_(\d{6})',name)[1],rows=len(local),source_key=key,description=description,first=local[0]['period'] if local else None,last=local[-1]['period'] if local else None))
 pd.DataFrame(rows_out).to_csv(O/f'{kind}_legacy_vintages.csv',index=False);pd.DataFrame(coverage).to_csv(O/f'{kind}_legacy_coverage.csv',index=False)
 summary.append(dict(series=kind,vintages=len(coverage),nonempty_vintages=sum(x['rows']>0 for x in coverage),records=len(rows_out),earliest_vintage=coverage[0]['vintage_month'],latest_vintage=coverage[-1]['vintage_month'],geography='policy concept of the euro area in each vintage; NOT fixed EA20',public_release_day_verified=False))
(P/'legacy_validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
