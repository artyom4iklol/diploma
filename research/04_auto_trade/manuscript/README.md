# Текст автомобильного диплома

Состояние на 28 октября 2026 года: полный диплом собран в [едином Word](../documents/diploma_auto_trade.docx). Он включает введение с восемью задачами, три главы, заключение, 34 использованных источника и три приложения. Содержание — [полный Markdown](full_thesis_content.md), [введение](introduction.md), [заключение](conclusion.md), [список источников](bibliography.md), [приложения](appendices.md). Редакторская и визуальная проверка — [итоговый протокол](full_thesis_review.md).

- [Глава 3 целиком в Markdown](chapter3_content.md): четыре параграфа, выводы, шесть таблиц и четыре рисунка. Исходные части: [3.1](chapter3_1.md), [3.2](chapter3_2.md), [3.3](chapter3_3.md), [3.4](chapter3_4.md), [выводы](chapter3_conclusions.md).
- [Источники главы 3](chapter3_bibliography.md), [реестр сносок](chapter3_sources.json), [сценарная основа](chapter3_evidence.json), [проверки](chapter3_checks.json), [редакторская проверка](chapter3_review.md). Все 18 комбинаций сохранены в `../results/chapter3_application/scenario_transfer.csv`. Глава усилена 48 историческими квартальными сопоставлениями, первичными регистрациями ACEA и порогом допустимых расходов. Расширенная основа — [реестр дополнений](chapter3_extension_evidence.json).
- Воспроизведение главы 3: `python research/04_auto_trade/manuscript/build_chapter3_evidence.py`, затем `python research/04_auto_trade/manuscript/extend_chapter3_evidence.py`, затем `python research/04_auto_trade/manuscript/plot_chapter3.py`, затем `python research/04_auto_trade/manuscript/build_chapter3.py`. Модели главы 2 не пересчитываются.
- [План главы 3](chapter3_plan.md) и [реестр планирования](chapter3_planning_sources.json) сохраняются как подготовительные документы. В написанной главе применено уточнённое название 3.2: «Обоснование рекомендаций на основе сценарных расчётов».

- [Глава 2 целиком в Markdown](chapter2_content.md): шесть параграфов, выводы, шесть основных таблиц, восемь основных рисунков и техническое приложение с четырьмя таблицами и четырьмя рисунками. Параграфы доступны отдельно: [2.1](chapter2_1.md), [2.2](chapter2_2.md), [2.3](chapter2_3.md), [2.4](chapter2_4.md), [2.5](chapter2_5.md), [2.6](chapter2_6.md), [выводы](chapter2_conclusions.md).
- [Источники главы 2](chapter2_bibliography.md), [реестр ссылок и версий](chapter2_sources.json), [численная основа](chapter2_evidence.json), [проверки](chapter2_checks.json) и [редакторская записка](chapter2_review.md).
- [Карта будущих иллюстраций](chapter2_illustration_map.md) фиксирует места и исходные ряды. Все 12 рисунков встроены в Markdown и в итоговый Word диплома.
- Построение рисунков: `python research/04_auto_trade/manuscript/plot_chapter2.py`. Сборка Markdown, приложения и обновление расчётных таблиц: `python research/04_auto_trade/manuscript/build_chapter2.py`. Сборка сверяет исходные хеши, месячные и национальные суммы; модели не пересчитываются.

- [Глава 1 целиком](chapter1_content.md) и [Word](../documents/chapter1_auto_trade.docx): четыре параграфа и выводы, 18 страниц в согласованном оформлении, 34 подстрочные сноски, 26 различных источников.
- Исходные параграфы: [1.1](chapter1_1.md), [1.2](chapter1_2.md), [1.3](chapter1_3.md), [1.4](chapter1_4.md), [выводы](chapter1_conclusions.md).
- [Библиография главы](chapter1_bibliography.md) и [машиночитаемый реестр](chapter1_sources.json) содержат только использованные источники, связь со сносками и ограничения проверенных версий.
- [Редакторская проверка](chapter1_review.md), [проверки состава](chapter1_checks.json) и [проверки оформления](chapter1_layout_checks.json).
- Сборка: `python research/04_auto_trade/manuscript/build_chapter1.py`. После повторной сборки требуется заново выполнить рендеринг Word и визуальную проверку всех страниц; генератор сбрасывает статус визуальной проверки.

Глава написана связным академическим текстом с учётом курсовой Наумова; параметры Word взяты из согласованного диплома. Графики и таблицы не включены. Собственные численные результаты предназначены для второй главы. Подготовительная контрольная точка, данные и модели сохранены без пересчёта.

## Сборка полного документа

`python research/04_auto_trade/manuscript/prepare_full_thesis.py` обновляет введение, заключение, действительную библиографию и приложения в объединённом Markdown. `python research/04_auto_trade/manuscript/build_full_thesis.py` собирает Word через Pandoc с нативными формулами, сносками и оглавлением. Каталог временной сборки задаётся `AUTO_THESIS_BUILD_DIR`; по умолчанию используется системный временный каталог. Номера оглавления сохранены в `full_thesis_page_map.json` для проверенной версии. После содержательных или форматных изменений необходимо заново отрендерить Word, обновить номера страниц и проверить все страницы; генератор сбрасывает статус визуальной проверки. Исходные главы и расчётные результаты при объединении не переписываются.
