# Журнал углубленной проверки новизны

Дата: 16.10.2026. Вопрос и метод заданы в `protocol.md`; данные и модель в ходе этого аудита не менялись. Это целевая проверка ближайших аналогов, не зарегистрированный систематический обзор.

## Каналы

- Веб-поиск на английском, русском и корейском; точные названия и DOI; первичные сайты KCI/KoreaScience, издатели, авторские копии опубликованных статей.
- Consensus: тематический поиск и получение записей ранее найденных работ. Результаты использовались для навигации; методы сверялись с текстами.
- OpenAlex API: метаданные трех приоритетных работ и запросы цитирующих исследований. Индекс не трактовался как исчерпывающий.
- Обратный просмотр библиографии и прямой поиск цитирующих работ, включая обнаруженную ссылку Koo (2026) → Hong (2023).

## Основные веб-запросы

Запросы приводятся дословно; повторные открытия и технические повторы ссылок не перечисляются.

1. `"Analysis of Korean Import and Export in the Semiconductor Industry" filetype:pdf`
2. `"Analysis of export changes to major trading partners of the Korean semiconductor industry"`
3. `"Research on CMS decomposition of South Korea’s manufacturing exports to China"`
4. `"Revealed Trade Competitiveness between Korea and Japan" pdf`
5. `"semiconductor" "Herfindahl" "decomposition"`
6. `"export concentration" "product mix" decomposition`
7. `"반도체" "수출" "집중도" "분해"`
8. `"export concentration" "Shapley" "geographic"`
9. `"semiconductor" "concentration" "shift-share"`
10. `"semiconductor" "Shapley decomposition" exports concentration`
11. `"integrated circuits" "composition effect" exports`
12. `"반도체" "허핀달" "분해"`
13. `"export" "geographical concentration" "composition effect"`
14. `"Herfindahl" "export" "Shapley"`
15. `"destination concentration" "decomposition" exports`
16. `"반도체" "샤플리" "수출"`
17. `"한국 반도체산업의 주요 교역국에 대한 수출변동 분석" pdf`
18. `"10.20462/tebs.2023.11.24.6.179" pdf`
19. `"Structural Changes in Korea’s Semiconductor Supply Chain"`
20. `"Exploratory Data Analysis of Big Data on Semiconductor Industry"`
21. `"Economic preference for semiconductor trade deals" concentration`
22. `"10.54404/jts.2026.210v.08"`
23. `"semiconductor" "export diversification" "composition" "HHI"`
24. `"semiconductor" "product-mix" "diversification"`
25. `"semiconductor" "within" "concentration" "decomposition"`
26. `"экспорт" "микросхем" "концентрации" "декомпозиция"`
27. `"geographic concentration" "product composition" exports semiconductor`
28. `"semiconductor" "export" "constant composition"`
29. `"반도체" "수출" "집중도" "구성효과"`
30. `"semiconductor" "concentration" "decomposition" site:oecd.org`
31. `"Korea" "semiconductor" "Shapley" exports`
32. `"반도체" "수출집중도" "분해"`
33. `"Assessing Trade Concentration, Dependency, and Resilience" pdf`
34. `"10.35611/jkt.2025.29.7.67"`

Дополнительно использованы запросы по точным названиям/DOI новых источников и запрос `site:oecd.org "0b35b5a6-en" "shift-share" "productivity"`, который позволил исключить разложение производительности как ложное предметное совпадение.

## Consensus

Успешные запросы:

- `semiconductor integrated circuit export geographic concentration product mix composition Shapley shift share decomposition Japan Korea`
- `"export concentration" "decomposition" product destination composition`

Получена полная библиографическая запись Kitetu через `fetch`; DOI и состав авторов исправлены по опубликованному тексту: авторов трое, в записи Consensus один из них отсутствовал. Дополнительный узкий запрос с фильтром годов вернул `INVALID_ARGUMENT` и **не засчитывается как выполненный поиск**. Проверка продолжена веб-поиском.

## Полнотекстовый доступ

Shin & Shin: PDF KoreaScience скачан обычным публичным запросом; 27 страниц. Первоначальные ошибки веб-просмотра не означали отсутствия файла.

Koo: доступен открытый PDF KCI, 21 страница; ссылка сработала при обычном переходе со страницы статьи с сохранением сессии. Проверены формула, таблицы, выводы и библиография. DOI взят с первой страницы PDF.

Kim (2021): полный опубликованный текст доступен на ResearchGate; первоначальная страница издателя возвращала техническую заглушку. Проверены раздел 2, формулы (1)–(3), разделы 3–4 и ссылки.

Kitetu et al.: полный опубликованный текст доступен в авторской загрузке ResearchGate; старая ссылка PFW на номер журнала при прямом скачивании вернула 404. Основные данные и методы проверены по авторской копии, а не только по записи Consensus.

Hong: KCI/RISS/DBpia/OpenAlex проверены; KCI preview — только одна страница. Полный текст не получен. Ограничение не обходилось и не скрывается в вердикте.

Kim & Lee (2025): записи KCI, Kyobo, ResearchGate и авторская страница проверены. Полного текста в использованных доступных источниках нет; аннотационный уровень сохранен в матрице. Номера страниц взяты из KCI и DOI-записи, а не из отличающегося списка на авторской странице.

## Правило вывода

Отрицательная выдача отдельного запроса не доказывает отсутствия исследования. Сопоставление выполнено по вопросу и оцениваемой величине; отсутствие конкретного ключевого слова не считалось достаточным. Результат аудита — ограниченная эмпирическая добавка без установленного прямого повтора, а не сертификат мировой оригинальности.
