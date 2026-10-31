"""One command, frozen sources and method; existing dissertation files are read-only."""
from pathlib import Path
import subprocess,sys,os,argparse,json,hashlib
from cache_files import hydrate
P=Path(__file__).resolve().parent

def main():
 a=argparse.ArgumentParser();a.add_argument('--offline',action='store_true',help='Use cached raw data; never contact data providers');a.add_argument('--reuse-models',action='store_true',help='Reuse saved estimates; still re-evaluate and validate');args=a.parse_args()
 hydrate()
 if (P/'protocol_lock.json').exists():
  from run_models import load_spec
  for name,expected in load_spec()['input_sha256'].items():
   if hashlib.sha256((P.parent/name).read_bytes()).hexdigest()!=expected:raise ValueError('Frozen input changed: '+name)
 if args.reuse_models:
  saved=json.loads((P/'checks/model_run.json').read_text())
  for name,expected in saved['files'].items():
   if hashlib.sha256((P/'results'/name).read_bytes()).hexdigest()!=expected:raise ValueError('Saved model output changed: '+name)
  for name,expected in saved.get('implementation',{}).items():
   if hashlib.sha256((P/name).read_bytes()).hexdigest()!=expected:raise ValueError('Model implementation changed; refit required: '+name)
 commands=[]
 if not args.offline:commands+=['collect_sources.py']
 commands+=['lock_protocol.py','build_panel.py']
 if not args.reuse_models:commands+=['run_models.py']
 commands+=['evaluate.py','validate.py','influence_audit.py','report_results.py']
 env=os.environ.copy();env.update({'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
 for name in commands:subprocess.run([sys.executable,str(P/name)],cwd=P,env=env,check=True)

if __name__=='__main__':main()
