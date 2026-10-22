import struct,zlib,json,pathlib
b=pathlib.Path('recovered10/thesis_us_financial_conditions_09_fulltexts.zip').read_bytes();pos=0;out=[];root=pathlib.Path('stage10/previous')
while b[pos:pos+4]==b'PK\x03\x04':
 h=struct.unpack_from('<IHHHHHIIIHH',b,pos);_,v,flags,method,tm,dt,crc,cs,us,nl,el=h
 name=b[pos+30:pos+30+nl].decode();start=pos+30+nl+el
 if start+cs>len(b):out.append({'file':name,'status':'TRUNCATED','expected':cs,'available':len(b)-start});break
 raw=b[start:start+cs];data=zlib.decompress(raw,-15) if method==8 else raw
 assert len(data)==us and zlib.crc32(data)==crc,name
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);out.append({'file':name,'status':'CRC_OK','bytes':len(data)});pos=start+cs
pathlib.Path('stage10/recovery_audit.json').write_text(json.dumps(out,indent=2));print('Recovered',len([x for x in out if x['status']=='CRC_OK']));print(out[-1]);print('PDF',len(list(root.rglob('papers/*.pdf'))))
