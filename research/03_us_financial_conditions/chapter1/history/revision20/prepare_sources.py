from pathlib import Path
import json,re,hashlib,html

ROOT=Path('/workspace/scratch/3c2847f1995e/chapter1_work')
ARC=ROOT/'archive/thesis_us_financial_conditions'
REG=ARC/'catalog/registry.json'
registry=json.loads(REG.read_text())
cross={x['id']:x for x in json.loads((ROOT/'bibliography_crossref.json').read_text())}
downloads=json.loads((ROOT/'new_downloads.json').read_text())
success={x['id']:x for x in downloads if x['status']=='downloaded'}

new=[
 {'id':'S41','author':'Brave, Scott A. and Kelley, David','year':'2017','title':'Introducing the Chicago Fed’s New Adjusted National Financial Conditions Index','journal':'Chicago Fed Letter 386','doi':'','url':'https://www.chicagofed.org/publications/chicago-fed-letter/2017/386','priority':'основная','relevance':'Определение и обновление ANFCI, различия с NFCI. Полный PDF уже находился в revision19; в текущем дополнении включён в общий реестр.'},
 {'id':'S42','author':'Hatzius, Jan and Hooper, Peter and Mishkin, Frederic S. and Schoenholtz, Kermit L. and Watson, Mark W.','year':'2010','title':'Financial Conditions Indexes: A Fresh Look after the Financial Crisis','journal':'NBER Working Paper 16150','doi':'10.3386/w16150','url':'https://www.nber.org/papers/w16150','priority':'основная','relevance':'Определение финансовых условий и различие между собственно финансовой и общей макроэкономической информацией.'},
 {'id':'S43','author':'Bernanke, Ben S. and Gertler, Mark and Gilchrist, Simon','year':'1998','title':'The Financial Accelerator in a Quantitative Business Cycle Framework','journal':'NBER Working Paper 6455','doi':'10.3386/w6455','url':'https://www.nber.org/papers/w6455','priority':'основная','relevance':'Теоретический механизм усиления колебаний через баланс заёмщика и премию за внешнее финансирование.'},
 {'id':'S44','author':'Bletzinger, Tilman and Martorana, Giulia and Mistak, Jakub','year':'2026','title':'Looser, Tighter, Clearer: A New Financial Conditions Index for the Euro Area','journal':'ECB Working Paper 3193','doi':'10.2866/8467971','url':'https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3193~9db57822d4.en.pdf','priority':'дополнительная','relevance':'Современный подход к измерению FCI с совместной оценкой макрофинансовой VAR; контекст выбора индекса, а не замена нашей модели.'},
]
registry=[x for x in registry if x['id'] not in {z['id'] for z in new}]+new
for x in registry:
 sid=x['id']
 if sid=='S41':
  data=(ARC/'papers/S41.pdf').read_bytes()
  x['full_text']={'status':'downloaded','file':'papers/S41.pdf','version':'Chicago Fed Letter 386, 2017; same PDF already in revision19/sources/ANFCI_method2017.pdf','source_url':x['url'],'sha256':hashlib.sha256(data).hexdigest(),'retrieved_at':'2026-10-16'}
 elif sid in success:
  d=success[sid]
  x['full_text']={'status':'downloaded','file':d['file'],'source_url':d['url'],'resolved_url':d['resolved_url'],'sha256':d['sha256'],'pages':d['pages'],'retrieved_at':'2026-10-16','version':x.get('journal','')}
 x['review_stage']='chapter1_2026-10-16'
 x['review_card']='chapter1/SOURCE_REVIEW.md#'+sid.lower()
 x['review_date']='2026-10-16'
 x['read_status']='Проверены полный текст в доступной версии, постановка и релевантные разделы; математические доказательства и расчёты независимо не воспроизводились' if x.get('full_text',{}).get('file') else 'Проверены библиография, официальная аннотация и доступные фрагменты; полный текст не получен'

notes={
'S01':'Базовая связь финансовых условий с нижними квантилями роста США. Из неё не следует автоматическая переносимость на еврозону.',
'S02':'Дневной CISS и учёт системности стресса. Структурные симуляции авторов не приписываются нашей одноуравневой модели.',
'S03':'Международная информация и нелинейная квантильная факторная модель; описаны возможности расширения, без заявления о её реализации.',
'S04':'Слабая и неточная дополнительная предсказуемость хвостов после учёта реальных индикаторов; аргумент за вневыборочные ориентиры.',
'S05':'По официальной аннотации: проверка 24 стран ОЭСР, квантильные регрессии не имеют безусловного преимущества перед GARCH. Подробности тестов не пересказываются.',
'S06':'Различия краткосрочных и более отдалённых рисков; наша проверка до четырёх кварталов не объявляется анализом трёхлетнего накопления уязвимостей.',
'S07':'Определение и прикладное использование GaR; важны ограничения неструктурной интерпретации.',
'S08':'Прямой предшественник по агрегату еврозоны. Выбор индикатора существенен; применение GaR к еврозоне уже известно.',
'S09':'По официальной аннотации: методы для устойчивых предикторов сохраняют основные результаты и могут улучшать нижние прогнозы. Полная оценка доказательств не заявлена.',
'S10':'По официальной аннотации: корреляция ошибок и дополнительные лаги меняют оценку текущей финансовой переменной; совместная значимость с лагами сохраняется.',
'S11':'Условное покрытие, конкурирующие модели и ограничения коротких квартальных рядов. В главе не утверждается, что тест авторов реализован в нашем эксперименте.',
'S12':'Различение стресса и уязвимости и их горизонтов. Основной разбор по ECB WP2808 2023; более поздняя журнальная версия не считается отдельной работой.',
'S13':'MIDAS-квантильные регрессии и оперативное обновление GaR еврозоны. Содержание высокочастотной постановки отделено от нашей квартальной.',
'S14':'Реальное время и оценка тяжести кризиса; различаются предупреждение до события и измерение риска после его начала.',
'S15':'Сильное влияние экстремальных наблюдений в BVAR; метод авторов не объявляется реализованным в квантильной модели.',
'S16':'Крайние хвосты и изменяющийся хвостовой показатель. Проверены введение, ограничения подходов и раздел 7 Summary and Discussions.',
'S17':'Форма полной плотности зависит от способа восстановления по квантилям. Один квантиль не превращается в полную плотность.',
'S18':'Быстрая международная передача финансового стресса и запаздывающий эффект на активность; изучена доступная рабочая версия.',
'S19':'По официальной аннотации и введению издателя: международные последствия стресса в глобальной VAR. Численные эффекты и результаты конкретных тестов не заимствуются.',
'S20':'Классическое определение квантильной регрессии. Основной текст сканирован; 18 страниц статьи распознаны OCR, определения сверены с содержанием.',
'S21':'Согласование критерия качества с объектом прогнозирования, в том числе квантилем. Аксиоматические доказательства не воспроизводились.',
'S22':'По аннотации авторов/издателя: взвешенные правила оценки позволяют выделять интересующие части распределения. Не используется как доказательство реализации нового теста.',
'S23':'Портфельное агрегирование CISS и системный характер стресса; важное различие с широким FCI.',
'S24':'ЕЦБ Macro-at-Risk: широкий круг факторов и зависимость информативности от горизонта, периода и цели. Используется версия 2026 года.',
'S25':'Отбор финансовых переменных, регуляризация и непересечение квантилей в небольшой выборке еврозоны.',
'S26':'Прямой предшественник с NFCI в модели Германии. Вклад нашей работы сформулирован без приоритета применения американского индекса в Европе.',
'S27':'Исторические версии NFCI, пересмотры и вложенное сравнение. Исторические версии не объявляются неизбежно худшими, а специальные тесты авторов не подменяются обычным DM.',
'S28':'Способ агрегирования не гарантирует качества; простые комбинации могут конкурировать со сложными индексами. Рабочая и журнальная версии названы отдельно.',
'S29':'Риски вокруг центрального прогноза и дополнительная информация финансовых условий.',
'S30':'Внутренние, американские и глобальные факторы европейских цен активов. Использована редакция марта 2026 года, исходная серия WP2560 2021.',
'S31':'Режимная передача стресса между США и еврозоной; вывод о зависимости от фазы цикла.',
'S32':'По официальной аннотации и введению: недельные данные 2000–2021, односторонняя центральная и двусторонняя хвостовая зависимость.',
'S33':'Риск, кредит и финансовый рычаг содержат разную информацию о стрессе и уязвимостях; связь с задачей выбора горизонта.',
'S34':'Широкий охват финансовой системы, индексы и их интерпретация. Двухколоночный текст проверен по введению и заключению.',
'S35':'Глобальный финансовый цикл и международная передача американской политики. Причинная идентификация статьи не переносится на коэффициент NFCI.',
'S36':'Инвестиционные фонды, международные портфельные потоки и финансирование фирм еврозоны; использована редакция декабря 2022.',
'S37':'Совместная динамика стресса при возможном расхождении широких финансовых условий США и еврозоны.',
'S38':'Цикл банковского рычага, валовые потоки капитала и глобальная ликвидность. Проверены аннотация, введение и выводы BIS WP458.',
'S39':'Сравнивается прогнозная процедура, а не одна формула. Условия применимости не объявляются автоматически выполненными.',
'S40':'Полный PDF ранее отсутствовал; получен по актуальной ссылке IMF. Проверены факторная конструкция, публикационные лаги, свойства версий и прогнозная мотивация.',
'S41':'Определение ANFCI и изменение 2017 года; учитываются макрокорректировки и различия весов, без интерпретации как чистого структурного шока.',
'S42':'Финансовые условия включают цены, количества и обследования; проверены определение и обзор механизмов.',
'S43':'Финансовый акселератор, внешний финансовый премиум и баланс заёмщика. PDF сканирован; проверены аннотация и введение с OCR.',
'S44':'Совместное оценивание FCI и макрофинансовой VAR; новый контекст измерения. Не включается задним числом в наш прогнозный набор.',
}

def initials(s):
 return ' '.join(z[0]+'.' for z in s.replace('-',' ').split() if z)

def authors(x):
 c=cross.get(x['id'],{})
 if c.get('author'):
  return ', '.join(a['family']+' '+initials(a['given']) for a in c['author'])
 parts=[]
 for v in x['author'].split(' and '):
  a=v.split(',',1)
  parts.append(a[0].strip()+' '+initials(a[1]) if len(a)>1 else a[0])
 return ', '.join(parts)

special={
'S02':'Chavleishvili S., Kremer M. Measuring Systemic Financial Stress and Its Risks for Growth. ECB Working Paper No. 2842. 2023.',
'S04':'Plagborg-Møller M., Reichlin L., Ricco G., Hasenzagl T. When Is Growth at Risk? Brookings Papers on Economic Activity. 2020. Spring. P. 167–229. DOI: 10.1353/eca.2020.0002.',
'S06':'Adrian T., Grinberg F., Liang N., Malik S., Yu J. The Term Structure of Growth-at-Risk. American Economic Journal: Macroeconomics. 2022. Vol. 14, No. 3. P. 283–323. DOI: 10.1257/mac.20180428.',
'S07':'Prasad A., Elekdag S., Jeasakul P., Lafarguette R., Alter A., Feng A. X., Wang C. Growth at Risk: Concept and Application in IMF Country Surveillance. IMF Working Paper No. 19/36. 2019. DOI: 10.5089/9781484397015.001.',
'S11':'Corradi V., Fosten J., Gutknecht D. Out-of-Sample Tests for Conditional Quantile Coverage an Application to Growth-at-Risk. Journal of Econometrics. 2023. Vol. 236, No. 2. Article 105490. DOI: 10.1016/j.jeconom.2023.105490.',
'S12':'Lang J. H., Rusnák M., Greiwe M. Medium-Term Growth-at-Risk in the Euro Area. ECB Working Paper No. 2808. 2023.',
'S14':'De Santis R. A., Van der Veken W. Forecasting Macroeconomic Risk in Real Time: Great and Covid-19 Recessions. ECB Working Paper No. 2436. 2020.',
'S16':'Adrian T., Sasaki Y., Wang Y. Robust Econometrics for Growth-at-Risk. Journal of Econometrics. 2026. Vol. 255. Article 106235. DOI: 10.1016/j.jeconom.2026.106235.',
'S20':'Koenker R., Bassett G. Regression Quantiles. Econometrica. 1978. Vol. 46, No. 1. P. 33–50. DOI: 10.2307/1913643.',
'S23':'Holló D., Kremer M., Lo Duca M. CISS — A Composite Indicator of Systemic Stress in the Financial System. ECB Working Paper No. 1426. 2012.',
'S24':'Expert Group on Macro-at-Risk, Time-Series Workstream; Chahad M., Mogliani M. (eds.). Macro-at-Risk in the Euro Area. ECB Occasional Paper No. 396. 2026. DOI: 10.2866/6868685.',
'S26':'Plaasch J., Röthig A. A Growth-at-Risk Model for the German Economy. Deutsche Bundesbank Technical Paper No. 05/2025. 2025.',
'S30':'Brandt L., Saint Guilhem A., Schröder M., Van Robays I. What Drives Euro Area Financial Markets? The Role of US Spillovers and Global Risk. ECB Working Paper No. 2560. 2021. Revised March 2026.',
'S31':'Dajčman S., Kavkler A., Mikek P., Romih D. Transmission of Financial Stress Shocks between the USA and the Euro Area During Different Business Cycle Phases. E&M Economics and Management. 2020. Vol. 23, No. 4. P. 152–165. DOI: 10.15240/tul/001/2020-4-010.',
'S33':'Brave S., Butters R. A. Diagnosing the Financial System: Financial Conditions and Financial Stress. International Journal of Central Banking. 2012. Vol. 8, No. 2. P. 191–239.',
'S34':'Brave S., Butters R. A. Monitoring Financial Stability: A Financial Conditions Index Approach. Economic Perspectives, Federal Reserve Bank of Chicago. 2011. Vol. 35, No. 1. P. 22–43.',
'S35':'Miranda-Agrippino S., Rey H. U.S. Monetary Policy and the Global Financial Cycle. Review of Economic Studies. 2020. Vol. 87, No. 6. P. 2754–2776. DOI: 10.1093/restud/rdaa019.',
'S36':'Kaufmann C. Investment Funds, Monetary Policy, and the Global Financial Cycle. ECB Working Paper No. 2489. 2020. Revised December 2022.',
'S37':'Habib M. M., Venditti F. The Global Financial Cycle: Implications for the Global Economy and the Euro Area. ECB Economic Bulletin. 2018. Issue 6.',
'S38':'Bruno V., Shin H. S. Cross-Border Banking and Global Liquidity. BIS Working Paper No. 458. 2014. Журнальная версия: Review of Economic Studies. 2015. Vol. 82, No. 2. P. 535–564.',
'S39':'Giacomini R., White H. Tests of Conditional Predictive Ability. Econometrica. 2006. Vol. 74, No. 6. P. 1545–1578. DOI: 10.1111/j.1468-0262.2006.00718.x.',
'S40':'Matheson T. D. Financial Conditions Indexes for the United States and Euro Area. IMF Working Paper No. 11/93. 2011. DOI: 10.5089/9781455253326.001.',
'S41':'Brave S. A., Kelley D. Introducing the Chicago Fed’s New Adjusted National Financial Conditions Index. Chicago Fed Letter. 2017. No. 386.',
'S42':'Hatzius J., Hooper P., Mishkin F. S., Schoenholtz K. L., Watson M. W. Financial Conditions Indexes: A Fresh Look after the Financial Crisis. NBER Working Paper No. 16150. 2010. DOI: 10.3386/w16150.',
'S43':'Bernanke B. S., Gertler M., Gilchrist S. The Financial Accelerator in a Quantitative Business Cycle Framework. NBER Working Paper No. 6455. 1998. DOI: 10.3386/w6455.',
'S44':'Bletzinger T., Martorana G., Mistak J. Looser, Tighter, Clearer: A New Financial Conditions Index for the Euro Area. ECB Working Paper No. 3193. 2026. DOI: 10.2866/8467971.',
}
for x in registry:
 sid=x['id'];c=cross.get(sid,{})
 if sid in special:ref=special[sid]
 else:
  year=x['year']
  if c.get('published-print'):year=str(c['published-print']['date-parts'][0][0])
  title=html.unescape((c.get('title') or [x['title']])[0])
  journal=html.unescape((c.get('journal') or [x.get('journal','')])[0])
  ref=f'{authors(x)} {title}. {journal}. {year}.'
  if c.get('volume'):ref+=' Vol. '+str(c['volume'])+'.'
  if c.get('issue'):ref+=' No. '+str(c['issue'])+'.'
  if c.get('article-number'):ref+=' Article '+str(c['article-number'])+'.'
  elif c.get('page'):ref+=' P. '+str(c['page']).replace('-','–')+'.'
  if x.get('doi'):ref+=' DOI: '+x['doi']+'.'
 x['chapter1_reference']=ref
 x['chapter1_review_note']=notes[sid]

REG.write_text(json.dumps(registry,ensure_ascii=False,indent=2))
out=ARC/'chapter1';out.mkdir(exist_ok=True)
(ROOT/'references.json').write_text(json.dumps({x['id']:x for x in registry},ensure_ascii=False,indent=2))
(out/'NEW_SOURCES_DOWNLOADS.json').write_text(json.dumps(downloads,ensure_ascii=False,indent=2))
(out/'BIBLIOGRAPHY_METADATA.json').write_text(json.dumps(list(cross.values()),ensure_ascii=False,indent=2))
lines=['# Разбор источников для первой главы','',
'Дата проверки 16 октября 2026 года. Исходный реестр из 40 уникальных работ рассмотрен целиком. Дополнительно в реестр включены методика ANFCI (полный текст уже имелся в revision19) и три новые работы. Восстановлен ранее отсутствовавший PDF Matheson. Рабочая и журнальная версии одной работы не считаются отдельными исследованиями.','',
'Уровень проверки: библиография, аннотации, постановки, выводы и релевантные разделы доступных полных текстов. Математические доказательства и численные результаты независимо не воспроизводились. Само наличие полного PDF не называется постраничной независимой верификацией статьи.','',
'Источники дополнительного поиска: Consensus, Undermind и официальные сайты авторов/издателей, ECB, IMF, NBER и Chicago Fed. Scite вернул ограничение подписки, поэтому результаты от него в этом проходе не использованы.','']
for x in registry:
 full=x.get('full_text',{});path=full.get('file')
 access='Полный PDF' if path and path.endswith('.pdf') else 'Полный HTML' if path else 'Аннотация и доступные фрагменты, полный текст отсутствует'
 lines.extend([f'## {x["id"]} {x["title"]}','',x['chapter1_reference'],'','Доступ: '+access+'.','',notes[x['id']],'','Место в первой главе: '+('1.1' if x['id'] in ['S23','S28','S33','S34','S40','S41','S42','S44'] else '1.2' if x['id'] in ['S18','S19','S30','S31','S32','S35','S36','S37','S38','S43'] else '1.3')+'.','',f'Источник: {x.get("url","")}',''])
 if path:lines.extend(['Файл в архиве: '+path+'.',''])
(out/'SOURCE_REVIEW.md').write_text('\n'.join(lines))
print(json.dumps({'registry':len(registry),'full_pdf':sum(bool(x.get('full_text',{}).get('file','').endswith('.pdf')) for x in registry),'full_html':sum(bool(x.get('full_text',{}).get('file','').endswith('.html')) for x in registry),'partial':[x['id'] for x in registry if not x.get('full_text',{}).get('file')]},ensure_ascii=False))
