from pathlib import Path
import struct,zlib,json,hashlib,shutil
source=Path('supervisor_sources/thesis_us_financial_conditions_14_acceptance.zip');b=source.read_bytes();out=Path('recovery15/recovered');out.mkdir(exist_ok=True);pos=0;log=[]
while True:
 pos=b.find(b'PK\x03\x04',pos)
 if pos<0:break
 try:
  v,fl,me,tm,dt,crc,cs,us,nl,el=struct.unpack_from('<5H3I2H',b,pos+4);name=b[pos+30:pos+30+nl].decode();start=pos+30+nl+el
  assert not fl&8 and me in [0,8] and not Path(name).is_absolute() and '..' not in Path(name).parts
  data=zlib.decompress(b[start:start+cs],-15) if me==8 else b[start:start+cs];ok=len(data)==us and zlib.crc32(data)==crc
  if ok and not name.endswith('/'):
   f=out/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  log.append(dict(name=name,ok=ok));pos=start+cs
 except Exception as e:log.append(dict(offset=pos,error=str(e)));pos+=4
p=out/'thesis_us_financial_conditions';m=json.loads((p/'MANIFEST_SHA256.json').read_text());byname={}
for f in Path('.').rglob('*'):
 if f.is_file() and 'recovery15' not in f.parts:byname.setdefault(f.name,[]).append(f)
for name,h in m.items():
 if (p/name).exists():continue
 for f in byname.get(Path(name).name,[]):
  if hashlib.sha256(f.read_bytes()).hexdigest()==h:
   dest=p/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);break
q=p/'final_check';q.mkdir(exist_ok=True)
(q/'RECOVERY_LOG.json').write_text(json.dumps(log,indent=2));shutil.copy2(p/'MANIFEST_SHA256.json',q/'ORIGINAL_MANIFEST_SHA256.json');shutil.copy2(__file__,q/'recover_from_workspace.py')
st=[dict(file=k,sha256=h,status='original_verified' if (p/k).exists() and hashlib.sha256((p/k).read_bytes()).hexdigest()==h else 'not_recovered') for k,h in m.items()];(q/'RECOVERY_INVENTORY.json').write_text(json.dumps(st,indent=2));print('RECOVERED',sum(x['status']=='original_verified' for x in st),'MISSING',sum(x['status']=='not_recovered' for x in st))
