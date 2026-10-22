"""Offline ANFCI extension and notes; first reproduce revision18 if needed."""
from pathlib import Path
import subprocess,sys
P=Path(__file__).resolve().parent
for name in ['anfci_pilot.py','build_notes.py']:
 print('Running',name,flush=True)
 subprocess.run([sys.executable,str(P/name)],check=True,cwd=P)
print('ANFCI extension and numerical checks complete. See revision19/results/.')
