"""Annotated, access-aware bibliography; does not claim every PDF was read."""
from pathlib import Path
import csv, json
from format_research_text import normalize_prose

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'literature'
old=json.loads((OUT/'source_manifest.json').read_text())
oldnotes=[
 ('thesis','1.4;2.5','Месячные BEV-потоки ЕС; DiD, Китай против JP/KR/US.','Ближайший аналог первоначальной модели; страны сравнения и BEV сами по себе вкладом не являются.','Полный текст получен; проверены постановка, данные, метод и ограничения.'),
 ('journal_article','1.2;1.4;3.3','Стоимость владения и сценарии электрификации по 20 странам и 10 классам.','Сценарные прогнозы отличаются от наблюдаемых пограничных потоков; это не доказательство эффективности мер в нашей панели.','Принятая версия получена; целевое чтение методов и границ.'),
 ('working_paper','1.2;3.3','Макроэкономические и торговые сценарии перехода Европы к EV.','Опора для обсуждения политики; собственная модель не оценивает ВВП, занятость или благосостояние.','Полный текст получен; целевое чтение.'),
 ('working_paper','1.2;3.3','CGE-сценарии ограничений на EV, гибриды и комплектующие.','Нельзя переносить их калиброванные эффекты в качестве результатов нашей PPML.','Полный текст получен; целевое чтение.'),
 ('journal_article','1.3;2.2','Адаптация экспортёров к тарифам через изменение состава и происхождения поставок.','Механизм переключения давно известен; вклад нашего случая должен быть количественным и конкретным.','Полный авторский текст получен; целевое чтение.'),
 ('thesis','1.4','Реакции инвесторов и акций на торговые события.','Смежный материал; не основа вывода о таможенных потоках.','Полный текст получен; целевой просмотр, вспомогательный приоритет.'),
 ('working_paper','1.1','Сети глобальных EV-цепочек и критических материалов.','Год версии не подтверждён; не включать в окончательный список без уточнения. Номер26 не является годом.','Полный текст получен; год не установлен, вспомогательная запись.'),
 ('working_paper','1.2;1.4;3.3','Структурная модель спроса; дополнительно синтетический контроль BEV/PHEV-регистраций существовавших моделей в EU6.','Добавление PHEV само по себе уже не ново; пограничное происхождение, новые модели и география оформления — другой измерительный объект.','Полный PDF получен; проверены модель, европейский раздел6.2 и приложениеD.1.')]
records=[]
for i,(o,notes) in enumerate(zip(old,oldnotes),1):
    typ,sections,method,limit,depth=notes
    records.append({'id':f'S{i:02d}','authors':o['authors'],'year':o['year'],'title':o['title'],'venue':o['venue'],'type':typ,'doi':o['doi'] or ('10.3386/w35334' if i==8 else None),'primary_url':o['primary_full_text_url'],'sections':sections,'data_method':method,'use_and_limit':limit,'review_status':depth,'local_filename':o['local_filename'],'sha256':o['sha256'],'priority':'background' if i in [6,7] else 'core'})

def add(authors,year,title,venue,typ,doi,url,sections,method,limit,status,file=None):
    records.append({'id':f'S{len(records)+1:02d}','authors':authors,'year':year,'title':title,'venue':venue,'type':typ,'doi':doi,'primary_url':url,'sections':sections,'data_method':method,'use_and_limit':limit,'review_status':status,'local_filename':file,'priority':'core'})
add('Hao Dou; Han Hao; Lang Mai; Boyu Liu; Ming Liu; Xin Sun',2026,
 'Observed constrained expansion and diminished affordability under the EU’s tariffs on Chinese electric vehicles','Joule10(6),102486','commentary','10.1016/j.joule.2026.102486','https://www.sciencedirect.com/science/article/pii/S2542435126001704','1.4;2.6',
 'Близкий комментарий о наблюдаемых рыночных последствиях; у приложения индексируется распределение цен BEV.',
 'Высокий риск тематического пересечения. По названию/метаданным нельзя заключать, что совместное разложение торговли отсутствует. Претензия на первенство не делается.',
 'Подтверждены издательские и университетские метаданные и подписи доступного индекса приложений. Основной полный текст не получен: издатель403/HTML вместо PDF; репозиторий указывает эмбарго до22.11.2026.')
add('Tamara L. Sheldon; Rubal Dua',2025,
 'A perspective on the evolving plug-in electric vehicle landscape amid trade tariffs and strategic responses','Energy Research & Social Science127,104327','perspective','10.1016/j.erss.2025.104327','https://doi.org/10.1016/j.erss.2025.104327','1.2;1.3',
 'Экспертный опрос о барьерах и ответных стратегиях производителей и государств.',
 'Объясняет возможные механизмы; экспертные ожидания не являются причинной оценкой торговли.',
 'Прочитаны издательский abstract и институциональная карточка; полного PDF нет. Ранее неустановленное название и DOI уточнены.')
add('Ming Liu; Han Hao; Xin Sun; Yong Geng; David Reiner; Klaus Hubacek; Xiaobo Qu; Jiaqi Lu; Fengqi You; Fuquan Zhao',2025,
 'The potential for differentiated vehicle segment tariffs','Nature Energy10,1042–1044','correspondence','10.1038/s41560-025-01798-6','https://www.nature.com/articles/s41560-025-01798-6','1.2;3.3',
 'Аргумент о дифференциации торговых мер по автомобильным сегментам.',
 'Полезно для обсуждения вариантов политики; не даёт оптимальной ставки, оцененной нашей моделью.',
 'Издательский открытый фрагмент и запись принятой версии Cambridge; основной PDF не прочитан.')
add('Frank Bickenbach; Dirk Dohse; Rolf J. Langhammer; Wan-Hsin Liu',2024,
 'EU Concerns About Chinese Subsidies: What the Evidence Suggests','Intereconomics59(4),214–221','policy_article','10.2478/ie-2024-0044','https://www.intereconomics.eu/contents/year/2024/number/4/article/eu-concerns-about-chinese-subsidies-what-the-evidence-suggests.html','1.2;2.1',
 'Данные и институциональный анализ китайских промышленных субсидий.',
 'Контекст расследования; статья не подменяет первичный регламент и не измеряет наши фазовые коэффициенты.',
 'Доступен полный издательский HTML; целевой просмотр аргументов, данных и выводов.')
add('Lanxin Zhang; Zongguo Wen; Xin Sun; Yihan Wang; Tingting Zhang',2026,
 'Revealing the impact of electric vehicles trade restrictions on greenhouse gas emissions and welfare','Resources, Conservation and Recycling227,108744','journal_article','10.1016/j.resconrec.2025.108744','https://www.sciencedirect.com/science/article/pii/S0921344925006214','1.2;3.3',
 'Многорегиональная частично-равновесная модель и учёт выбросов для сценариев EV-ограничений.',
 'Торговая структура не равна экологическому результату. Для собственных оценок выбросов нужны дополнительные данные.',
 'Издательский abstract и доступные части статьи; полный PDF не получен. Онлайн2025, журнальный выпуск2026.')
add('Keith Head; Thierry Mayer',2019,'Brands in Motion: How Frictions Shape Multinational Production','American Economic Review109(9),3073–3124','journal_article','10.1257/aer.20161345','https://pubs.aeaweb.org/doi/10.1257/aer.20161345','1.1;1.3',
 'Модель международного размещения производства и сбыта автомобильных брендов.',
 'Обосновывает разграничение владельца марки, места сборки и рынка назначения; не идентифицирует марки в Comext.',
 'Подтверждены издательские метаданные и abstract; полный текст не прочитан.')
add('Pablo Fajgelbaum; Pinelopi Goldberg; Patrick Kennedy; Amit Khandelwal; Daria Taglioni',2024,
 'The US-China Trade War and Global Reallocations','American Economic Review: Insights6(2),295–312','journal_article','10.1257/aeri.20230094','https://pubs.aeaweb.org/doi/10.1257/aeri.20230094','1.3;2.6',
 'Перераспределение экспорта третьих стран при торговой войне США–КНР.',
 'Страны сравнения тоже реагируют; их нельзя автоматически объявлять нетронутым контролем.',
 'Получена NBER-версия, пересмотренная в декабре2023; целевое чтение постановки и интерпретации, не построчная проверка журнальной версии.','expanded/reallocations_nber_2023.pdf')
add('Mary Amiti; Stephen J. Redding; David E. Weinstein',2019,
 'The Impact of the 2018 Tariffs on Prices and Welfare','Journal of Economic Perspectives33(4),187–210','journal_article','10.1257/jep.33.4.187','https://www.aeaweb.org/articles?id=10.1257/jep.33.4.187','1.2;1.3',
 'Подходы к измерению тарифного переноса, цен и благосостояния в эпизоде2018.',
 'Зарубежная оценка не переносится на китайские автомобили ЕС как готовый параметр.',
 'Прочитан издательский abstract; полный текст не получен в данном цикле.')
add('Alberto Cavallo; Gita Gopinath; Brent Neiman; Jenny Tang',2021,
 'Tariff Pass-Through at the Border and at the Store: Evidence from US Trade Policy','American Economic Review: Insights3(1),19–34','journal_article','10.1257/aeri.20190536','https://pubs.aeaweb.org/doi/10.1257/aeri.20190536','1.3;2.3',
 'Микроданные пограничных и розничных цен и различия переноса тарифов.',
 'Таможенная средняя стоимость CN8 не является розничной ценой или ценой постоянного качества.',
 'Подтверждены издательские метаданные и abstract; полный текст не прочитан.')
add('Lingduo Jiang; Yi Lu; Hong Song; Guofeng Zhang',2023,
 'Responses of exporters to trade protectionism: Inferences from the US-China trade war','Journal of International Economics140,103687','journal_article','10.1016/j.jinteco.2022.103687','https://www.sciencedirect.com/science/article/pii/S0022199622001192','1.3;2.3',
 'Месячные таможенные данные и раздельные реакции количества, цен и направлений экспорта.',
 'Декомпозиция каналов уже применяется в литературе; для нашего случая нужен самостоятельный результат.',
 'Издательский abstract и доступный текст введения. Consensus указывает2022; журнальный выпуск январь2023, в библиографии используется2023.')
add('Liugang Sheng; Huasheng Song; Xueqian Zheng',2025,
 'How did Chinese exporters manage the trade war?','Journal of International Money and Finance153,103300','journal_article','10.1016/j.jimonfin.2025.103300','https://www.sciencedirect.com/science/article/pii/S026156062500035X','1.3;2.3',
 'Качество товаров, перенаправление китайского экспорта и изменение unit values.',
 'Средняя таможенная стоимость смешивает цену и качество. Не измерять качество нашей панелью без отдельной идентификации.',
 'Издательский abstract и институциональные метаданные; запрос авторского PDF вернул HTML, полный текст не получен.')
add('Irina Balteanu; Maximiliano Moreno; Francesca Viani',2026,
 'Flooded by China? Trade diversion due to US tariffs during Trump’s first mandate','Banco de España Working Paper2634, October2026','working_paper','10.53479/44545','https://www.bde.es/wbe/en/publicaciones/analisis-economico-investigacion/documentos-trabajo/flooded-by-china-trade-diversion-due-to-us-tariffs-during-trumps-first-mandate.html','1.3;2.6',
 'DiD-локальные проекции и дезагрегированные импортные данные ЕС для другого тарифного эпизода.',
 'Полезна для зависимости результатов от товара и направления; чистая идентификация авторов не переносится в наш эпизод.',
 'Полный официальный PDF получен; целевой просмотр данных, спецификации и ограничений.','expanded/flooded_2026.pdf')
add('J. M. C. Santos Silva; Silvana Tenreyro',2006,'The Log of Gravity','Review of Economics and Statistics88(4),641–658','journal_article','10.1162/rest.88.4.641','https://personal.lse.ac.uk/TENREYRO/jensen08k.pdf','2.2',
 'PPML, гетероскедастичность и проблемы логарифмирования торговых потоков.',
 'Выбор PPML не создаёт причинной идентификации и не требует буквального распределения Пуассона для евро.',
 'Полный авторский PDF получен; целевое чтение мотивации и методики.','expanded/log_gravity_2006.pdf')
add('J. M. C. Santos Silva; Silvana Tenreyro',2022,'The Log of Gravity at 15','Portuguese Economic Journal21,423–437','review','10.1007/s10258-021-00203-w','https://link.springer.com/article/10.1007/s10258-021-00203-w','2.2;2.6',
 'Обзор дальнейшей литературы по PPML и моделям постоянной эластичности.',
 'Методический ориентир; обзор не доказывает состоятельность именно нашей небольшой четырёхэффектной панели.',
 'Проверены издательские метаданные и abstract; полный текст не заявляется прочитанным.')
add('Anthony F. Shorrocks',2013,'Decomposition procedures for distributional analysis: a unified framework based on the Shapley value','Journal of Economic Inequality11,99–126','journal_article','10.1007/s10888-011-9214-z','https://link.springer.com/article/10.1007/s10888-011-9214-z','2.2',
 'Разложения с усреднением порядков замены факторов на основе значения Шепли.',
 'Метод стандартный. Точное сложение компонентов не превращает бухгалтерское разложение в причинное.',
 'Издательские метаданные; основной текст закрыт подпиской. Онлайн2012, выпуск2013.')
add('Evelyn M. Kitagawa',1955,'Components of a Difference Between Two Rates','Journal of the American Statistical Association50(272),1168–1194','journal_article','10.1080/01621459.1955.10501299','https://doi.org/10.1080/01621459.1955.10501299','2.2',
 'Разделение изменения общей величины на изменение групповых уровней и структуры.',
 'Классическая основа симметричного разложения; не заявлять его собственной методической новизной.',
 'Подтверждены первичные библиографические сведения; полный текст не прочитан.')
add('Whitney K. Newey; Kenneth D. West',1987,'A Simple, Positive Semi-definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix','Econometrica55(3),703–708','journal_article','10.2307/1913610','https://www.nber.org/papers/t0055','2.2;2.6',
 'Положительно полуопределённая HAC-оценка ковариации.',
 'Наша малая временная выборка и поправки требуют осторожности; статья не гарантирует точность конкретного95%-интервала.',
 'Получен скан препринта1986; текст не извлечён и построчно не проверялся. Прочитан первичный abstract; журнальная дата1987.','expanded/newey_west_1986.pdf')
add('Sergio Correia; Paulo Guimarães; Tom Zylkin',2020,'Fast Poisson estimation with high-dimensional fixed effects','Stata Journal20(1),95–115','journal_article','10.1177/1536867X20909691','https://doi.org/10.1177/1536867X20909691','2.2',
 'IRLS с поглощением постоянных эффектов и проверкой существования PPML-оценок.',
 'В проекте самостоятельная реализация, а не запуск Stata ppmlhdfe; совпадение проверяется независимыми вычислениями.',
 'Проверены издательский abstract, авторская документация и открытый текст arXiv1903.01690.')
add('Martin Weidner; Thomas Zylkin',2021,'Bias and consistency in three-way gravity models','Journal of International Economics132,103513','journal_article','10.1016/j.jinteco.2021.103513','https://www.sciencedirect.com/science/article/pii/S0022199621000933','2.2;2.6',
 'Смещение параметров и ковариаций PPML с большим числом эффектов.',
 'Не утверждать применение их коррекции или прямую применимость их асимптотики к нашей четырёхэффектной модели.',
 'Издательский abstract и запись открытой версии arXiv; отдельная аналитическая коррекция в проекте не реализована.')
add('Samuel Rosenow; Alvaro Espitia; Ana Fernandes',2024,'High Tariffs, High Stakes: The Policy Drivers Behind Firm-Level Adoption of Green Technologies','World Bank/IFC research draft, July2024','working_paper',None,'https://documents1.worldbank.org/curated/en/099121224200014958/pdf/P50267216f338606e19f5f1ca4dceead53d.pdf','1.2;3.3',
 'Фирменный структурный гравитационный анализ импорта зелёных технологий в35 развивающихся странах.',
 'Другая единица анализа; не выдавать фирменные реакции из внешней работы за наши оценки.',
 'Прочитан индексируемый abstract официального документа; обычная загрузка PDF403, полного локального текста нет.')
add('Stuart G. Baker',1994,'The Multinomial-Poisson Transformation','JRSS SeriesD: The Statistician43(4),495–504','journal_article','10.2307/2348134','https://academic.oup.com/jrsssd/article-abstract/43/4/495/7123023','2.2',
 'Связь мультиномиального и пуассоновского правдоподобий.',
 'Наша модель долей — эквивалентное представление, а не новый оцениватель; алгебра не создаёт причинности.',
 'Прочитана издательская аннотация; эквивалентность нашего случая выведена и численно проверена отдельно.')
add('Paulo Guimarães',2004,'Understanding the Multinomial-Poisson Transformation','Stata Journal4(3),265–273','journal_article','10.1177/1536867X0400400304','https://journals.sagepub.com/doi/10.1177/1536867X0400400304','2.2',
 'Преобразование между Poisson- и logit-представлениями.',
 'Для стоимости используется квазиправдоподобие; денежные единицы не объявляются независимыми биномиальными испытаниями.',
 'Проверены издательская аннотация и библиографическая карточка; полный текст не прочитан.')

add('Robert C. Feenstra; John Romalis',2014,'International Prices and Endogenous Quality','Quarterly Journal of Economics129(2),477–527','journal_article','10.1093/qje/qju001','https://academic.oup.com/qje/article-abstract/129/2/477/1866808','1.3;2.3',
 'Модель эндогенного качества и различие unit values и очищенных цен.',
 'Наша CN8-панель не идентифицирует качество; собственные unit-value-компоненты не называются чистыми ценами.',
 'Получен полный NBER-препринт2012; целевое чтение мотивации и структуры. Метаданные журнальной версии2014 проверены отдельно.','expanded/quality_nber_2012.pdf')

downloads=json.loads((OUT/'expanded/download_manifest.json').read_text())
writing_access_path=OUT/'writing_reading_access.json'
writing_updates={r['id']:r for r in json.loads(writing_access_path.read_text())['updates']} if writing_access_path.exists() else {}
for r in records:
    r['checked_on']='2026-10-26'
    if r.get('local_filename'):
        match=next((x for x in downloads if x['name']==Path(r['local_filename']).name and 'sha256' in x),None)
        if match:r['sha256']=match['sha256'];r['download_url']=match['url']
    if r['id'] in writing_updates:
        update=writing_updates[r['id']]
        for key in ['download_url','sha256','local_filename','review_status']:
            r[key]=update[key]
        r['checked_on']=update.get('checked_on',r['checked_on'])
(OUT/'expanded_catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
with (OUT/'expanded_catalog.csv').open('w',newline='') as f:
    keys=['id','authors','year','title','venue','type','doi','primary_url','sections','data_method','use_and_limit','review_status','priority']
    w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(records)

official=[
 ('Eurostat','Comext DS-045409, API guide','https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started/comext-database','2.1','Основной источник месячных потоков; точные JSON и запросы сохранены вdata/full_raw.'),
 ('Eurostat','International trade in goods — detailed data: reference metadata','https://ec.europa.eu/eurostat/cache/metadata/en/ext_go_detail_sims.htm','1.1;2.1','Определения происхождения, стоимости, количества, агрегатов и конфиденциальности.'),
 ('Eurostat','Trade in goods — Rotterdam effect','https://ec.europa.eu/eurostat/web/european-statistics-learning-hub/statistics-for-beginners/trade-in-goods','1.1;2.4;3.1','Место таможенного оформления не обязательно совпадает со страной потребления и физическим портом.'),
 ('European Commission','Commission Implementing Regulation(EU)2024/2754','https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202402754','2.1;3.3','Первичный акт; юридический охватexCN8/TARIC отличается от широкого кодаCN8 модели.'),
 ('European Commission','Definitive duties: official Access2Markets scope summary','https://trade.ec.europa.eu/access-to-markets/en/news/eu-commission-imposes-countervailing-duties-imports-battery-electric-vehicles-bevs-china','2.1','Подтверждает начало применения30.10.2024 и охват меры; месячная окончательная фаза начинается вноябре.'),
 ('IEA', 'Global EV Outlook2025','https://www.iea.org/reports/global-ev-outlook-2025','1.1;2.1','Международный отраслевой контекст; границыEV определены отдельно и не равны трём кодам нашей панели.'),
 ('IEA', 'Global EV Outlook2026, manufacturing and trade','https://www.iea.org/reports/global-ev-outlook-2026/manufacturing-and-trade','1.1;2.1;3.3','Контекст2025, производство и происхождение брендов; источник не подменяет нашу выгрузку Comext.'),
 ('ACEA','New car registrations2025,27January2026','https://www.acea.auto/pc-registrations/new-car-registrations-1-8-in-2025-battery-electric-17-4-market-share/','2.1;2.3','Регистрации и структура всего рынка ЕС. Не делить таможенные поставки на регистрации как будто это точная рыночная доля.'),
 ('European Commission','Guidance on price undertakings,12January2026','https://policy.trade.ec.europa.eu/news/commission-issues-guidance-document-submission-price-undertaking-offers-battery-electric-vehicles-2026-01-12_en','3.3','Контекст возможных инструментов политики; вне оценочного периода2021–2025.'),
 ('European Commission','EU–China joint statement,9October2026','https://ec.europa.eu/commission/presscorner/api/files/document/print/en/statement_26_2122/STATEMENT_26_2122_EN.pdf','3.3','Последующий режим; сам документ не устанавливает числовую квоту и дату её вступления. Не смешивать с основной выборкой.')]
official=[{'id':f'O{i:02d}','institution':a,'title':b,'url':c,'sections':d,'use_and_limit':e,'checked_on':'2026-10-26'} for i,(a,b,c,d,e) in enumerate(official,1)]
(OUT/'official_sources_catalog.json').write_text(json.dumps(official,ensure_ascii=False,indent=2)+'\n')
lines=['# Расширенная карта литературы и источников','',
 'Дата:26.10.2026. Это целевой поиск и аннотированная карта, а не систематический обзор всей мировой литературы.','',
 f'В реестре {len(records)} научных и учебных работ и {len(official)} официальных источников. Две работы — студенческие; комментарии, рабочие статьи и журнальные исследования различаются в полеtype. У одной вспомогательной записи год пока не подтверждён. НаличиеPDF не означает прочтения всего текста.','',
 '## Наиболее близкие материалы и значение для новизны','',
 '- S01: практически совпадают исходный BEV-эпизод и три страны сравнения.','- S08: уже есть BEV/PHEV и наблюдаемая европейская оценка, поэтому добавлениеPHEV само по себе вкладом не считается.','- S09: новый близкий комментарий Joule требует прямого цитирования; без основного полного текста нельзя утверждать отсутствие повтора всей конструкции.','- Собственный проверяемый вклад проекта: совместные физические/стоимостные и географические разложения, границы интерпретации фазовых коэффициентов и чувствительность к ориентиру сравнения. Приоритет открытия гибридной адаптации не заявляется.','',
 '## Научные работы','', '| ID | Работа и тип | Где использовать | Данные/подход | Значение и ограничение | Глубина проверки |','|---|---|---|---|---|---|']
for r in records:
    year=str(r['year']) if r['year'] is not None else 'год не установлен'
    citation=f"{r['authors']}({year}). [{r['title']}]({r['primary_url']}). {r['venue']}. {r['type']}"
    lines.append('| '+' | '.join([r['id'],citation,r['sections'],r['data_method'],r['use_and_limit'],r['review_status']]).replace('\n',' ')+' |')
lines+=['','## Официальные источники','', '| ID | Источник | Параграфы | Использование и границы |','|---|---|---|---|']
for r in official:lines.append(f"| {r['id']} | {r['institution']}: [{r['title']}]({r['url']}) | {r['sections']} | {r['use_and_limit']} |")
lines+=['','## Правила использования','',
 '1. В обзоре различать эмпирическую статью, сценарную модель, экспертный комментарий и студенческую работу.','2. Ссылаться на первичную публикацию; фиксировать отдельно год журнального выпуска и версию прочитанного препринта.','3. Открытые Comext/ACEA/IEA имеют разный охват; согласовывать определения перед сравнением чисел.','4. Не приписывать модели расчёт выбросов, благосостояния, оптимального тарифа или намерений обходить пошлины.','5. Полные локальные копии некоторых новыхPDF остаются читательским кэшем; в репозитории сохранены ссылки, контрольные суммы, статусы и аннотации.','',
 'Поиск: запросы по EU-ChinaEV/PHEVtariffs, trade diversion, product switching, customs value/quality, PPML/HAC/decomposition. Использованы веб-поиск и Consensus как обнаружение работ; библиографические сведения проверены по издателям и институциональным репозиториям. Один одновременный запрос Consensus был ограничен частотой; вместо обхода использованы обычные первичные источники.']
(ROOT/'LITERATURE_REVIEW_MATRIX.md').write_text(normalize_prose('\n'.join(lines)+'\n'))

bib=[]
for r in records:
    typ='article' if r['type'] not in ['working_paper','thesis'] else 'misc'
    fields={'author':r['authors'].replace(';',' and').replace(',',' and').replace('et al.','and others'),'title':r['title'],'year':r['year'],'journal':r['venue'],'doi':r['doi'],'url':r['primary_url'],'note':r['review_status']}
    bib.append('@'+typ+'{'+r['id']+',\n'+',\n'.join('  '+k+' = {'+str(v).replace('{','').replace('}','')+'}' for k,v in fields.items() if v is not None)+'\n}')
(OUT/'expanded_references.bib').write_text('\n\n'.join(bib)+'\n')
print({'research_records':len(records),'official_records':len(official),'review_statuses_preserved':True})
