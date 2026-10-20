# Материалы главы 3

- `chapter3.docx` — оформленная глава; в полной сборке диплома занимает страницы 54–73. Текущая редакция включает 9 источников и 11 подстрочных сносок.
- `chapter3_content.md` — единый текст с библиографией.
- `chapter3_1.md` — приоритеты по результатам исследования.
- `chapter3_2.md` — товарная диверсификация.
- `chapter3_3.md` — география и источники спроса.
- `chapter3_4.md` — сценарии, реализация и мониторинг.
- `chapter3_scenario_protocol.md` — заранее заданные правила дополнительного расчета.
- `chapter3_evidence.json` и три CSV `chapter3_scenario*.csv` — все сценарии, интервалы и окна.
- `chapter3_market_protocol.md` — правила сопоставления восьми направлений при одинаковом приросте.
- `chapter3_market_evidence.json` и `chapter3_markets.csv` — все географические варианты, интервалы, окна и масштабы по товарным ячейкам.
- `chapter3_source_audit.json` — источники, подтверждаемые утверждения и ограничения доступа.
- `chapter3_review.md`, `chapter3_checks.json`, `chapter3_document_checks.json` — содержательная, численная и визуальная проверка.
- `chapter3_assets/` — три черно-белых рисунка в PNG и SVG.

## Воспроизведение

Из корня репозитория, с зависимостями существующего проекта и генераторов предыдущих глав:

```bash
python research/02_chip_trade/documents/prepare_chapter3_evidence.py
python research/02_chip_trade/documents/prepare_chapter3_assets.py
python research/02_chip_trade/documents/prepare_chapter3_markets.py
python research/02_chip_trade/documents/build_chapter3.py
python research/02_chip_trade/documents/audit_chapter3.py
```

Новые обращения к Comtrade не нужны. Скрипты читают сохраненную панель и основную географическую сетку; все результаты главы 3 записываются в отдельные файлы. После новой сборки Word визуальную проверку следует выполнить заново: сборщик намеренно возвращает флаг ожидания проверки.
