"""Remove duplicate global headings from embedded thesis figures, pixel-exactly.

Run on the reviewed 30-figure edition. The top 110 SVG units (220 PNG pixels)
contain only global title/subtitle text. Country labels, plot panels, legends,
axes and all observations remain below this strip. Five figures already have
no global heading. Essential subtitle metadata moves to the Word caption.
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import argparse,hashlib,json
from lxml import etree as E
from PIL import Image

HERE=Path(__file__).resolve().parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
SKIP={18,20,25,28,30}
CAPTIONS={
 '1.3':'Число рынков и корреляция экспортных потоков при равных весах и индивидуальном стандартном отклонении 10 п.п.',
 '2.7':'Географическая структура экспорта внутри товарных групп в 2024 году, %',
 '3.4':'Требуемое расширение ячеек «товар — рынок», %; цветовая шкала log(1 + рост)',
 'Б.1':'Корреляции годовых темпов роста направлений экспорта: коэффициент Пирсона, 2018–2024 гг.',
 'Б.2':'Поставки от товарных групп к направлениям экспорта в 2024 году, млрд долл. США',
 'В.1':'Основные оценки и 95%-е интервалы при бутстреп-блоках 6 и 12 месяцев',
}
def sha(b):return hashlib.sha256(b).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True)
 ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,default=HERE/'diploma_full.docx')
 ap.add_argument('--png-dir',type=Path,required=True);args=ap.parse_args()
 report=json.loads(args.manifest.read_text());assert sha(args.base.read_bytes())==report['output_sha256']
 with ZipFile(args.base) as z:infos=z.infolist();parts={i.filename:z.read(i.filename) for i in infos}
 root=E.fromstring(parts['word/document.xml']);rels=E.fromstring(parts['word/_rels/document.xml.rels'])
 targets={r.get('Id'):'word/'+r.get('Target') for r in rels}
 drawings=root.findall('.//w:drawing',NS)
 flattened=[(f,im) for f in report['figures'] for im in f['images']];assert len(drawings)==len(flattened)==32
 args.png_dir.mkdir(parents=True,exist_ok=True);changed=[];cropped_media=set()
 for drawing,(figure,item) in zip(drawings,flattened):
  blip=drawing.find('.//a:blip',NS);name=targets[blip.get('{'+NS['r']+'}embed')]
  original=parts[name];assert sha(original)==item['sha256'],(item['file'],name)
  im=Image.open(BytesIO(original));w,h=im.size;cut=0 if figure['archive_number'] in SKIP else 220
  if cut:
   im=im.crop((0,cut,w,h));data=BytesIO();im.save(data,format='PNG',optimize=True)
   assert name not in cropped_media;cropped_media.add(name);parts[name]=data.getvalue()
   # Keep physical width and data resolution; reduce height by the deleted strip.
   for ex in drawing.findall('.//wp:extent',NS)+drawing.findall('.//a:xfrm/a:ext',NS):
    ex.set('cy',str(round(int(ex.get('cy'))*(h-cut)/h)))
   changed.append(figure['number'])
  (args.png_dir/item['file']).write_bytes(parts[name])
  item['previous_sha256']=item['sha256'];item['sha256']=sha(parts[name]);item['removed_top_pixels']=cut
 for p in root.findall('.//w:body/w:p',NS):
  ts=p.findall('.//w:t',NS);text=''.join(t.text or '' for t in ts)
  # Figure captions contain one plain text run in the reviewed edition.
  for label,title in CAPTIONS.items():
   if text.startswith('Рисунок '+label+' — '):
    assert len(ts)==1;ts[0].text='Рисунок '+label+' — '+title
  if text.startswith('Рисунок 2.7 показывает распределение каждой товарной группы'):
   assert len(ts)==1;ts[0].text=text.replace('в двух опорных годах','в 2024 году')
 for f in report['figures']:
  if f['number'] in CAPTIONS:f['caption']=CAPTIONS[f['number']]
 parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
 with ZipFile(args.output,'w') as z:
  for info in infos:z.writestr(info,parts[info.filename])
 report['output_sha256']=sha(args.output.read_bytes())
 report['title_removal']={'changed_figures':changed,'already_without_global_titles':['3.1','3.3','Д.2','В.2','Е.1'],
  'method':'Delete title/subtitle strip only; all remaining pixels are unchanged.',
  'preserved':'Country labels, panel descriptions, axes, units, legends, all chart data; text, tables, equations and footnotes.',
  'metadata_in_captions':list(CAPTIONS)}
 # Old page numbers remain pending a new render and update_figure_toc.py pass.
 report.pop('rendered_pages',None);report.pop('toc_pages',None)
 (HERE/'figure_insertion_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'removed_headers':len(changed),'already_clean':5,'logical_figures':30,'output_sha256':report['output_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
