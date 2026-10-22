"""Coverage audit, not forecast estimation or certification of public availability."""
from pathlib import Path
import json
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent
manifest=json.loads((P/'rtd_chunk_manifest.json').read_text())
assert len(manifest)==62 and all(x['status']=='verified_history_response' for x in manifest)
summary={};events={}
for kind in ['gdp','esi']:
 a=pd.concat([pd.read_csv(P/x['file']) for x in manifest if x['series']==kind],ignore_index=True)
 # Replace events use VALID_FROM; Delete events have their timestamp in VALID_TO.
 action=a.ACTION.eq('Delete');stamp=a.VALID_FROM.where(~action,a.VALID_TO)
 a['event_time']=pd.to_datetime(stamp,utc=True,errors='coerce');a['delete']=action
 assert a.event_time.notna().all()
 a['rank']=np.where(a.delete,0,1)
 a['value']=pd.to_numeric(a.OBS_VALUE,errors='coerce').where(~action,np.nan)
 events[kind]=a.sort_values(['event_time','rank'])
 summary[kind]=dict(rows=len(a),observation_periods=int(a.TIME_PERIOD.nunique()),event_timestamps=int(a.event_time.nunique()),first_event=str(a.event_time.min()),last_event=str(a.event_time.max()),delete_events=int(action.sum()))
rows=[]
for q in pd.period_range('2011Q2','2025Q4',freq='Q'):
 cutoff=q.end_time.tz_localize('Europe/Brussels').tz_convert('UTC')
 snapshots={}
 for kind,a in events.items():
  x=a[a.event_time<=cutoff].drop_duplicates('TIME_PERIOD',keep='last').set_index('TIME_PERIOD').value.dropna()
  snapshots[kind]=x
 g=snapshots['gdp'];gi=pd.Series(g.to_numpy(),index=pd.PeriodIndex(g.index.str.replace('-Q','Q'),freq='Q')).sort_index()
 e=snapshots['esi'];ei=pd.Series(e.to_numpy(),index=pd.PeriodIndex(e.index,freq='M')).sort_index()
 target_months=[str(pd.Period(q.start_time,freq='M')),str(pd.Period(q.start_time,freq='M')+1)]
 g_lag=all(str(x).replace('Q','-Q') in g.index for x in [q-1,q-2])
 rows.append(dict(origin=str(q),gdp_lag1_inputs_present=g_lag,esi_first_two_months_present=all(x in e.index for x in target_months),gdp_history_quarters=len(gi),esi_history_months=len(ei),positive_gdp=bool(gi.gt(0).all()),publication_timestamp_certified=False,geography='historical policy concept, not fixed EA20'))
pd.DataFrame(rows).to_csv(P/'coverage_59_origins.csv',index=False)
summary['origins']=len(rows);summary['gdp_lag_inputs_present']=sum(x['gdp_lag1_inputs_present'] for x in rows);summary['esi_first_two_months_present']=sum(x['esi_first_two_months_present'] for x in rows)
summary['public_release_timestamps_certified']=False
summary['scope']='Source and coverage audit only; VALID_FROM is a frozen RTD snapshot/event time and is not automatically the public publication time. No new forecast model has been fitted.'
(P/'coverage_validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
