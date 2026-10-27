"""Assemble and check Markdown chapter 2. Does not create Word or refit models."""
from pathlib import Path
import hashlib
import json
import re
import build_chapter2_evidence as evidence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TITLE = "Глава 2 Анализ товарной и географической перестройки поставок новых электромобилей и бензиновых гибридов из Китая в ЕС"


def main():
    evidence.main()
    tables = json.loads((HERE / "chapter2_generated_tables.json").read_text())
    sections = [HERE / f"chapter2_{i}.md" for i in range(1, 7)]
    sections.append(HERE / "chapter2_conclusions.md")
    for token, filename in [("T03", "chapter2_3.md"), ("T04", "chapter2_4.md"), ("T05", "chapter2_5.md")]:
        path = HERE / filename
        text = path.read_text()
        marked = f"<!-- BEGIN AUTO {token} -->\n" + tables[token] + f"\n<!-- END AUTO {token} -->"
        if "{{" + token + "}}" in text:
            text = text.replace("{{" + token + "}}", marked)
        else:
            text, count = re.subn(rf"<!-- BEGIN AUTO {token} -->.*?<!-- END AUTO {token} -->", lambda _: marked, text, flags=re.S)
            assert count == 1, (filename, token)
        path.write_text(text, encoding="utf-8")

    prior = json.loads((HERE / "chapter1_sources.json").read_text())["citations"]
    notes = {}

    def note(key, ids, text, scope, files=(), urls=(), kind="external"):
        notes[key] = {"source_ids": ids, "text": text, "supported_scope": scope,
                      "kind": kind, "source_files": list(files), "urls": list(urls)}

    def old(key, original, scope):
        item = prior[original]
        note(key, item["source_ids"], item["text"], scope)

    note("C2LAUNCH", ["C2O11"], "European Commission. Commission launches investigation on subsidised electric cars from China. Press release, 04.10.2023. С. 1.",
         "Сигнал 13.09.2023 и формальный запуск 04.10.2023.", urls=["https://ec.europa.eu/commission/presscorner/api/files/document/print/en/ip_23_4752/IP_23_4752_EN.pdf"])
    note("C2JUNE", ["C2O12"], "European Commission. Commission investigation provisionally concludes that electric vehicle value chains in China benefit from unfair subsidies. Press release, 12.06.2024. С. 1.",
         "Июньское предварительное раскрытие; фактическое начало временной меры проверяется по июльскому документу.", urls=["https://ec.europa.eu/commission/presscorner/api/files/document/print/en/ip_24_3231/IP_24_3231_EN.pdf"])
    note("C2PROVISIONAL", ["C2O13"], "European Commission, Representation in Ireland. Commission imposes provisional countervailing duties on imports of battery electric vehicles from China while discussions with China continue. 04.07.2024. Раздел Procedure and next steps (дата обращения: 27.10.2026).",
         "Временные меры применяются с 05.07.2024; месячный индикатор июля–октября является авторской агрегацией.", urls=["https://ireland.representation.ec.europa.eu/news-and-events/news/commission-imposes-provisional-countervailing-duties-imports-battery-electric-vehicles-china-while-2024-07-04_en"])
    note("C2DEFINITIVE", ["O04", "O05"], "Commission Implementing Regulation (EU) 2024/2754 of 29 October 2024. Art. 1, 5. European Commission. EU Commission imposes countervailing duties on imports of battery electric vehicles (BEVs) from China. Access 2Markets, 12.12.2024 (дата обращения: 27.10.2026).",
         "Дата начала 30.10.2024, ex-CN/TARIC и неодинаковые ставки производителей; не оценка фактически уплаченной средней ставки.", urls=["https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202402754", "https://trade.ec.europa.eu/access-to-markets/en/news/eu-commission-imposes-countervailing-duties-imports-battery-electric-vehicles-bevs-china"])
    note("C2DATA", ["O01"], "Eurostat. Comext DS-045409. Месячный импорт, январь 2021 — декабрь 2025 года; CN 87038010, 87036010, 87034010; SUPPLEMENTARY_QUANTITY и VALUE_IN_EUROS. Выгрузка 26.10.2026, обновление источника 16.10.2026. Расчёты автора.",
         "Источник собственной панели и годовых/квартальных агрегатов; численные значения проверены по chapter2_evidence.json.", files=["data/full_raw/request.json", "results/full/annual_eu_flows.csv", "results/full/panel.csv"], kind="data")
    old("C2METADATA", "ESTATDEF", "Определения происхождения, внешнего импорта, стоимости и единиц; самостоятельная трактовка агрегатов отделена от определения Eurostat.")
    old("C2ROTTERDAM", "ROTTERDAM", "Различие страны оформления и конечного потребления.")
    old("C2SHAPLEY", "DECOMPOSITION", "Принцип симметричного распределения; прочитан черновик 1999 года, не журнальная версия 2013 года.")
    old("C2QUALITY", "QUALITY", "Средняя стоимость не равна цене неизменного качества; прочитаны аннотация и введение WP 2012 года.")
    old("C2PPML", "PPML", "Оценивание мультипликативного среднего в уровнях; прочитан основной полный текст и его введение, а не только метаданные.")
    old("C2KE", "KE", "Ближайший аналог, статус бакалаврской работы и различие постановок.")
    old("C2BARWICK", "BARWICKREVIEW", "Регистрации фиксированных моделей пяти марок в шести странах; не все China-origin потоки ЕС.")
    old("C2DOU", "DOU", "Сценарный анализ; принятая авторская версия Nature Energy, а не недоступный основной текст Joule.")
    own = {
        "C2AUDIT": ("Аудит исходной панели и независимые численные проверки авторских расчётов, 26–27.10.2026.", ["results/full/data_audit.json", "results/full/observability_details.json", "results/augmented/data_audit.json", "results/augmented/conditional_share_equivalence.json", "results/augmented/numerical_validation.json", "results/augmented/output_validation.json"]),
        "C2MODEL": ("Расчёты автора: предпочтительная PPML CN/REST, спецификация от 26.10.2026; два исхода и синхронные взвешенные повторные оценки.", ["augmented_model_spec.json", "results/augmented/rest_preferred_quantity.json", "results/augmented/rest_preferred_value.json", "results/augmented/paired_block_summary.json"]),
        "C2ACCOUNT": ("Расчёты автора: симметричное разложение доли Китая во внешнем импорте выбранных кодов, базы 2023/2024 и конечный 2025 год.", ["results/full/accounting_decompositions.json"]),
        "C2VALUE": ("Расчёты автора: разложение изменения стоимости на количество и среднюю таможенную стоимость внутри CN8.", ["results/full/china_value_change_accounting.json"]),
        "C2UNITFLAG": ("Eurostat Comext; авторская проверка опубликованных месячных количества и стоимости BEV из Китая, Нидерланды, 2025 год. Причина низкой удельной стоимости по агрегированной панели не установлена.", ["results/full/panel.csv", "results/full/annual_member_flows.csv", "manuscript/chapter2_evidence.json"]),
        "C2GEODATA": ("Eurostat Comext; расчёты автора по годовым потокам стран оформления, 2023–2025 годы.", ["results/full/annual_member_flows.csv"]),
        "C2CONCENTRATION": ("Расчёты автора: технологические и совокупные HHI по количеству и стоимости; шкала 0–1.", ["results/full/entry_concentration.csv", "results/geography_focus/pooled_HHI_product_geography.csv"]),
        "C2GROUP": ("Расчёты автора: трёхфакторное групповое разложение технологических HHI с усреднением шести порядков замены.", ["results/geography_focus/category_HHI_group_shapley.csv"]),
        "C2ENTRY": ("Расчёты автора: тождество продолжающих, новых положительных и исчезнувших направлений относительно 2023 года.", ["results/geography_focus/entry_margin_summary.csv"]),
        "C2DYNAMIC": ("Расчёты автора: полугодовая PPML без тренда; обе половины 2022 года исключены; совместная предшествующая диагностика по шести коэффициентам.", ["results/augmented/rest_halfyear_quantity.json", "results/augmented/rest_halfyear_value.json"]),
        "C2SENSITIVITY": ("Расчёты автора: предусмотренные варианты расширенной PPML по количеству и стоимости. Полный набор коэффициентов сохранён отдельно от основной таблицы.", ["results/augmented/coefficients.csv"]),
        "C2GEOMODEL": ("Расчёты автора: модель групповой неоднородности и ковариационно согласованные контрасты окончательной фазы.", ["results/augmented/rest_geographic_quantity.json", "results/augmented/rest_geographic_value.json"]),
    }
    for key, (text, paths) in own.items():
        for path in paths:
            assert (ROOT / path).exists(), path
        note(key, ["O01", "AUTHOR_CALCULATIONS"], text, "Собственный расчёт на сохранённых данных; не приписывается внешней публикации.", files=paths, kind="own_calculation")
    for item in notes.values():
        item["source_sha256"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in item["source_files"]}

    content = "# " + TITLE + "\n\n" + "\n\n".join(p.read_text().strip() for p in sections) + "\n"
    keys = re.findall(r"\[\^([^\]]+)\]", content)
    unique = list(dict.fromkeys(keys))
    assert set(unique) == set(notes), (set(unique) - set(notes), set(notes) - set(unique))
    assert "{{" not in content
    assert not re.search(r"!\[|Рисунок\s+2\.", content)
    assert len(re.findall(r"^Таблица 2\.[1-6] —", content, re.M)) == 6
    assert len(re.findall(r"^## 2\.[1-6] ", content, re.M)) == 6
    definitions = "\n".join(f"[^{key}]: {notes[key]['text']}" for key in unique)
    combined = content + "\n" + definitions + "\n"
    (HERE / "chapter2_content.md").write_text(combined, encoding="utf-8")
    (HERE / "chapter2_sources.json").write_text(json.dumps({"date": "2026-10-27", "citations": notes, "footnote_occurrences": len(keys), "first_use_order": unique}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    external = [notes[key]["text"] for key in unique if notes[key]["kind"] != "own_calculation"]
    (HERE / "chapter2_bibliography.md").write_text("# Источники второй главы\n\n" + "\n\n".join(f"{i}. {text}" for i, text in enumerate(external, 1)) + "\n\nСобственные расчёты и их исходные файлы перечислены в chapter2_sources.json; они не представлены отдельными внешними публикациями.\n", encoding="utf-8")
    checks = {
        "date": "2026-10-27", "format": "Markdown", "chapter_complete": True,
        "sections": 6, "conclusions": True, "tables": 6, "figures_created_this_stage": 0,
        "footnote_occurrences": len(keys), "distinct_footnote_definitions": len(unique),
        "all_citations_resolved": True, "unresolved_table_placeholders": False,
        "words_including_tables_and_formula_tokens": len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+(?:[-–][A-Za-zА-Яа-яЁё0-9]+)*", content)),
        "cyrillic_words_in_body_and_tables": len(re.findall(r"[А-Яа-яЁё]+(?:[-–][А-Яа-яЁё]+)*", content)),
        "source_evidence": "chapter2_evidence.json", "regressions_refitted": False,
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sections, HERE / "chapter2_content.md"]},
        "limits": ["Word layout and graphics await a later authorized assembly stage.", "The low observed NL BEV customs unit value is disclosed and not economically resolved.", "Numerical checks do not establish causal tariff effects."],
    }
    (HERE / "chapter2_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in checks.items() if k != "sha256"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
