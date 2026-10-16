"""Collect/cache monthly exports at the documented public preview rate.

The local per-query cache is bundled into byte-preserving yearly JSONL.GZ files
for version control. Re-running restores those bundles before requesting gaps.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import httpx
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "monthly_cache"
BUNDLES = ROOT / "data" / "monthly_raw"
MANIFEST = ROOT / "data" / "monthly_manifest.json"
PROGRESS = ROOT / "data" / "collection_progress.json"
CMDS = (8542,854231,854232,854233,854239,854290)
LOG_LOCK = threading.Lock()


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def task_id(frequency, reporter, period, cmd):
    return f"{frequency}_{reporter}_{period}_{cmd}"


def atomic_json(path, obj):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


class RateLimiter:
    def __init__(self, interval=2.0):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_start = 0.0
        self.pause_until = 0.0
        self.blocked = threading.Event()

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                target = max(self.next_start, self.pause_until)
                if now >= target:
                    self.next_start = now + self.interval
                    return
                delay = target - now
            time.sleep(min(delay, 1))

    def pause(self, seconds):
        with self.lock:
            self.pause_until = max(self.pause_until, time.monotonic()+seconds)

    def completed(self):
        # Also leave a quiet interval after a response. Public preview returned
        # 429 when a new request followed a slow completed response immediately.
        with self.lock:
            self.next_start=max(self.next_start,time.monotonic()+1.2)


def restore_bundles():
    for path in sorted(BUNDLES.glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                entry = json.loads(line)
                meta, raw = entry["metadata"], entry["raw_utf8"].encode("utf-8")
                assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
                key = meta["task_id"]
                p, m = CACHE/f"{key}.json.gz", CACHE/f"{key}.meta.json"
                if not p.exists():
                    p.write_bytes(gzip.compress(raw,mtime=0))
                    atomic_json(m,meta)


def import_probes():
    for directory in (ROOT/"data"/"raw", ROOT/"data"/"raw_followup"):
        for path in sorted(directory.glob("*.meta.json")):
            old = json.loads(path.read_text())
            if old.get("flow", "X") != "X":
                continue
            frequency = old.get("frequency", "M")
            reporter, period, cmd = int(old["reporter"]), int(old["period"]), int(old["cmdCode"])
            key = task_id(frequency,reporter,period,cmd)
            dest = CACHE/f"{key}.json.gz"
            if dest.exists():
                continue
            source = path.with_name(path.name.replace(".meta.json", ".json.gz"))
            raw = gzip.decompress(source.read_bytes())
            assert hashlib.sha256(raw).hexdigest() == old["sha256"]
            meta = dict(old, frequency=frequency, flow="X", reporter=reporter,
                        period=period, cmdCode=cmd, task_id=key, imported_from=str(path.relative_to(ROOT)))
            dest.write_bytes(gzip.compress(raw,mtime=0))
            atomic_json(CACHE/f"{key}.meta.json", meta)


def validate(obj, frequency, reporter, period, cmd, allowed_reporters=None):
    all_rows = obj.get("data") or []
    allowed_reporters = allowed_reporters or [reporter]
    rows = [x for x in all_rows if int(x["reporterCode"])==reporter]
    issues = []
    if not rows:
        return dict(status="empty", rows=0, issues=["no_rows"])
    if len(all_rows)>=500:
        issues.append("row_cap_reached")
    if any(int(x["reporterCode"]) not in allowed_reporters for x in all_rows):
        issues.append("unexpected_reporter_in_response")
    partners=[]
    for x in rows:
        correct=(int(x["period"])==period and int(x["reporterCode"])==reporter
                 and int(x["cmdCode"])==cmd and x["flowCode"]=="X"
                 and int(x["partner2Code"])==0 and x["customsCode"]=="C00"
                 and int(x["motCode"])==0 and x["freqCode"]==frequency)
        if not correct:
            issues.append("selection_mismatch")
        expected="H5" if (period//100 if frequency=="M" else period)<=2021 else "H6"
        if x["classificationCode"]!=expected:
            issues.append("unexpected_hs_edition")
        if x.get("primaryValue") is None or float(x["primaryValue"])<0:
            issues.append("invalid_value")
        partners.append(int(x["partnerCode"]))
    if len(partners)!=len(set(partners)):
        issues.append("duplicate_partner")
    world=[x for x in rows if int(x["partnerCode"])==0]
    value=float(world[0]["primaryValue"]) if len(world)==1 else None
    if len(world)!=1 or value is None or value<=0:
        issues.append("missing_or_invalid_world")
    other=sum(float(x["primaryValue"] or 0) for x in rows if int(x["partnerCode"])!=0)
    gap=abs(other-value)/value if value else None
    if gap is not None and gap>1e-6:
        issues.append("world_partner_gap")
    return dict(status="ok" if not issues else "invalid",rows=len(rows),
                world_usd=value,partner_sum_usd=other,world_relative_gap=gap,
                hs_editions=sorted({x["classificationCode"] for x in rows}),
                issues=sorted(set(issues)))


def read_cached(task):
    frequency,reporter,period,cmd = task
    key=task_id(*task)
    path,meta_path=CACHE/f"{key}.json.gz",CACHE/f"{key}.meta.json"
    if path.exists() and meta_path.exists():
        raw=gzip.decompress(path.read_bytes());meta=json.loads(meta_path.read_text())
        assert hashlib.sha256(raw).hexdigest()==meta["sha256"], key
        obj=json.loads(raw)
        return dict(meta,check=validate(obj,*task,allowed_reporters=meta.get("response_reporters")),cache_hit=True)
    return None


def retrieve_group(tasks, limiter, client):
    frequency,_,period,cmd=tasks[0]
    reporters=sorted(t[1] for t in tasks)
    request_id=f"{frequency}_{'-'.join(map(str,reporters))}_{period}_{cmd}"
    params=dict(period=period,reporterCode=','.join(map(str,reporters)),cmdCode=cmd,flowCode="X",
                partner2Code=0,customsCode="C00",motCode=0,maxRecords=500,includeDesc="true")
    url=f"https://comtradeapi.un.org/public/v1/preview/C/{frequency}/HS?"+urllib.parse.urlencode(params)
    attempts=[]
    for attempt in range(7):
        if limiter.blocked.is_set():
            return [dict(task_id=task_id(*task),frequency=frequency,reporter=task[1],period=period,
                         cmdCode=cmd,flow='X',url=url,cache_hit=False,
                         check=dict(status='blocked',rows=0,issues=['collection_stopped_after_access_or_quota_error'])) for task in tasks]
        limiter.acquire()
        start=time.monotonic()
        try:
            response=client.get(url)
            limiter.completed()
            response.raise_for_status()
            raw=response.content
            obj=json.loads(raw)
            if obj.get("error"):
                raise ValueError(str(obj["error"]))
            attempts.append(dict(at=utcnow(),status=200,seconds=round(time.monotonic()-start,3)))
            with LOG_LOCK:
                with (CACHE/'request_attempts.jsonl').open('a') as log:
                    log.write(json.dumps(dict(request_id=request_id,**attempts[-1]))+'\n')
            result=[]
            for task in tasks:
                key=task_id(*task);reporter=task[1]
                meta=dict(task_id=key,frequency=frequency,reporter=reporter,period=period,
                          cmdCode=cmd,flow="X",url=url,retrieved_at=utcnow(),source_request_id=request_id,
                          response_reporters=reporters,sha256=hashlib.sha256(raw).hexdigest(),
                          bytes=len(raw),attempts=attempts,http_version=response.http_version)
                path=CACHE/f"{key}.json.gz"
                temp=path.with_suffix(".tmp");temp.write_bytes(gzip.compress(raw,mtime=0));temp.replace(path)
                atomic_json(CACHE/f"{key}.meta.json",meta)
                try:
                    check=validate(obj,*task,allowed_reporters=reporters)
                except (KeyError,ValueError,TypeError) as exc:
                    check=dict(status="invalid",rows=0,issues=["schema_error: "+str(exc)])
                result.append(dict(meta,check=check,cache_hit=False))
            return result
        except (httpx.HTTPError, TimeoutError, ValueError, OSError) as exc:
            limiter.completed()
            status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
            attempts.append(dict(at=utcnow(),status=status,error=str(exc),seconds=round(time.monotonic()-start,3)))
            delay=min(3*2**attempt,60)
            if status==429:
                header=exc.response.headers.get("Retry-After")
                if header and str(header).isdigit():delay=max(delay,int(header))
                attempts[-1]['retry_after']=header
                attempts[-1]['response_detail']=exc.response.text[:300]
                # A request's exponential wait must not starve unrelated queries.
                # The shared pause still honors the server's Retry-After.
                shared=max(3,int(header)) if header and str(header).isdigit() else 3
                limiter.pause(shared)
                time.sleep(delay)
            elif status in (400,401,403):
                attempts[-1]['response_detail']=exc.response.text[:2000]
                attempts[-1]['retry_after']=exc.response.headers.get('Retry-After')
                if status in (401,403):limiter.blocked.set()
                with LOG_LOCK:
                    with (CACHE/'request_attempts.jsonl').open('a') as log:
                        log.write(json.dumps(dict(request_id=request_id,**attempts[-1]))+'\n')
                break
            else:
                time.sleep(delay)
            with LOG_LOCK:
                with (CACHE/'request_attempts.jsonl').open('a') as log:
                    log.write(json.dumps(dict(request_id=request_id,**attempts[-1]))+'\n')
    return [dict(task_id=task_id(*task),frequency=frequency,reporter=task[1],period=period,
                 cmdCode=cmd,flow="X",url=url,attempts=attempts,cache_hit=False,
                 check=dict(status="http_error",rows=0,issues=["request_failed"])) for task in tasks]


def pack(records):
    grouped=defaultdict(list)
    for item in records:
        if "sha256" not in item:
            continue
        year=item["period"]//100 if item["frequency"]=="M" else item["period"]
        grouped[(item["frequency"],item["reporter"],year)].append(item)
    bundles=[]
    for (frequency,reporter,year),items in sorted(grouped.items()):
        lines=[]
        for item in sorted(items,key=lambda x:x["task_id"]):
            key=item["task_id"]
            meta=json.loads((CACHE/f"{key}.meta.json").read_text())
            raw=gzip.decompress((CACHE/f"{key}.json.gz").read_bytes())
            assert hashlib.sha256(raw).hexdigest()==meta["sha256"]
            lines.append(json.dumps(dict(metadata=meta,raw_utf8=raw.decode("utf-8")),ensure_ascii=False))
        payload=("\n".join(lines)+"\n").encode("utf-8")
        path=BUNDLES/f"{frequency}_{reporter}_{year}.jsonl.gz"
        temp=path.with_suffix(".tmp");temp.write_bytes(gzip.compress(payload,mtime=0));temp.replace(path)
        bundles.append(dict(path=str(path.relative_to(ROOT)),requests=len(items),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
    atomic_json(ROOT/"data"/"monthly_bundle_manifest.json",bundles)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=1)
    parser.add_argument("--through",type=int,default=2025)
    parser.add_argument("--cache-only",action="store_true")
    args=parser.parse_args()
    for p in (CACHE,BUNDLES):p.mkdir(parents=True,exist_ok=True)
    restore_bundles();import_probes()
    tasks=[("M",r,year*100+month,cmd) for year in range(2017,args.through+1)
           for month in range(1,13) for r in (392,410) for cmd in CMDS]
    if args.through>=2025:
        tasks += [("A",r,2025,cmd) for r in (392,410) for cmd in CMDS]
    limiter=RateLimiter()
    records=[];start=time.monotonic()
    expected=len(tasks)
    if args.cache_only:
        tasks=[t for t in tasks if (CACHE/f"{task_id(*t)}.json.gz").exists()]
    def save():
        ordered=sorted(records,key=lambda x:x["task_id"])
        atomic_json(MANIFEST,ordered)
        progress=dict(updated_at=utcnow(),expected_requests=expected,completed=len(records),
                      statuses=dict((status,sum(x["check"]["status"]==status for x in records))
                                    for status in ("ok","empty","invalid","http_error","blocked")),
                      cache_hits=sum(x["cache_hit"] for x in records),
                      elapsed_seconds=round(time.monotonic()-start,1),
                      complete=len(records)==expected and all(x['check']['status']=='ok' for x in records))
        atomic_json(PROGRESS,progress)
        print(json.dumps(progress),flush=True)
    missing=defaultdict(list)
    for task in tasks:
        cached=read_cached(task)
        if cached is not None:records.append(cached)
        else:missing[(task[0],task[2],task[3])].append(task)
    save()
    try:
        with httpx.Client(http2=True,timeout=45,follow_redirects=True,
                limits=httpx.Limits(max_connections=args.workers,max_keepalive_connections=args.workers,keepalive_expiry=60),
                headers={"User-Agent":"diploma-research/1.0 (public-preview; rate-limited)"}) as client:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures={pool.submit(retrieve_group,group,limiter,client):group for group in missing.values()}
                checkpoint=len(records)//20
                bundle_checkpoint=len(records)//144
                for future in concurrent.futures.as_completed(futures):
                    records.extend(future.result())
                    if len(records)//20>checkpoint:
                        save();checkpoint=len(records)//20
                    if len(records)//144>bundle_checkpoint:
                        pack(records);bundle_checkpoint=len(records)//144
    finally:
        save();pack(records)


if __name__=="__main__":
    main()
