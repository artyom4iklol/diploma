"""Additional availability probes declared after the 34-request pilot."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw_followup"
RAW.mkdir(parents=True, exist_ok=True)
TASKS = [(r, "M", 202401, cmd) for r in (392,410)
         for cmd in (854231,854233,854239,854290)]
TASKS += [(r,"A",2025,8542) for r in (392,410)]
TASKS += [(r,"M",202512,854232) for r in (392,410)]


def main():
    manifest, checks = [], []
    for reporter, frequency, period, cmd in TASKS:
        stem=f"{reporter}_X_{frequency}_{period}_{cmd}"
        p, meta_p = RAW/f"{stem}.json.gz", RAW/f"{stem}.meta.json"
        params=dict(period=period,reporterCode=reporter,cmdCode=cmd,flowCode="X",
                    partner2Code=0,customsCode="C00",motCode=0,maxRecords=500,includeDesc="true")
        url=f"https://comtradeapi.un.org/public/v1/preview/C/{frequency}/HS?"+urllib.parse.urlencode(params)
        obj=None
        if p.exists() and meta_p.exists():
            raw=gzip.decompress(p.read_bytes());meta=json.loads(meta_p.read_text())
            assert hashlib.sha256(raw).hexdigest()==meta["sha256"]
            obj=json.loads(raw)
        else:
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
                    obj=json.loads(raw)
                    if obj.get("error"):raise ValueError(obj["error"])
                    meta=dict(url=url,retrieved_at=datetime.now(timezone.utc).isoformat(),
                              sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                              reporter=reporter,frequency=frequency,period=period,cmdCode=cmd)
                    p.write_bytes(gzip.compress(raw,mtime=0));meta_p.write_text(json.dumps(meta,indent=2)+"\n")
                    time.sleep(3)
                    break
                except (urllib.error.URLError,TimeoutError,ValueError) as exc:
                    if attempt==4:
                        obj=None
                        meta=dict(url=url,reporter=reporter,frequency=frequency,period=period,cmdCode=cmd,error=str(exc))
                    else:time.sleep(min(5*2**attempt,40))
        rows=(obj or {}).get("data",[]) or []
        world=[x for x in rows if int(x["partnerCode"])==0]
        world_value=float(world[0]["primaryValue"]) if len(world)==1 else None
        ps=sum(float(x["primaryValue"]) for x in rows if int(x["partnerCode"])!=0)
        check=dict(reporter=reporter,frequency=frequency,period=period,cmdCode=cmd,
                   rows=len(rows),cap_ok=len(rows)<500,
                   status="request_failed" if obj is None else ("available" if rows else "empty"),
                   selection_ok=bool(rows) and all(int(x["period"])==period and int(x["reporterCode"])==reporter and int(x["cmdCode"])==cmd and x["flowCode"]=="X" and int(x["partner2Code"])==0 and x["customsCode"]=="C00" and str(x["motCode"])=="0" for x in rows),
                   unique_partners=len({x["partnerCode"] for x in rows})==len(rows),
                   world_usd=world_value,world_relative_gap=abs(ps-world_value)/world_value if world_value else None)
        manifest.append(meta);checks.append(check)
        (ROOT/"data"/"followup_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        print(json.dumps(check),flush=True)
    with (ROOT/"results"/"followup_availability.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(checks[0]));writer.writeheader();writer.writerows(checks)


if __name__=="__main__":main()
