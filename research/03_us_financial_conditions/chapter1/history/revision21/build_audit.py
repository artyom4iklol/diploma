from pathlib import Path
import json, re, hashlib
ROOT=Path(__file__).resolve().parent
ARC=ROOT.parent if (ROOT.parent/'catalog/registry.json').is_file() else ROOT/'archive/thesis_us_financial_conditions'
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
refs=json.loads((ROOT/'references.json').read_text())
source=(ROOT/'chapter1_revised_source.md').read_text()
sections={}
for block in re.split(r'(?=^## )',source,flags=re.M):
    if block.startswith('## '):
        title=block.splitlines()[0][3:]
        for sid in set(re.findall(r'S\d\d',block)):
            sections.setdefault(sid,[]).append(title)
checks=[]
cards=['# Проверка источников первой главы\n\n17 октября 2026 года. 44 уникальные работы; 37 PDF, один полный HTML, шесть частично доступных работ. Порядок карточек сохраняет идентификаторы общего реестра; номера в тексте главы приведены отдельно.\n\nРабочая и журнальная версии одной статьи учитываются как одна работа. Для полнотекстовых источников проверены разделы, относящиеся к использованным положениям; доказательства и расчёты независимо не воспроизводились. Текущая редакция не включает новых загрузок статей.\n']
for sid,r in refs.items():
    f=r.get('full_text',{})
    path=f.get('file')
    checksum=None
    if path:
        p=ARC/path
        assert p.is_file(),path
        checksum=hashlib.sha256(p.read_bytes()).hexdigest()
        assert checksum==f['sha256'],sid
        checks.append({'id':sid,'path':path,'sha256':checksum,'matches_registry':True})
    r['chapter1_sections']=sections[sid]
    lines=[f'## {sid}',r['chapter1_reference'],
           f"Номер в библиографии главы: {r['chapter1_citation_number']}.",
           '**Роль и границы использования.** '+r['chapter1_review_note'],
           '**Доступ.** '+r['chapter1_access_scope'],
           '**Разделы.** '+'; '.join(sections[sid])+'.',
           '**Версия.** '+r.get('consulted_version_note',f.get('version','По сведениям реестра')),
           '[Официальный источник или страница публикации]('+r['url']+').']
    if path:
        lines.append('[Сохранённый полный текст](../'+path+'). Контрольная сумма совпадает с реестром.')
    cards.append('\n\n'.join(lines))
(OUT/'SOURCE_AUDIT.md').write_text('\n\n'.join(cards)+'\n')
(OUT/'source_integrity.json').write_text(json.dumps({'date':'2026-10-17','unique_works':44,'complete_pdfs':37,'complete_html':1,'partial_access':6,'new_full_texts':0,'verified_files':checks},ensure_ascii=False,indent=2)+'\n')
(ROOT/'references.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n')
print({'audited_sources':len(refs),'verified_full_text_files':len(checks)})
