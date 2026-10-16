"""Limited, cached UN Comtrade monthly availability audit; no risk estimates."""
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
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
IMPORTERS = (156, 344, 490, 702, 608, 704, 458, 699)
TASKS = [(r, "X", p) for r in (392, 410)
         for p in [201701, *range(202401, 202413)]]
TASKS += [(r, "M", 202401) for r in IMPORTERS]


def retrieve(reporter: int, flow: str, period: int):
    stem = f"{reporter}_{flow}_{period}_854232"
    data_path = RAW / f"{stem}.json.gz"
    meta_path = RAW / f"{stem}.meta.json"
    if data_path.exists() and meta_path.exists():
        raw = gzip.decompress(data_path.read_bytes())
        meta = json.loads(meta_path.read_text())
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
        return json.loads(raw), meta
    params = dict(period=period, reporterCode=reporter, cmdCode="854232",
                  flowCode=flow, partner2Code=0, customsCode="C00", motCode=0,
                  maxRecords=500, includeDesc="true")
    url = "https://comtradeapi.un.org/public/v1/preview/C/M/HS?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "diploma-research-data-audit/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
            obj = json.loads(raw)
            if obj.get("error"):
                raise ValueError(str(obj["error"]))
            meta = dict(url=url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                        reporter=reporter, flow=flow, period=period, cmdCode="854232")
            data_path.write_bytes(gzip.compress(raw, mtime=0))
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
            time.sleep(3)
            return obj, meta
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if attempt == 4:
                return None, dict(url=url, reporter=reporter, flow=flow,
                                  period=period, error=str(exc))
            time.sleep(min(5 * 2 ** attempt, 40))


def check(obj, meta):
    rows = (obj or {}).get("data", []) or []
    result = {k: meta[k] for k in ("reporter", "flow", "period")}
    result.update(rows=len(rows), status="empty" if not rows else "available",
                  cap_ok=len(rows) < 500, error=meta.get("error", ""))
    if obj is None:
        result["status"] = "request_failed"
    if not rows:
        return result
    partners = [int(x["partnerCode"]) for x in rows]
    result["unique_partners"] = len(partners) == len(set(partners))
    result["selection_ok"] = all(int(x["period"]) == meta["period"]
        and int(x["reporterCode"]) == meta["reporter"] and str(x["cmdCode"]) == "854232"
        and x["flowCode"] == meta["flow"] and int(x["partner2Code"]) == 0
        and x["customsCode"] == "C00" and str(x["motCode"]) == "0" for x in rows)
    world = [x for x in rows if int(x["partnerCode"]) == 0]
    result["world_rows"] = len(world)
    result["world_usd"] = float(world[0]["primaryValue"]) if len(world) == 1 else None
    partner_sum = sum(float(x["primaryValue"]) for x in rows if int(x["partnerCode"]) != 0)
    result["partners_sum_usd"] = partner_sum
    if result["world_usd"]:
        gap = abs(partner_sum - result["world_usd"]) / result["world_usd"]
        result["world_relative_gap"] = gap
        result["reconciliation_ok"] = gap < 1e-6
    if meta["flow"] == "M":
        jp = [x for x in rows if int(x["partnerCode"]) == 392]
        kr = [x for x in rows if int(x["partnerCode"]) == 410]
        result["jp_rows"], result["kr_rows"] = len(jp), len(kr)
        if len(jp) == len(kr) == len(world) == 1:
            result["rest_of_world_usd"] = result["world_usd"] - float(jp[0]["primaryValue"]) - float(kr[0]["primaryValue"])
            result["rest_of_world_nonnegative"] = result["rest_of_world_usd"] >= 0
    return result


def main():
    audit, manifest = [], []
    for reporter, flow, period in TASKS:
        obj, meta = retrieve(reporter, flow, period)
        row = check(obj, meta)
        audit.append(row)
        manifest.append(meta)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    fields = list(dict.fromkeys(k for row in audit for k in row))
    with (RESULTS / "monthly_availability.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit)
    print(f"Saved {len(audit)} checks; no volatility/covariance estimated.", flush=True)


if __name__ == "__main__":
    main()
