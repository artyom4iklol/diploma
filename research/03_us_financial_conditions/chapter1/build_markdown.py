"""Build the reviewed chapter and source checks; no network or model estimation."""
from pathlib import Path
import re, json, hashlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
refs = json.loads((ROOT / 'references.json').read_text())
refs['S05']['chapter1_reference'] = re.sub(r'Souza A\. B\.(?: M\.)*', 'Souza A. B. M.', refs['S05']['chapter1_reference'])
versions = {
 'S01': 'NY Fed Staff Report No. 794, редакция ноября 2017 года',
 'S03': 'авторская рукопись от 8 октября 2021 года',
 'S04': 'авторская рукопись от 2 июля 2020 года',
 'S06': 'IMF Working Paper No. 18/180; сохранённая редакция с пятью авторами, включая Jie Yu',
 'S08': 'ECB Working Paper No. 2458, 2020',
 'S13': 'CAMA Working Paper No. 97/2020',
 'S15': 'Cleveland Fed Working Paper No. 21-02R',
 'S16': 'arXiv:2508.00263v3, 13 марта 2026 года',
 'S17': 'Cleveland Fed Working Paper No. 22-12, май 2022 года',
 'S18': 'Kiel Working Paper No. 1844, 2013, под названием International Transmission of Financial Stress: Evidence from a GVAR',
 'S27': 'St. Louis Fed Working Paper No. 2022-003B, 3 июня 2022 года',
 'S28': 'ECB Working Paper No. 2451, 2020, под названием The Simpler the Better: Measuring Financial Conditions for Monetary Policy and Financial Stability',
 'S29': 'NY Fed Staff Report No. 914, 2020',
 'S35': 'NBER Working Paper No. 21722, редакция марта 2019 года',
 'S39': 'рабочая версия апреля 2003 года',
}
source = (ROOT / 'chapter1_revised_source.md').read_text()
order = []
def cite(match):
    items = [x.split('|',1) for x in match.group(1).split(';')]
    ids = [x[0] for x in items]
    for sid in ids:
        assert sid in refs, sid
        if sid not in order:
            order.append(sid)
    return '[' + '; '.join(str(order.index(x[0])+1)+((', '+x[1]) if len(x)>1 else '') for x in items) + ']'

body = re.sub(r'\{\{([^{}]+)\}\}', cite, source)
assert '{{' not in body and set(order) == set(refs)
bib = []
for number, sid in enumerate(order, 1):
    r = refs[sid]
    r.update(review_stage='chapter1_revision22', review_date='2026-10-17',
             review_card='chapter1/SOURCE_AUDIT.md#'+sid.lower(),
             chapter1_citation_number=number)
    if sid in versions:
        r['consulted_version_note'] = 'Использованная полнотекстовая версия: '+versions[sid]+'.'
    partial = r.get('full_text',{}).get('status') not in ('downloaded','html_saved')
    r['chapter1_access_scope'] = ('Официальная аннотация и доступные фрагменты; полный текст не получен.' if partial else 'Полный текст доступен; для содержательных утверждений проверены относящиеся к ним разделы. Независимая репликация статьи не выполнялась.')
    text = r['chapter1_reference']
    doi = r.get('doi')
    # Use the official publication URL for institutional papers where registry DOIs may denote SSRN records.
    if doi and doi in text:
        text = text.replace('DOI: '+doi+'.', '[DOI: '+doi+'](https://doi.org/'+doi+').')
    else:
        text += ' [Источник]('+r['url']+').'
    if sid in versions:
        text += ' '+r['consulted_version_note']
    bib.append(str(number)+'. '+text)

final = body.rstrip()+'\n\n## Список использованных источников к главе 1\n\n'+'\n\n'.join(bib)+'\n'
(OUT / 'Chapter_1_US_Financial_Conditions_Euro_Area.md').write_text(final)
(ROOT / 'references.json').write_text(json.dumps(refs, ensure_ascii=False, indent=2)+'\n')
metrics = dict(revision=22,date='2026-10-17',body_words=len(body.split()),body_characters=len(body),
               citation_groups=len(re.findall(r'\{\{[^}]+\}\}',source)),unique_sources=len(order),
               equations=source.count('\\tag{'),figures=0,tables=0,
               source_order=order,sha256=hashlib.sha256(final.encode()).hexdigest(),
               scope='Содержательная редакция главы; эмпирические результаты не пересчитывались.')
(OUT / 'chapter_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:v for k,v in metrics.items() if k!='source_order'},ensure_ascii=False,indent=2))
