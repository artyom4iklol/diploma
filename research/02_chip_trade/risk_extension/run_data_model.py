"""One command for collection, input validation, and numerical estimates.

The default target is the primary 2017–2024 panel. Text and manuscript creation
are deliberately separate commands. --include-2025 also collects the supplement.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--include-2025',action='store_true')
    parser.add_argument('--cache-only',action='store_true')
    parser.add_argument('--api-key-env')
    args=parser.parse_args()
    collect=[sys.executable,str(ROOT/'collect_panel.py'),'--workers','1',
             '--through','2025' if args.include_2025 else '2024','--priority-year','2024']
    if args.cache_only:collect.append('--cache-only')
    if args.api_key_env:collect.extend(['--api-key-env',args.api_key_env])
    result=subprocess.run(collect)
    if result.returncode:raise SystemExit(result.returncode)
    result=subprocess.run([sys.executable,str(ROOT/'build_monthly_panel.py')])
    if result.returncode:
        print(json.dumps(dict(model_estimated=False,reason='Input completeness/reconciliation gate failed'),ensure_ascii=False))
        raise SystemExit(3)
    result=subprocess.run([sys.executable,str(ROOT/'analyze_monthly.py')])
    if result.returncode:raise SystemExit(result.returncode)
    result=json.loads((ROOT/'results/monthly/analysis_validation.json').read_text())
    print(json.dumps(dict(model_estimated=True,primary=result['primary'],
                          causal_identification=False,manuscript_written=False),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
