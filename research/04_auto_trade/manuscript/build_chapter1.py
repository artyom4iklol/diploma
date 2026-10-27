"""Assemble the theoretical chapter and native footnotes in the approved format."""
from pathlib import Path
import sys,json,re,hashlib
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'writing'))
sys.path.insert(0,str(ROOT))
from thesis_format import new_document,add_footnote
from format_research_text import normalize_prose
from docx.enum.text import WD_ALIGN_PARAGRAPH

catalog={r['id']:r for r in json.loads((ROOT/'literature/expanded_catalog.json').read_text())}
official={r['id']:r for r in json.loads((ROOT/'literature/official_sources_catalog.json').read_text())}
def short_authors(raw,ident):
    if ident=='S21':return 'Santos Silva J. M. C., Tenreyro S.'
    more='et al.'in raw
    raw=raw.replace('et al.','').strip()
    values=raw.split(';')if ';'in raw else raw.split(',')
    out=[]
    for value in values:
        parts=value.strip().split()
        if not parts:continue
        surname=parts[-1]
        initials=[]
        for token in parts[:-1]:
            initials.append('-'.join(x[0]+'.'for x in token.strip('.').split('-')if x))
        out.append(surname+' '+' '.join(initials))
    if len(out)>4:return ', '.join(out[:3])+' et al.'
    return ', '.join(out)+(' et al.'if more else '')
def cite(ident):
    s=catalog[ident];year=s['year']
    authors=short_authors(s['authors'],ident)
    text=f"{authors.rstrip('.')}. {s['title']} // {s['venue']}."
    if str(year) not in s['venue']:text+=f' {year}.'
    if s.get('doi'):text+=' DOI '+s['doi']+'.'
    return normalize_prose(text)
notes={}
def note(key,ids,text,scope):notes[key]={'source_ids':ids,'text':text,'supported_scope':scope}

hm='Head K., Mayer T. Brands in Motion: How frictions shape multinational production. Banque de France Working Paper 629. 2017. Раздел 3, с. 14–19 (рабочая версия).'
note('HM17',['S14'],hm,'Страна бренда, сборка и сбыт, выбор моделей и источника поставок; без переноса численных параметров.')
note('IEA25PROD',['O06'],'IEA. Global EV Outlook 2025. Paris, 2025. P. 31–34.','Производство и национальность производителя — разные измерения.')
note('AFBEV',['A01'],'U.S. Department of Energy. Alternative Fuels Data Center. All-Electric Vehicles. Раздел How It Works (дата обращения: 27.10.2026).','Общее технологическое определение BEV; без заявления тождественности юридическому exCN-охвату.')
note('AFPHEV',['A02'],'U.S. Department of Energy. Alternative Fuels Data Center. Plug-In Hybrid Electric Vehicles. Разделы How It Works, Fueling and Driving Options (дата обращения: 27.10.2026).','Технология PHEV, внешняя зарядка и зависимость режима использования от зарядки.')
note('AFHEV',['A03'],'U.S. Department of Energy. Alternative Fuels Data Center. Hybrid Electric Vehicles. Разделы Regenerative Braking, Fuel-Efficient System Design (дата обращения: 27.10.2026).','HEV без внешней зарядки; различия внутри гибридного класса.')
note('SCOPE',['O05'],'European Commission. EU Commission imposes countervailing duties on imports of battery electric vehicles (BEVs) from China. Access2Markets, 12.12.2024. Описание охвата меры по Регламенту (ЕС) 2024/2754 (дата обращения: 27.10.2026).','Юридический exCN-охват, в том числе вспомогательный увеличитель запаса хода; не текущий индивидуальный расчёт пошлины.')
note('ESTATDEF',['O02'],'Eurostat. International trade in goods — detailed data. Reference metadata. Разделы 3.2–3.4 (дата обращения: 27.10.2026).','Происхождение и reporting country; CN8 и границы набора измерений.')
note('ROTTERDAM',['O03'],'Eurostat. Trade in goods. European statistics learning hub. Раздел What is the Rotterdam effect? (дата обращения: 27.10.2026).','Оформление в одной стране и конечное назначение в другой; не восстановление физического маршрута из нашей панели.')
note('IEA25TRADE',['O06'],'IEA. Global EV Outlook 2025. Paris, 2025. P. 33–35, примечания к данным международной торговли.','Различие отраслевой оценки торговли по зарубежным продажам и таможенных потоков.')
note('INCIDENCE',['S16','S17'],cite('S16')+' Целевое чтение с. 187–189. '+cite('S17')+' Для второй работы использован NBER Working Paper 26396 (2019), аннотация и введение.','Разные уровни цен и распределение нагрузки; оценки США не переносятся на ЕС.')
note('ECAS',['A04','A05'],'European Commission. Anti-subsidy measures; Anti-subsidy investigations. Trade and Economic Security. Описание инструментов и предмета расследования (дата обращения: 27.10.2026).','Правовое назначение компенсационных мер, субсидирование, ущерб, причинная связь и интересы ЕС.')
note('SUBSIDIES',['S12'],cite('S12'),'Виды промышленной поддержки и ограничения измерения; не наша оценка причин субсидий.')
note('DOU',['S02'],cite('S02')+' Принятая авторская версия, с. 5–9, 18–19.','Сценарии стоимости владения, заданные ответы производителей, база 2024H1 и приближение стоимости локализации.')
note('USITC',['S04'],cite('S04')+' Раздел методологии, с. 7–9.','Различия сценариев ограничений готовых машин и компонентов, CGE; не фактическая оценка нашей панели.')
note('IMF',['S03'],cite('S03')+' Разделы 3.1–3.2, с. 12–16.','Сценарное значение производственных и межотраслевых связей; без переноса ВВП-эффектов.')
note('BARWICKPOL',['S08'],cite('S08')+' Раздел 2, с. 6–9.','Совместная политика тарифов и субсидий как модельный нормативный результат; без универсальной оптимальной ставки.')
note('MINONDO',['S05'],cite('S05')+' С. 1275–1277, 1292–1293.','Смена разновидностей и происхождения в другом фирменном эпизоде; не подтверждение обхода в автомобилях.')
note('QUALITY',['S31'],cite('S31')+' Использована NBER-версия 2012 года, аннотация и введение.','Различие качества и unit values; собственной оценки качества нет.')
note('REALLOCATION',['S15'],cite('S15')+' Прочитана NBER-версия, пересмотренная в декабре 2023 года, аннотация и введение.','Реакция третьих стран, а не автоматически незатронутая группа.')
note('FLOODED',['S20'],cite('S20')+' Аннотация.','Неоднородность перенаправления китайских поставок в другом эпизоде; без переноса численных коэффициентов.')
shorrocks='Shorrocks A. F. Decomposition Procedures for Distributional Analysis: A Unified Framework Based on the Shapley Value. First draft, June 1999. Раздел 2, с. 4–7.'
note('DECOMPOSITION',['S23'],shorrocks,'Точное сложение и симметричное усреднение порядков; только прочитанный черновик 1999 года, не журнальная версия 2013.')
note('TIMING',['S17'],cite('S17')+' Прочитана NBER-версия 26396 (2019), введение, с. 3–4.','Закупки и запасы в американском эпизоде как пример возможного временного механизма.')
note('HMREVIEW',['S14'],hm,'Сопоставление единицы анализа и границ переноса структурного подхода.')
note('MACROREVIEW',['S03','S04'],cite('S03')+' '+cite('S04'),'Сценарные модели, без трактовки их результатов как наблюдаемых изменений нашей панели.')
note('GREENREVIEW',['S02','S13'],cite('S02')+' '+cite('S13')+' Вторая работа используется по издательской аннотации.','Типы постановок: принятие технологии, выбросы и благосостояние; без пересказа непрочитанных деталей S13.')
note('BARWICKREVIEW',['S08'],cite('S08')+' Раздел 6.2 и приложение D.1.','Существовавшие модели китайских марок, BEV/PHEV-регистрации и синтетический контроль EU6.')
note('ADAPTREVIEW',['S05','S15'],cite('S05')+' '+cite('S15'),'Сопоставление механизмов товарной и международной адаптации без присвоения фирменных выводов.')
note('VALUEREVIEW',['S31','S17'],cite('S31')+' '+cite('S17'),'Качество, средняя стоимость единицы и разные уровни цен.')
note('KE',['S01'],cite('S01')+' Аннотация; обсуждение ограничений. Бакалаврская работа.','Данные 2022–01.2026, CN против JP/KR/US, DiD, собственные оговорки автора.')
note('PERSPECTIVES',['S10','S11'],cite('S10')+' '+cite('S11')+' По доступным аннотациям и фрагментам.','Тематика и жанр экспертных обсуждений; без приписывания причинных оценок.')
note('JOULE',['S09'],cite('S09')+' Основной полный текст не получен. Проверены издательские метаданные и карточка University of Groningen (дата обращения: 27.10.2026).','Тематическая близость и существование публикации; результаты статьи не пересказываются.')
note('METHODREVIEW',['S23'],shorrocks,'Атрибуция метода; собственное применение не заявляется новой математической конструкцией.')
note('PPML',['S21'],cite('S21'),'PPML для неотрицательных потоков без логарифмирования; не гарантия причинной идентификации.')
note('MELITZ',['S32'],cite('S32')+' С. 1695–1698.','Производительность, затраты участия, фирменный отбор; собственный вывод о наблюдаемых направлениях отделяется от фирменной модели.')
note('PORTFOLIO',['S08'],cite('S08')+' Разделы 4.1–4.2, с. 12–14.','Многопродуктовые фирмы учитывают замещение собственных моделей; не оценка наших CN8-эластичностей.')
note('COMPETITION',['S14','S08'],hm+' '+cite('S08')+' Разделы 4.1–4.2.','Постоянная наценка в прочитанной версии Head/Mayer и эндогенные ценовые решения в Barwick; сопоставление предпосылок.')
note('SCENARIOS',['S02','S08'],cite('S02')+' С. 5–9, 18–19 принятой авторской версии. '+cite('S08')+' Разделы 2 и 4.','Сценарии и моделируемые решения; критика ценового приближения локализации сформулирована как собственная методическая интерпретация.')
# Give the full reference at first mention; retain clear short references thereafter.
short_hm='Head K., Mayer T. Brands in Motion. Banque de France WP 629. 2017.'
short_barwick='Barwick P. J. et al. From Trade War to Green Transition. NBER WP 35334. 2026.'
short_dou='Dou H. et al. Distributional impacts of EU tariffs on Chinese electric vehicles across European markets. 2026.'
short_shorrocks='Shorrocks A. F. Decomposition Procedures for Distributional Analysis. First draft, 1999.'
cavallo_wp='Cavallo A., Gopinath G., Neiman B., Tang J. Tariff Pass-Through at the Border and at the Store: Evidence from US Trade Policy. NBER Working Paper 26396. 2019.'
feenstra_wp='Feenstra R. C., Romalis J. International Prices and Endogenous Quality. NBER Working Paper 18314. 2012.'
fajgelbaum_wp='Fajgelbaum P., Goldberg P., Kennedy P. et al. The US-China Trade War and Global Reallocations. NBER Working Paper 29562. Revised December 2023.'
notes['PORTFOLIO']['text']=cite('S08')+' Разделы 4.1–4.2.'
notes['INCIDENCE']['text']=cite('S16')+' С. 187–189. '+cavallo_wp+' Аннотация и введение.'
notes['BARWICKPOL']['text']=short_barwick+' Раздел 2.'
notes['QUALITY']['text']=feenstra_wp+' Аннотация и введение.'
notes['REALLOCATION']['text']=fajgelbaum_wp+' Введение.'
notes['TIMING']['text']='Cavallo A. et al. Tariff Pass-Through at the Border and at the Store. NBER WP 26396. 2019. С. 3–4.'
notes['HMREVIEW']['text']=short_hm+' Раздел 3. '+cite('S32')+' С. 1695–1698.'
notes['HMREVIEW']['source_ids']=['S14','S32']
notes['COMPETITION']['text']=short_hm+' Раздел 3. '+short_barwick+' Разделы 4.1–4.2.'
notes['SCENARIOS']['text']=short_dou+' Принятая авторская версия, с. 5–9, 18–19. '+short_barwick+' Разделы 2 и 4.'
notes['MACROREVIEW']['text']='Wingender P. et al. Europe’s Shift to EVs Amid Intensifying Global Competition. IMF WP 24/218. 2024. С. 12–16. Coffin D. et al. The Impact of Changes in Trade Policies on the Electric Vehicle Sector. USITC 2024–05–A. С. 7–9.'
notes['ADAPTREVIEW']['text']='Minondo A. How exporters neutralised an increase in tariffs. 2024. С. 1275–1277. Fajgelbaum P. et al. The US-China Trade War and Global Reallocations. NBER WP 29562. Редакция декабря 2023.'
notes['BARWICKREVIEW']['text']=short_barwick+' Раздел 6.2 и приложение D.1.'
notes['METHODREVIEW']['text']=short_shorrocks+' Раздел 2.'
for entry in notes.values():entry['text']=normalize_prose(entry['text'])

aux=[
 {'id':'A01','institution':'U.S. Department of Energy','title':'All-Electric Vehicles','url':'https://afdc.energy.gov/vehicles/electric-basics-ev'},
 {'id':'A02','institution':'U.S. Department of Energy','title':'Plug-In Hybrid Electric Vehicles','url':'https://afdc.energy.gov/vehicles/electric-basics-phev'},
 {'id':'A03','institution':'U.S. Department of Energy','title':'Hybrid Electric Vehicles','url':'https://afdc.energy.gov/vehicles/electric-basics-hev'},
 {'id':'A04','institution':'European Commission','title':'Anti-subsidy measures','url':'https://policy.trade.ec.europa.eu/enforcement-and-protection/trade-defence/anti-subsidy-measures_en'},
 {'id':'A05','institution':'European Commission','title':'Anti-subsidy investigations','url':'https://policy.trade.ec.europa.eu/enforcement-and-protection/trade-defence/anti-subsidy-measures/anti-subsidy-investigations_en'}]
paths=[HERE/f'chapter1_{n}.md'for n in range(1,5)]+[HERE/'chapter1_conclusions.md']
title='Глава 1 Теоретические основы товарной и географической адаптации автомобильной торговли'
body='# '+title+'\n\n'+'\n\n'.join(p.read_text().strip()for p in paths)+'\n'
used=re.findall(r'\[\^([^]]+)\]',body)
assert len(used)==len(set(used)), 'Use a distinct footnote token for each reference.'
assert set(used)<=set(notes), sorted(set(used)-set(notes))
notes={key:notes[key] for key in used}
all_ids=set(catalog)|set(official)|{x['id']for x in aux}
assert all(set(x['source_ids'])<=all_ids for x in notes.values())
definitions='\n'+'\n\n'.join('[^'+key+']: '+notes[key]['text']for key in used)+'\n'
(HERE/'chapter1_content.md').write_text(body+definitions)
ids=sorted({ident for x in notes.values()for ident in x['source_ids']})
records=[]
for ident in ids:
    if ident in catalog:records.append(deepcopy(catalog[ident]))
    elif ident in official:records.append(deepcopy(official[ident]))
    else:records.append(next(deepcopy(x)for x in aux if x['id']==ident))
register={'date':'2026-10-27','citations':notes,'records':records,'working_auxiliary_ids':'A01–A05 are additional official sources actually used in this chapter, not part of the 26 October preparation snapshot.',
 'Head_Mayer_read_version':{'version':'Banque de France WP629, May 2017','journal_version':'2019 metadata checked; full journal text not read','reviewed':'PDF pages 1–7 and 16–21; introduction and model section 3 (printed pages 14–19)','url':'https://publications.banque-france.fr/sites/default/files/medias/documents/dt629_0.pdf','sha256':'4a1cc39c8e10a23e18265df2543fe612c0aea681087a7a6a9916152c96250da8'},
 'revision':'2026-10-27 substantive revision 2',
 'read_versions':{'S14':{'cited':'Banque de France WP629, 2017','journal_full_text_read':False},'S23':{'cited':'first draft, June 1999, section 2','journal_2013_full_text_read':False},'S32':{'cited':'Econometrica 2003, pp. 1695–1698','selected_sections_only':True}},
 'not_claimed':['causal_tariff_effect','priority_over_Joule','full_reading_of_all_works','new_PPML_or_decomposition_method']}
register['read_versions'].update({'S15':{'cited':'NBER WP29562, revised December 2023'},'S17':{'cited':'NBER WP26396, 2019'},'S31':{'cited':'NBER WP18314, 2012'}})
(HERE/'chapter1_sources.json').write_text(json.dumps(register,ensure_ascii=False,indent=2)+'\n')
bib=['# Источники, использованные в первой главе','', 'Рабочие ID сохраняются для последующей общей библиографии; версии и глубина чтения — в chapter1_sources.json.','']
for x in records:
    if x['id']=='S14':text=hm
    elif x['id']=='S23':text=shorrocks
    elif x['id']=='S17':text=cavallo_wp
    elif x['id']=='S31':text=feenstra_wp
    elif x['id']=='S15':text=fajgelbaum_wp
    elif x['id']in catalog:text=cite(x['id'])
    else:text=x['institution']+'. '+x['title']+'. '+x['url']+' (дата обращения: 27.10.2026).'
    bib.append('- '+x['id']+'. '+text)
bib+=['','Для S14, S15, S17, S23 и S31 выше приведены фактически использованные рабочие версии; связанные журнальные записи сохраняются в общем каталоге. Наличие PDF не означает прочтения всего текста.']
(HERE/'chapter1_bibliography.md').write_text('\n'.join(bib)+'\n')

d=new_document();d.core_properties.title='Теоретические основы товарной и географической адаптации автомобильной торговли'
for value in body.strip().split('\n\n'):
    if value.startswith('# '):
        p=d.add_paragraph(value[2:],style='Title');p.alignment=WD_ALIGN_PARAGRAPH.LEFT
    elif value.startswith('## '):d.add_paragraph(value[3:],style='Thesis Section')
    else:
        p=d.add_paragraph()
        chunks=re.split(r'(\[\^[^]]+\])',value)
        for chunk in chunks:
            m=re.fullmatch(r'\[\^([^]]+)\]',chunk)
            if m:add_footnote(d,p,notes[m.group(1)]['text'])
            else:p.add_run(chunk.replace('\n',' '))
path=ROOT/'documents/chapter1_auto_trade.docx';d.save(path)
summary={'date':'2026-10-27','chapter':'theoretical','sections':4,'conclusions':True,'body_words':len(re.sub(r'\[\^[^]]+\]','',body).split()),'native_footnotes':len(used),'unique_sources':len(records),'source_ids':ids,'figures':0,'tables':0,'docx_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'revision':'substantive_revision_2','visual_review':'pending','path':str(path.relative_to(ROOT.parents[1]))}
(HERE/'chapter1_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
