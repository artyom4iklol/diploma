"""Download and cache UN Comtrade annual trade records without an API key.

Each request is split into small HS-code batches. Raw successful responses
and hashes are retained. Existing files are reused unless --refresh is passed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import pathlib
import time
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text())
RAW = ROOT / "data" / "raw"
REQUEST_LOCK = threading.Lock()
LAST_REQUEST = 0.0
REQUEST_PAUSE = 2.5


def throttle():
    global LAST_REQUEST
    with REQUEST_LOCK:
        delay = REQUEST_PAUSE - (time.monotonic() - LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        LAST_REQUEST = time.monotonic()


def download_one(reporter: str, year: int, codes: list[str], refresh: bool):
    stem = f"{reporter}_{year}_{'-'.join(codes)}"
    raw_path = RAW / f"{stem}.json"
    compressed_path = raw_path.with_suffix(".json.gz")
    meta_path = RAW / f"{stem}.meta.json"
    if (raw_path.exists() or compressed_path.exists()) and meta_path.exists() and not refresh:
        body = raw_path.read_bytes() if raw_path.exists() else gzip.decompress(compressed_path.read_bytes())
        obj = json.loads(body)
        meta = json.loads(meta_path.read_text())
        if hashlib.sha256(body).hexdigest() != meta["sha256"]:
            raise ValueError(f"Cached source hash mismatch: {stem}")
        print(f"cache {stem}: {len(obj.get('data', []))} rows", flush=True)
        return meta
    params = {
        "period": str(year), "reporterCode": reporter,
        "cmdCode": ",".join(codes), "flowCode": "X", "partner2Code": "0",
        "customsCode": "C00", "motCode": "0", "maxRecords": "500", "includeDesc": "true",
    }
    url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS?" + urllib.parse.urlencode(params, safe=",")
    last_error = None
    for attempt in range(4):
        try:
            throttle()
            request = urllib.request.Request(url, headers={"User-Agent": "diploma-research-pilot/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            obj = json.loads(body)
            if not isinstance(obj.get("data"), list):
                raise ValueError(f"No data array: {str(obj)[:160]}")
            if not obj["data"]:
                raise ValueError("Empty response; availability has not been confirmed")
            if len(obj["data"]) >= 500:
                if len(codes) == 1:
                    raise ValueError("Preview limit reached for a single product; incomplete data")
                midpoint = len(codes) // 2
                return [download_one(reporter, year, codes[:midpoint], refresh),
                        download_one(reporter, year, codes[midpoint:], refresh)]
            if obj.get("count") is not None and obj["count"] != len(obj["data"]):
                raise ValueError("Count and response length disagree")
            raw_path.write_bytes(body)
            compressed_path.write_bytes(gzip.compress(body, mtime=0))
            meta = {"url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                    "records": len(obj["data"]), "reporter": reporter, "year": year,
                    "requested_codes": codes, "raw_file": raw_path.name}
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
            print(f"download {stem}: {meta['records']} rows", flush=True)
            return meta
        except Exception as exc:
            last_error = exc
            print(f"retry {attempt+1}/4 {stem}: {type(exc).__name__}: {exc}", flush=True)
            if attempt < 3:
                time.sleep(min(5 * 2**attempt, 20))
    raise RuntimeError(f"Failed {stem}: {last_error}")


def flatten(values):
    for value in values:
        if isinstance(value, list):
            yield from flatten(value)
        else:
            yield value


def main():
    global REQUEST_PAUSE
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--pause", type=float, default=2.5,
                        help="Minimum seconds between public API requests")
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args()
    REQUEST_PAUSE = max(1.0, args.pause)
    RAW.mkdir(parents=True, exist_ok=True)
    years = args.years or CONFIG["years"]
    tasks = [(r, y, batch, args.refresh) for r in CONFIG["reporters"]
             for y in years for batch in CONFIG["download_batches"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 3))) as pool:
        results = list(pool.map(lambda x: download_one(*x), tasks))
    manifest = list(flatten(results))
    name = "sources_manifest.json" if years == CONFIG["years"] else "pilot_sources_manifest.json"
    (RAW.parent / name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Complete: {len(manifest)} source files, {sum(x['records'] for x in manifest)} records", flush=True)


if __name__ == "__main__":
    main()
