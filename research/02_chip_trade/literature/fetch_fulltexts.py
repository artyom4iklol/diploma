"""Validate archived sources; optionally fetch non-archived PDFs for personal use.

No credentials, proxies, access-control bypasses or automatic retries are used.
The personal cache is ignored by Git and must not be published without permission.
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
from pathlib import Path
import urllib.error
import urllib.request


HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--personal', action='store_true',
                        help='also fetch non-archived PDFs to the ignored personal cache')
    args = parser.parse_args()
    rows = json.loads((HERE / 'sources.json').read_text())['sources']
    results = []
    for row in rows:
        target = HERE / row['repository_file'] if row['repository_file'] else None
        if target is None and not args.personal:
            continue
        if target is None:
            target = HERE / 'personal_cache' / (row['id'] + '.pdf')
        result = {'id': row['id'], 'target': str(target.relative_to(HERE))}
        try:
            if target.exists():
                body = target.read_bytes()
            else:
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                if row.get('landing_url'):
                    with opener.open(row['landing_url'], timeout=30) as landing:
                        landing.read()
                headers = {'User-Agent': 'academic-source-check/1.0', **row.get('request_headers', {})}
                req = urllib.request.Request(row['fulltext_url'], headers=headers)
                with opener.open(req, timeout=30) as response:
                    body = response.read(40_000_001)
                if len(body) > 40_000_000:
                    raise ValueError('response exceeds the 40 MB download limit')
            if not body.startswith(b'%PDF-') or b'%%EOF' not in body[-8192:]:
                raise ValueError('not a complete PDF; HTML, previews and sign-in pages are excluded')
            digest = hashlib.sha256(body).hexdigest()
            if row.get('sha256') and digest != row['sha256']:
                raise ValueError('SHA-256 changed; review the source version before accepting it')
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
            result.update(status='verified', sha256=digest, bytes=len(body))
        except (OSError, ValueError, urllib.error.URLError) as error:
            result.update(status='unavailable', error=str(error))
        results.append(result)
        print(f"{row['id']}: {result['status']}")
    if args.personal:
        cache = HERE / 'personal_cache'
        cache.mkdir(exist_ok=True)
        (cache / 'download_log.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    return int(any(r['status'] != 'verified' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
