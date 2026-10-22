from pathlib import Path
import pandas as pd,json
P=Path(__file__).resolve().parent;O=P/'results'
a=pd.read_csv(O/'forecast_calendar_59.csv')
old=pd.read_csv(P.parent/'revision16/results/forecast_calendar_all_origins.csv')
old=old[['origin','growth_observed_quarter','gdp_actual_regular_release','gdp_release_evidence','gdp_release_url','esi_months','esi_release_dates','esi_release_evidence']]
a=a.drop(columns=[x for x in old.columns if x!='origin' and x in a.columns])
a=a.merge(old,on='origin',how='left',validate='one_to_one')
assert len(a)==59 and a.gdp_actual_regular_release.notna().all()
assert (pd.to_datetime(a.gdp_actual_regular_release)<=pd.to_datetime(a.forecast_date)).all()
a.to_csv(O/'forecast_calendar_59.csv',index=False)
e=pd.read_csv(P.parent/'revision16/results/esi_monthly_release_audit.csv');e=e[e.origin.isin(a.origin)].copy()
e=e.drop(columns=['forecast_deadline','available_by_deadline','exact_vintage_used','geography_used'])
e=e.merge(a[['origin','forecast_date']],on='origin',validate='many_to_one')
e['available_by_forecast']=(pd.to_datetime(e.release_date)<=pd.to_datetime(e.forecast_date))
e['version_source']='RTD + published bulletin repair, retained known history; see forecast_calendar_59.csv'
assert len(e)==118 and e.available_by_forecast.all();e.to_csv(O/'ESI_monthly_actual_dates_118.csv',index=False)
p=O/'final_validation.json';j=json.loads(p.read_text());j['GDP_lag_actual_release_dates_verified']=59;j['ESI_actual_monthly_release_dates_verified']=118;p.write_text(json.dumps(j,indent=2));print('59 GDP regular release dates and 118 actual ESI releases verified before forecasts')
