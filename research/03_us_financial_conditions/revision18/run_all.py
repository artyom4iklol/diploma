"""Reproduce the final pilot and all numerical checks without network access."""
from pathlib import Path
import subprocess,sys
P=Path(__file__).resolve().parent
for name in ['build_vintages.py','fit_pilot.py','final_diagnostics.py','finish_calendar.py']:
 print('Running',name,flush=True)
 subprocess.run([sys.executable,str(P/name)],check=True,cwd=P)
print('All numerical checks passed. Results are in revision18/results/.',flush=True)
