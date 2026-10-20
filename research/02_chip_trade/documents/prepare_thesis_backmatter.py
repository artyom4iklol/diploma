"""Prepare a deduplicated bibliography and appendices from saved evidence."""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent


def number(x, places=2):
    return f"{x:.{places}f}".replace("-", "−").replace(".", ",")


def interval(a, b, places=3):
    return f"[{number(a, places)}; {number(b, places)}]"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def one(rows, **keys):
    matches = [r for r in rows if all(r.get(k) == v for k, v in keys.items())]
    assert len(matches) == 1, keys
    return matches[0]


def main():
    master = {r["id"]: r for r in json.loads((HERE.parent / "literature/sources.json").read_text())["sources"]}
    sources = {}
    for chapter in (1, 2, 3):
        audit = json.loads((HERE / f"chapter{chapter}_source_audit.json").read_text())
        for source in audit["sources"]:
            sid = source["source_id"]
            if sid == "un_comtrade":
                sid = "un_comtrade_monthly_2017_2024"
            if sid not in sources:
                sources[sid] = {"source_id": sid, "citation": source["citation"], "chapters": [], "evidence_basis": []}
            row = sources[sid]
            row["chapters"].append(chapter)
            basis = source.get("evidence_basis", source.get("access_status"))
            if basis and basis not in row["evidence_basis"]:
                row["evidence_basis"].append(basis)
            consulted = source.get("consulted_citation") or master.get(sid, {}).get("consulted_citation")
            if consulted:
                row["consulted_citation"] = consulted
            if sid == "un_comtrade_monthly_2017_2024":
                row["citation"] = "United Nations Statistics Division. UN Comtrade Database. Месячный экспорт Японии и Республики Корея за 2017–2024 годы. Выгрузка 16 октября 2026 года."
            doi = master.get(sid, {}).get("doi")
            if doi:
                row["doi"] = doi

    bibliography = ["# Список использованных источников", ""]
    ordered = sorted(sources.values(), key=lambda r: r["citation"].casefold())
    for i, row in enumerate(ordered, 1):
        citation = row["citation"]
        if row.get("doi") and row["doi"] not in citation:
            citation += " DOI: " + row["doi"] + "."
        consulted = row.get("consulted_citation")
        if consulted and consulted != row["citation"]:
            citation += " Использованная версия: " + consulted
        row["number"] = i
        row["formatted"] = citation
        bibliography += [f"{i}. {citation}", ""]
    assert len(ordered) == 36
    (HERE / "thesis_bibliography.md").write_text("\n".join(bibliography).rstrip() + "\n")
    (HERE / "thesis_bibliography.json").write_text(json.dumps({"source_count": len(ordered), "sources": ordered}, ensure_ascii=False, indent=2) + "\n")

    base = (HERE / "chapter2_appendices.md").read_text()
    base = base.replace("# Приложения ко второй главе", "# Приложения", 1)
    before_e, old_e = base.split("## Приложение Е Воспроизводимость расчетов", 1)
    reproducibility = """## Приложение Е Воспроизводимость расчетов

Основная панель, исходные ответы, протокол и программы сохранены в репозитории artyom4iklol/diploma в разделе research/02_chip_trade/risk_extension. Параметры основного расчета зафиксированы в monthly_analysis_protocol.md. Программа analyze_monthly.py формирует условные индексы и интервалы; post_estimation/diagnose_results.py — дополнительные разложения. Результаты основной модели соответствуют полной панели 2017–2024 годов, полученной 16 октября 2026 года.

Проверены совпадение дисперсии индекса с квадратичной формой, сложение товарного и географического вкладов, сложение детальных атрибуций и согласованность исходных сумм. Описательные данные рисунков и таблиц подготовлены из сохраненной панели. Неопределенные темпы в недоступных вариантах чувствительности не заменялись нулями.

Расчетные материалы второй главы сохранены в chapter2_evidence.json. Товарные сценарии третьей главы воспроизводятся программой prepare_chapter3_evidence.py; параметры заданы в chapter3_scenario_protocol.md, результаты — в chapter3_evidence.json. Дополнительное географическое сравнение воспроизводится программой prepare_chapter3_markets.py по протоколу chapter3_market_protocol.md; результаты находятся в chapter3_market_evidence.json. Эти файлы размещены в каталоге research/02_chip_trade/documents.

Для основного расчета и сценариев используются 1 999 повторов парного циркулярного блочного бутстрепа. Основная длина блока составляет 12 месяцев, дополнительная — 6 месяцев. В основном расчете начальное состояние генератора случайных чисел равно 20261016, в сценариях третьей главы — 20261019. Веса, товарная сетка и набор направлений фиксируются в соответствии с протоколами. В географическом сравнении одновременные интервалы строятся отдельно для восьми направлений каждого экспортера.

Файлы доказательной базы содержат контрольные суммы исходных материалов. Проверки данных, структурных тождеств и соответствия текста расчетам сохранены рядом с результатами. Единый документ формируется программой build_thesis.py; библиография и приложения — программой prepare_thesis_backmatter.py. Сборка текста не изменяет исходную панель и не переоценивает основную модель.
"""
    sections = [before_e.rstrip(), reproducibility.strip()]
    scenario = json.loads((HERE / "chapter3_evidence.json").read_text())
    sections += ["## Приложение Ж Чувствительность товарных сценариев", "Сценарии изменяют долю памяти относительно структуры 2024 года. География внутри товаров и взаимные пропорции трех остальных категорий сохраняются. В таблицах сопоставлены разность стандартных отклонений на полной истории 2018–2024 годов, ее поточечный 95%-й интервал при шестимесячном блоке и точечные разности на двух отдельных исторических окнах. Основные интервалы при блоке 12 месяцев приведены в таблицах 3.4 и 3.5."]
    for i, (reporter, country) in enumerate([(392, "Япония"), (410, "Республика Корея")], 1):
        rows = []
        for shift in scenario["shifts_pp"]:
            value = one(scenario["scenarios"], reporter=reporter, shift_pp=shift)
            ci = one(scenario["paired_intervals"], reporter=reporter, shift_pp=shift, block_months=6)
            early = one(scenario["windows"], reporter=reporter, shift_pp=shift, window="2018–2020")
            late = one(scenario["windows"], reporter=reporter, shift_pp=shift, window="2021–2024")
            rows.append([number(shift, 1), number(value["delta_sd_pp"]), interval(ci["ci_low"], ci["ci_high"]), number(early["delta_sd_pp"]), number(late["delta_sd_pp"])])
        sections += [f"**Таблица Ж.{i} — {country}**", table(["Сдвиг доли, п.п.", "ΔSD 2018–2024, п.п.", "95%-й интервал, блок 6 мес.", "ΔSD 2018–2020, п.п.", "ΔSD 2021–2024, п.п."], rows), "Источник: расчеты автора по UN Comtrade."]
    sections += ["Примечание: в обоих окнах сохраняются одни и те же веса 2024 года и сценарные сдвиги; для окон отдельные интервалы не рассчитывались. Различия между ними характеризуют чувствительность к истории темпов и не являются независимой проверкой прогноза. Дополнительный разряд интервалов позволяет сохранить знак малых значений."]

    markets = json.loads((HERE / "chapter3_market_evidence.json").read_text())
    sections += ["## Приложение З Дополнительные результаты географических сценариев", "Во всех сценариях стоимость дополнительных поставок равна 1% экспорта четырех категорий за 2024 год. Добавление распределяется между тремя категориями вне памяти пропорционально их исходным долям. Для каждого направления оценивается разность с базовым размещением той же добавки по существующей географии внутри товаров. Все альтернативы одного экспортера имеют одинаковые товарные пропорции и общий объем; меняется размещение дополнительной корзины."]
    for i, (reporter, country) in enumerate([(392, "Япония"), (410, "Республика Корея")], 1):
        rows = []
        for value in [r for r in markets["rows"] if r["reporter"] == reporter]:
            early = one(markets["windows"], reporter=reporter, partner=value["partner"], window="2018–2020")
            late = one(markets["windows"], reporter=reporter, partner=value["partner"], window="2021–2024")
            rows.append([value["partner_name"], number(early["delta_vs_reference_pp"], 3), number(late["delta_vs_reference_pp"], 3), interval(value["family_ci_low_b6"], value["family_ci_high_b6"]), number(value["max_required_cell_growth_pct"], 1), str(value["max_required_cell_good"])])
        sections += [f"**Таблица З.{i} — {country}**", table(["Направление", "ΔSD 2018–2020, п.п.", "ΔSD 2021–2024, п.п.", "Одновременный интервал, блок 6 мес.", "Макс. рост ячейки, %", "Код HS6"], rows), "Источник: расчеты автора по UN Comtrade."]
    sections += ["Примечание: одновременные 95%-е интервалы рассчитаны на полной истории 2018–2024 годов отдельно для восьми направлений каждого экспортера и являются приближенными. Для отдельных окон приведены только точечные оценки. Максимальный рост ячейки — наибольшее относительное увеличение стоимости одного из трех товаров на данном направлении, необходимое для размещения всей дополнительной корзины; рядом указан соответствующий код. Этот показатель описывает масштаб сценария и не подтверждает наличие спроса. Other Asia, nes сохраняет наименование категории UN Comtrade. Остаточная группа не рассматривается как отдельный рынок для размещения добавки."]
    (HERE / "thesis_appendices.md").write_text("\n\n".join(sections).rstrip() + "\n")
    print(json.dumps({"sources": len(ordered), "appendices": 8, "appendix_tables": 11}, ensure_ascii=False))


if __name__ == "__main__":
    main()
