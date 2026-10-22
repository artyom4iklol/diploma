from pathlib import Path
import json,shutil,hashlib,re
R=Path(__file__).resolve().parent
old=R.parent/'gar_stage07/previous/growth_at_risk_06/02_sources/literature_registry.json'
a=json.load(open(old))
new=[
('S25','Szendrei, Tibor and Varga, Katalin','2023','Revisiting vulnerable growth in the Euro Area: Identifying the role of financial conditions in the distribution','Economics Letters','10.1016/j.econlet.2023.110990','Отбор переменных для разных частей распределения роста еврозоны; ближайшая работа для проверки новизны.'),
('S26','Plaasch, Jannick and Röthig, Andreas','2025','A Growth-at-Risk model for the German economy','Deutsche Bundesbank Technical Paper 05/2025','','Практический пример GaR для европейской экономики; институциональная рабочая публикация, не журнальная статья.'),
('S27','Amburgey, Aaron J. and McCracken, Michael W.','2023','On the real-time predictive content of financial condition indices for growth','Journal of Applied Econometrics','10.1002/jae.2943','Основная работа о пересмотрах NFCI, прогнозной проверке и сравнении вложенных квантильных моделей.'),
('S28','Arrigoni, Simone and Bobasu, Alina and Venditti, Fabrizio','2022','Measuring Financial Conditions using Equal Weights Combination','IMF Economic Review','10.1057/s41308-022-00170-y','Обоснование сравнения способов измерения финансовых условий; рабочая версия имеет другое название.'),
('S29','Adams, Patrick A. and Adrian, Tobias and Boyarchenko, Nina and Giannone, Domenico','2021','Forecasting Macroeconomic Risks','International Journal of Forecasting','10.1016/j.ijforecast.2021.01.003','Прогнозирование макроэкономических рисков с финансовыми условиями и опросными прогнозами.'),
('S30','Brandt, Lennart and Saint Guilhem, Arthur and Schröder, Maximilian and Van Robays, Ine','2026','What drives euro area financial markets? The role of US spillovers and global risk','ECB Working Paper 2560, revised March 2026','','Механизм передачи финансовых условий США в еврозону; разграничение американских и глобальных факторов. Исходная версия 2021 года.'),
('S31','Dajčman, Silvo and Kavkler, Alenka and Mikek, Peter and Romih, Dejan','2020','Transmission of Financial Stress Shocks between the USA and the Euro Area During Different Business Cycle Phases','E&M Economics and Management','10.15240/tul/001/2020-4-010','Механизм трансграничной передачи стресса и зависимость от фазы цикла; не доказательство прогнозного выигрыша нашей модели.'),
('S32','Kırcı Altınkeski, Buket and Çevik, Emrah İsmail and Diboğlu, Sel and Kutan, Ali M.','2022','Financial stress transmission between the U.S. and the Euro Area','Journal of Financial Stability','','Близкое исследование передачи стресса США–еврозона. Полный текст не получен; не использовать как изученный источник.'),
('S33','Brave, Scott and Butters, R. Andrew','2012','Diagnosing the Financial System: Financial Conditions and Financial Stress','International Journal of Central Banking','','Методология NFCI и различие финансовых условий, стресса и долговой нагрузки.'),
('S34','Brave, Scott and Butters, R. Andrew','2011','Monitoring Financial Stability: A Financial Conditions Index Approach','Economic Perspectives, Federal Reserve Bank of Chicago','','Первичное описание индексов финансовых условий; дополнение к S33, не самостоятельное подтверждение нашей гипотезы.')]
for id,author,year,title,journal,doi,rel in new:
 a.append(dict(id=id,author=author,year=year,title=title,journal=journal,doi=doi,url='https://doi.org/'+doi if doi else '',relevance=rel,priority='основная' if id in ['S25','S27','S30','S33'] else 'дополнительная'))
d={x['id']:x for x in a}
d['S14']['journal']='ECB Working Paper 2436'
d['S23']['journal']='ECB Working Paper 1426'
d['S24']['journal']='ECB Occasional Paper 396'
d['S34']['publication_note']='Заголовок карточки Chicago Fed: Monitoring Financial Stability. Заголовок PDF: Measuring financial stability: A financial conditions index approach. Это один документ.'
d['S09']['year']='2024';d['S09']['date_note']='Online 2023; journal issue 2024.'
d['S12']['publication_note']='В реестре приведена рабочая версия ECB WP 2808 (2023). Журнальная версия IMF Economic Review: online 2025, issue 2026, DOI 10.1057/s41308-024-00272-9; отдельной работой не считается.'
d['S12']['journal']='ECB Working Paper 2808';d['S12']['url']='https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2808~573fdb4019.en.pdf'
d['S02']['journal']='ECB Working Paper 2842';d['S02']['url']='https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2842~9a4cb3f225.en.pdf'
res={};attempts=[]
for f in sorted((R/'catalog').glob('*results.json')):
 for r in json.load(open(f)):
  attempts.append(r)
  if r['id'] not in res or r['status']=='downloaded':res[r['id']]=r
res['S06']['version']='IMF Working Paper 18/180; downloaded revision has five authors including Jie Yu; PDF cover retains August 2018'
res['S30']['version']='ECB Working Paper 2560 (May 2021), revised March 2026'
res['S03']['version']='Author preprint dated 8 October 2021; inherited from stage06, original download URL not retained'
res['S27']['version']='St Louis Fed Working Paper 2022-003B, June 3, 2022; journal publication 2023'
# Collect only fetched Consensus records, not search snippets.
cr=[]
for f in (R/'consensus').glob('*.json'):
 ob=json.load(open(f));v=ob.get('fetch',[]) if isinstance(ob,dict) else ob
 if isinstance(v,dict):v=[v]
 for r in v:
  r=r.get('value',r)
  for c in r.get('content',[]):
   try:
    x=json.loads(c.get('text','{}'))
    if 'id' in x and 'metadata' in x:cr.append(x)
   except (ValueError,TypeError):pass
mapping={'S01':'101dddc9d35b53c08f870ed2f1604d6c','S02':'4f6286bae4db598087140e39519234f6','S04':'d7fa9a4e6109594395af19ad0a77adf5','S05':'fc83bebaaa775271827d084786805a52','S06':'677314e0e1105e5db20366432c315be8','S07':'65b2ff1c641d506b9d9fcfc59311e199','S08':'968b667eacd05619a18fdefd2658a369','S09':'412f5872aafe591e9334e7d06fa57583','S12':'05e98ad57e3a56b8be2df5a32363e739','S13':'a07ec0abb517584b8643868a7a75ec36','S16':'b3c812afc61f54e1b2caf29f85320a82','S19':'0163920d5ed45cbe82ad1e8adc8b47c9','S25':'d8ce1c4728c45fde9ea9fcf55aba73f0','S27':'73528294e6ee5602bd09e545c95fa6cb','S28':'b1bbbac1c5b35aecaab29919a507d376','S29':'7955dbcdc4dd5841945c9a03b426530d','S30':'71fdae6111ce5850b5b25a244b05cd10','S31':'5c3184f5ff235290804f30e5bf22da93','S32':'c6b00444e5ea591295f4cb0105a3ddd2','S33':'bb279f211c3d5f758edbcf7527dc5c4e'}
byc={x['id']:x for x in cr}
for x in a:
 rr=res.get(x['id'],{'status':'unavailable','error':'No downloadable full text found'})
 x['full_text']={k:v for k,v in rr.items() if k not in ['id','first_page']}
 x['read_status']='Файл технически проверен, название/версия сверены. Скачивание не означает полного содержательного разбора.' if rr['status']=='downloaded' else 'Библиография/аннотация; полного текста в архиве нет.'
 if not x['url']:x['url']=rr.get('source_url','')
 if x['id'] in mapping:
  cc=byc.get(mapping[x['id']]);assert cc is not None,x['id'];x['consensus']=cc
  x['consensus']['retrieved_at']='2026-10-01'
 x['evidence_note']='Журнальная публикация и её рабочая версия считаются одной исследовательской работой. Выводы конкретной версии требуют проверки по приложенному тексту.'
(R/'catalog/registry.json').write_text(json.dumps(a,ensure_ascii=False,indent=2))
(R/'catalog/download_attempts.json').write_text(json.dumps(attempts,ensure_ascii=False,indent=2))
lines=['# Финансовые условия США в прогнозировании рисков роста еврозоны','', '# Каталог литературы','', 'Дата сборки: 1 октября 2026 года. Идентификаторы S01–S24 сохранены из прежнего списка. S25–S26 — работы этапа 07; S27–S34 — дополнение текущего этапа. Это целевая подборка, а не исчерпывающий систематический обзор всей литературы.','',f"Всего {len(a)} работ; полных PDF: {sum(x['full_text']['status']=='downloaded' for x in a)}; карточек, полученных через Consensus fetch: {len(mapping)}.",'','Год и журнал ниже относятся к библиографической записи; фактически приложенная версия указана отдельно. Число страниц включает обложки и приложения. Унаследованные оценки релевантности являются рабочими заметками, не результатом нового полного чтения.','']
for x in a:
 t=x['full_text'];lines += [f"## {x['id']}. {x['title']}",'',f"{x['author']}. {x['year']}. {x['journal']}.",'',f"Библиографическая ссылка: {x['url']}",f"DOI: {x.get('doi') or 'не указан/не подтверждён в этом каталоге'}",'',f"Зачем в дипломе: {x['relevance']}",'']
 if t['status']=='downloaded':lines += [f"Полный текст: [{x['id']}.pdf](../{t['file']}) — {t['pages']} стр.",f"Версия: {t['version']}",f"Источник файла: {t['source_url']}"]
 else:lines += ['**Полный текст не получен.**',f"Проверенный адрес: {t.get('source_url','')}",f"Результат получения: {t.get('error','нет файла')}. Это не доказывает отсутствие открытой версии вообще."]
 if 'consensus'in x:lines += [f"Consensus: {x['consensus']['url']} (карточка получена; библиографию сверять с первоисточником)."]
 lines += [x.get('publication_note',''),x.get('date_note',''),x['read_status'],'']
(R/'catalog/READING_CATALOG.md').write_text('\n'.join(lines))
bib=[]
for x in a:
 typ='techreport' if any(t in x['journal'] for t in ['Working Paper','Technical Paper','Occasional Paper']) else 'article'
 b=['@'+typ+'{'+x['id']+',']
 for k in ['author','title','year','journal','doi','url']:
  if x.get(k):b.append('  '+k+' = {'+str(x[k]).replace('{','').replace('}','')+'},')
 b.append('  note = {Downloaded version and access status: see registry.json}\n}')
 bib.append('\n'.join(b))
(R/'catalog/references.bib').write_text('\n\n'.join(bib))
missing=[x for x in a if x['full_text']['status']!='downloaded']
(R/'catalog/MISSING_FULL_TEXTS.md').write_text('# Полные тексты, не полученные при сборке\n\nЭто список незакрытого доступа, а не утверждение, что открытых версий не существует. Не подменять полную статью аннотацией, приложением или данными репликации. Следующий путь: университетская подписка, открытая авторская рукопись либо запрос авторам пользователем.\n\n'+'\n\n'.join(f"- **{x['id']} — {x['title']}** ({x['year']}). {x['url']}\n  Причина: {x['full_text'].get('error','нет файла')}." for x in missing))
print('REGISTRY',len(a),'PDF',len(a)-len(missing),'MISSING',[x['id'] for x in missing],'CONSENSUS',len(mapping))
