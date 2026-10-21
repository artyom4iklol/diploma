"""Refresh the plain thesis TOC using the actual PDF pagination; verify after render."""
from pathlib import Path
import argparse,json,re,hashlib
import fitz
from docx import Document

def norm(s):return re.sub(r'\s+',' ',s).strip()

def main():
 p=argparse.ArgumentParser();p.add_argument('docx',type=Path);p.add_argument('pdf',type=Path)
 p.add_argument('--check',action='store_true');a=p.parse_args();d=Document(a.docx);pdf=fitz.open(a.pdf)
 texts=[norm(page.get_text()) for page in pdf];mapping={};mismatches=[]
 blocks=[[norm(b[4]) for b in page.get_text('blocks')] for page in pdf]
 for para in d.paragraphs[1:27]:
  heading,old=para.text.rsplit('\t',1)
  candidates=[i+1 for i,bb in enumerate(blocks) if i>0 and norm(heading) in bb]
  if not candidates and heading.startswith('Глава '):
   candidates=[i+1 for i,t in enumerate(texts) if i>0 and norm(heading) in t]
  assert candidates,heading
  page=candidates[0];mapping[heading]=page
  if old!=str(page):mismatches.append((heading,old,page))
  if not a.check:
   # These are plain single-run static TOC entries, no fields/hyperlinks.
   assert len(para.runs)==1
   para.runs[0].text=heading+'\t'+str(page)
 if a.check:assert not mismatches,mismatches
 else:
  d.save(a.docx)
  m=a.docx.with_name('figure_insertion_manifest.json')
  report=json.loads(m.read_text());report['output_sha256']=hashlib.sha256(a.docx.read_bytes()).hexdigest()
  report['rendered_pages']=len(pdf);report['toc_pages']=mapping
  m.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'pages':len(pdf),'toc_entries':len(mapping),'changed_entries':len(mismatches),'check':a.check},ensure_ascii=False))

if __name__=='__main__':main()
