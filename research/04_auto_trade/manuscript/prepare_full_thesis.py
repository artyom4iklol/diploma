"""Assemble the complete manuscript, actual bibliography and appendices."""
from pathlib import Path
import json
import re
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
TITLE = "Географическая концентрация и товарная адаптация поставок новых электромобилей и бензиновых гибридов из Китая в ЕС"


def strip_definitions(text):
    return re.sub(r"^\[\^[^\]]+\]:.*(?:\n[ \t]+.*)*", "", text, flags=re.M).strip()


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(map(str, row)) + " |" for row in rows)])


def number(x, n=0):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def main():
    chapters = {}; notes = {}
    for n in [1, 2, 3]:
        chapters[n] = strip_definitions((HERE / f"chapter{n}_content.md").read_text())
        source = json.loads((HERE / f"chapter{n}_sources.json").read_text())["citations"]
        for key, value in source.items():
            assert key not in notes
            notes[key] = value
    intro_notes = {
        "I_CONTEXT": {"source_ids": ["C2O11", "O04", "O05"], "text": notes["C2LAUNCH"]["text"] + " " + notes["C2DEFINITIVE"]["text"]},
        "I_THEORY": {"source_ids": ["S32", "S14"], "text": notes["MELITZ"]["text"] + " " + notes["HM17"]["text"]},
        "I_RESEARCH": {"source_ids": ["S01", "S02", "S08"], "text": notes["KE"]["text"] + " " + notes["DOU"]["text"] + " " + notes["PORTFOLIO"]["text"]},
        "I_DATA": {"source_ids": ["O01", "O08"], "text": notes["C2DATA"]["text"] + " " + notes["C3ACEA"]["text"]},
        "I_METHOD": {"source_ids": ["S21", "S23"], "text": notes["PPML"]["text"] + " " + notes["DECOMPOSITION"]["text"]},
    }
    notes.update(intro_notes)
    (HERE / "introduction_sources.json").write_text(json.dumps(intro_notes, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    split = chapters[2].index("# Приложение А.")
    main2 = chapters[2][:split].strip()
    # Place the full-height map before its detailed discussion, avoiding a stranded
    # paragraph above a page-sized illustration in the compiled thesis.
    main2, moved = re.subn(r'(В 2025 году крупнейшим направлением[^\n]+)\n\n(<!-- BEGIN FIG G07_geography -->.*?<!-- END FIG G07_geography -->)', r'\2\n\n\1', main2, flags=re.S)
    assert moved == 1
    appendix_a = chapters[2][split:].strip()
    scenario = pd.read_csv(ROOT / "results/chapter3_application/scenario_transfer.csv")
    rows = [[x.category, number(x.alpha*100), number(x.rho*100), number(x.exposed_quantity, 1), number(x.remaining_quantity, 1), number(x.remaining_share_pct, 2)] for x in scenario.itertuples()]
    appendix_b = "# Приложение Б Сценарные и исторические материалы рекомендательной главы\n\n"
    appendix_b += "## Б.1 Полный набор сценарных сочетаний\n\nТаблица Б.1 — Условная экспозиция и неперенесённая часть\n\n"
    appendix_b += table(["Категория", "α, %", "ρ, %", "Затронутый объём, шт.", "Неперенесённый объём, шт.", "Доля категории, %"], rows)
    appendix_b += "\n\nИсточник: расчёты автора по Eurostat Comext. Все 18 сочетаний сохранены; α и ρ являются заданными условиями, а дробные единицы — расчётными величинами.[^C3EXPOSURE]\n\n"
    h = pd.read_csv(ROOT / "results/chapter3_application/historical_quarter_changes.csv")
    rows = [[x.category, x.quarter, number(x.BE_NL_change), number(x.other25_change), number(x.total_change)] for x in h.itertuples()]
    appendix_b += "## Б.2 Полный набор квартальных сопоставлений\n\nТаблица Б.2 — Изменение количества относительно того же квартала предыдущего года\n\n"
    appendix_b += table(["Категория", "Квартал", "Изменение BE/NL, шт.", "Изменение остальных стран, шт.", "Общее изменение, шт."], rows)
    appendix_b += "\n\nИсточник: расчёты автора по Eurostat Comext. Приведены все 48 сопоставлений, включая случаи роста пары. Совместное изменение не устанавливает перенос партий между странами.[^C3HISTORY]\n"
    appendix_c = """# Приложение В Паспорт данных и контрольные проверки

## В.1 Охват и версия исходной статистики

В исследовании используется месячный импорт за январь 2021 — декабрь 2025 года из Eurostat Comext DS-045409. Постоянный состав стран — ЕС-27. Происхождение CN означает Китай; REST рассчитывается как внешний импорт за вычетом CN в каждой сопоставимой ячейке. Коды новых автомобилей: 87038010, 87036010 и 87034010. Показатели: SUPPLEMENTARY_QUANTITY и VALUE_IN_EUROS. Дата выгрузки — 26 октября 2026 года, обновление источника — 16 октября 2026 года.

Непосредственно опубликованное значение и восстановленный нуль сохраняют разные статусы. Восстановление допускается при точном равенстве европейского агрегата и суммы всех опубликованных национальных значений, неотрицательности и отсутствии ограничивающих флагов. Оставшиеся неопределённые значения не заменяются нулями. Ключ потока: страна, происхождение, товарный код и месяц.[^C2AUDIT]

Таблица В.1 — Основные результаты контроля исходной панели и вычислений

| Проверка | Результат | Значение для интерпретации |
| --- | --- | --- |
| Основная сетка CN/REST | 9 720 потоков | Одинаковый охват двух показателей |
| Неопределённые показатели | 0 | Все значения имеют установленный статус |
| Отрицательные остатки REST | 0 | Остаточное происхождение не требует исправления знака |
| Совпадение CN + REST с внешним импортом | Точное | Одинаковый знаменатель сравнения |
| Предпочтительная PPML | 8 500 строк | Удалены нулевые группы; положительная торговля сохранена |
| Информативное парное представление | 4 118 пар и 264 одиночные строки | Состав информации отличается от числа исходных строк |
| Общие и групповые разложения HHI | 4 общих и 12 групповых; ошибка ниже 10⁻¹² | Компоненты складываются до округления |
| Повторные взвешенные оценки | 398 успешных, 199 на исход | Сохранён полный предусмотренный набор |
| Сценарные сочетания переноса | 18; границы и сложение соблюдены | Условия заданы, поведение не оценивалось |
| Квартальные сопоставления | 48; 20 случаев сокращения BE/NL | Полный ретроспективный набор |

Источник: авторские проверки сохранённых данных и результатов.

## В.2 Дополнительные сведения и воспроизведение

Первичные регистрации новых BEV в ЕС-27 взяты из выпуска ACEA от 27 января 2026 года, с. 4. Они относятся ко всем происхождениям и используются как отдельный рыночный ряд. Таможенный импорт не делится на регистрации для получения доли марки. Последующие документы Европейской комиссии 2026 года образуют контекст рекомендательной главы и не включаются в оценочное окно 2021–2025.

Воспроизведение предполагает последовательную проверку версии исходного ответа, построение панели, структурные расчёты, оценивание фиксированной спецификации и подготовку иллюстраций. Контрольные суммы позволяют установить совпадение файлов; они не устраняют возможные ошибки первоначальных деклараций или ограничения сравнительной конструкции. Материалы исследования и код доступны в репозитории artyom4iklol/diploma, раздел research/04_auto_trade. Состояние данных и результатов, использованное для итогового текста, зафиксировано 28 октября 2026 года.
"""
    bibliography = make_bibliography(notes)
    (HERE / "appendices.md").write_text(appendix_a + "\n\n" + appendix_b + "\n\n" + appendix_c + "\n", encoding="utf8")
    chapter3_full, shortened = re.subn(r'Порядок внедрения объединяет эталонную версию данных[^\n]+', 'Порядок внедрения включает эталонную версию данных, пилотный разбор и регулярное обновление с журналом пересмотров. Контроль основан на определённости наблюдений, воспроизводимости, своевременности и завершённости проверки. Результат — согласованная процедура применения выводов; экономия и предотвращённые потери требуют отдельной оценки на данных организации.', chapters[3])
    assert shortened == 1
    content = "\n\n".join([(HERE / "introduction.md").read_text().strip(), chapters[1], main2, chapter3_full, (HERE / "conclusion.md").read_text().strip(), bibliography, appendix_a, appendix_b, appendix_c])
    used = re.findall(r"\[\^([^\]]+)\]", content)
    assert set(used) <= set(notes), set(used) - set(notes)
    keys = list(dict.fromkeys(used))
    definitions = "\n".join(f"[^{key}]: {notes[key]['text']}" for key in keys)
    (HERE / "full_thesis_content.md").write_text(content + "\n\n" + definitions + "\n", encoding="utf8")
    (HERE / "full_thesis_sources.json").write_text(json.dumps({"date": "2026-10-28", "citations": {k: notes[k] for k in keys}, "footnote_occurrences": len(used), "distinct_note_definitions": len(keys)}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    checks = {"date": "2026-10-28", "chapters": 3, "sections": 14, "introduction_tasks": 8, "conclusion": True, "appendices": 3,
              "footnote_occurrences": len(used), "bibliography_entries": 34, "source_ids": sorted({x for k in keys for x in notes[k]["source_ids"] if x != "AUTHOR_CALCULATIONS"}),
              "chapter_sha256": {f"chapter{n}_content.md": hashlib.sha256((HERE / f"chapter{n}_content.md").read_bytes()).hexdigest() for n in [1, 2, 3]}}
    (HERE / "full_thesis_content_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(checks, ensure_ascii=False))


def make_bibliography(notes):
    scientific = {
        "S01": "Ke Y. EU Countervailing Duties and Chinese BEV Trade Flows: Descriptive Evidence from a Difference-in-Differences Analysis. Bachelor thesis. Umeå University, 2026.",
        "S02": "Dou H. et al. Distributional impacts of EU tariffs on Chinese electric vehicles across European markets // Nature Energy. Accepted author version. 2026. DOI: 10.1038/s41560-026-02105-7.",
        "S03": "Wingender P., Yao J., Zymek R., Carton B., Cerdeiro D., Weber A. Europe’s Shift to EVs Amid Intensifying Global Competition. IMF Working Paper 24/218. 2024.",
        "S04": "Coffin D., Crotty P., Walling J., Yuan W. J. J. The Impact of Changes in Trade Policies on the Electric Vehicle (EV) Sector — A CGE Analysis. USITC Economics Working Paper 2024–05–A. 2024.",
        "S05": "Minondo A. How exporters neutralised an increase in tariffs // The World Economy. 2024. Vol. 47, no. 3. P. 1274–1296. DOI: 10.1111/twec.13492.",
        "S08": "Barwick P. J., Collison J., Goldberg P. K., Li S., Wang Y. From Trade War to Green Transition: Optimal Electric Vehicle Tariffs with Revenue-Funded Subsidies. NBER Working Paper 35334. June 2026. DOI: 10.3386/w35334.",
        "S09": "Dou H., Hao H., Mai L., Liu B., Liu M., Sun X. Observed constrained expansion and diminished affordability under the EU’s tariffs on Chinese electric vehicles // Joule. 2026. Vol. 10, no. 6. Article 102486. DOI: 10.1016/j.joule.2026.102486.",
        "S12": "Bickenbach F., Dohse D., Langhammer R. J., Liu W.-H. EU Concerns About Chinese Subsidies: What the Evidence Suggests // Intereconomics. 2024. Vol. 59, no. 4. P. 214–221. DOI: 10.2478/ie-2024-0044.",
        "S14": "Head K., Mayer T. Brands in Motion: How frictions shape multinational production. Banque de France Working Paper 629. May 2017.",
        "S15": "Fajgelbaum P., Goldberg P., Kennedy P., Khandelwal A., Taglioni D. The US-China Trade War and Global Reallocations. NBER Working Paper 29562. Revised December 2023.",
        "S16": "Amiti M., Redding S. J., Weinstein D. E. The Impact of the 2018 Tariffs on Prices and Welfare // Journal of Economic Perspectives. 2019. Vol. 33, no. 4. P. 187–210. DOI: 10.1257/jep.33.4.187.",
        "S17": "Cavallo A., Gopinath G., Neiman B., Tang J. Tariff Pass-Through at the Border and at the Store: Evidence from US Trade Policy. NBER Working Paper 26396. 2019.",
        "S20": "Balteanu I., Moreno M., Viani F. Flooded by China? Trade diversion due to US tariffs during Trump’s first mandate. Banco de España Working Paper 2634. October 2026. DOI: 10.53479/44545.",
        "S21": "Santos Silva J. M. C., Tenreyro S. The Log of Gravity // Review of Economics and Statistics. 2006. Vol. 88, no. 4. P. 641–658. DOI: 10.1162/rest.88.4.641.",
        "S23": "Shorrocks A. F. Decomposition Procedures for Distributional Analysis: A Unified Framework Based on the Shapley Value. First draft. June 1999.",
        "S31": "Feenstra R. C., Romalis J. International Prices and Endogenous Quality. NBER Working Paper 18314. 2012.",
        "S32": "Melitz M. J. The Impact of Trade on Intra-Industry Reallocations and Aggregate Industry Productivity // Econometrica. 2003. Vol. 71, no. 6. P. 1695–1725. DOI: 10.1111/1468-0262.00467.",
    }
    catalog = {x["id"]: x for x in json.loads((ROOT / "literature/expanded_catalog.json").read_text())}
    read = {x["id"]: x for x in json.loads((ROOT / "writing/source_use_register.json").read_text())["scientific_and_student_works"]}
    official = {x["id"]: x for x in json.loads((ROOT / "literature/official_sources_catalog.json").read_text())}
    aux = {x["id"]: x for x in json.loads((HERE / "chapter1_sources.json").read_text())["records"] if x["id"].startswith("A")}
    ids = {x for v in notes.values() for x in v["source_ids"] if x != "AUTHOR_CALCULATIONS"}
    entries = []
    for ident in sorted(ids):
        if ident in scientific:
            entry = scientific[ident]
            url = read.get(ident, {}).get("download_url") or catalog[ident]["primary_url"]
        elif ident in official:
            x = official[ident]; url = x["url"]
            titles = {"O01": "Comext DS-045409. International trade in goods — detailed data. Месячная статистика 2021–2025; выгрузка 26.10.2026. API guide",
                      "O04": "Commission Implementing Regulation (EU) 2024/2754 of 29 October 2024",
                      "O05": "EU Commission imposes countervailing duties on imports of battery electric vehicles (BEVs) from China. Access2Markets. 12.12.2024",
                      "O06": "Global EV Outlook 2025. Paris, 2025",
                      "O08": "New car registrations: +1.8% in 2025; battery-electric 17.4% market share. Press release car registrations December 2025. 27.01.2026",
                      "O09": "Commission issues Guidance Document on submission of price undertaking offers for battery electric vehicles from China. 12.01.2026",
                      "O10": "Joint Statement at the second meeting of the EU-China Trade and Investment Consultations. Beijing, 09.10.2026"}
            if ident == "O08": url = "https://www.acea.auto/files/Press_release_car_registrations_December_2025.pdf"
            entry = x["institution"] + ". " + titles.get(ident, x["title"]) + "."
        elif ident in aux:
            x = aux[ident]; entry = x["institution"] + ". " + x["title"] + "."; url = x["url"]
        elif ident in ["C2O11", "C2O12", "C2O13"]:
            x = next(v for v in notes.values() if v["source_ids"] == [ident])
            entry = x["text"].replace(" С. 1.", ""); url = x["urls"][0]
        else:
            raise ValueError(ident)
        date = "28.10.2026" if ident in ["O08", "O09", "O10"] else "27.10.2026"
        entry = re.sub(r"\s*\(дата обращения: [^)]+\)\.?", "", entry)
        entry = entry.rstrip(".") + ". URL: " + url + " (дата обращения: " + date + ")."
        entries.append({"id": ident, "text": entry})
    assert len(entries) == 34, len(entries)
    entries.sort(key=lambda x: x["text"].casefold())
    for n, x in enumerate(entries, 1): x["number"] = n
    (HERE / "full_bibliography.json").write_text(json.dumps({"date": "2026-10-28", "entries": entries, "basis": "Only used references; versions match actual chapter citations."}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    result = "# Список использованных источников\n\n" + "\n\n".join(f"{x['number']}. {x['text']}" for x in entries)
    (HERE / "bibliography.md").write_text(result + "\n", encoding="utf8")
    return result


if __name__ == "__main__":
    main()
