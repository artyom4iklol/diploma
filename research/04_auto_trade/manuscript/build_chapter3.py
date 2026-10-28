"""Assemble the complete recommendation chapter in Markdown; preserve chapters 1–2."""
from pathlib import Path
import hashlib
import json
import re
import build_chapter3_evidence as evidence
import extend_chapter3_evidence as extension

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TITLE = "Глава 3 Рекомендации по мониторингу и оценке товарной и географической адаптации поставок автомобилей из Китая в ЕС"


def main():
    evidence.main()
    extension.main()
    generated = json.loads((HERE / "chapter3_generated_tables.json").read_text())
    sections = [HERE / f"chapter3_{i}.md" for i in range(1, 5)] + [HERE / "chapter3_conclusions.md"]
    p = HERE / "chapter3_2.md"
    s = p.read_text()
    marked = "<!-- BEGIN AUTO T02 -->\n" + generated["T02"] + "\n<!-- END AUTO T02 -->"
    if "{{T02}}" in s:
        s = s.replace("{{T02}}", marked)
    else:
        s, count = re.subn(r"<!-- BEGIN AUTO T02 -->.*?<!-- END AUTO T02 -->", lambda _: marked, s, flags=re.S)
        assert count == 1
    p.write_text(s, encoding="utf8")
    extended = json.loads((HERE / "chapter3_extension_evidence.json").read_text())
    for filename, token, key in [("chapter3_2.md", "THISTORY", "T05"), ("chapter3_3.md", "TMARKET", "T06")]:
        path = HERE / filename; s = path.read_text()
        marked = f"<!-- BEGIN AUTO {token} -->\n" + extended["tables"][key] + f"\n<!-- END AUTO {token} -->"
        if "{{" + token + "}}" in s:
            s = s.replace("{{" + token + "}}", marked)
        else:
            s, count = re.subn(rf"<!-- BEGIN AUTO {token} -->.*?<!-- END AUTO {token} -->", lambda _: marked, s, flags=re.S)
            assert count == 1
        path.write_text(s, encoding="utf8")
    placements = [
        ("chapter3_1.md", "G01", "G01_monitoring", "Последовательность совместного разбора торговых показателей", "Схема предложена автором; ветви показывают разные направления проверки."),
        ("chapter3_2.md", "G02", "G02_exposure", "Условная географическая экспозиция при двух масштабах затруднения", "Структура 2025 года; перенос отсутствует. Параметры 10 и 25% заданы для иллюстрации."),
        ("chapter3_2.md", "G03", "G03_history", "Исторические сочетания квартальных изменений BE/NL и остальных стран", "Показаны все 20 случаев сокращения пары относительно того же квартала предыдущего года; линия — равенство прироста вне пары её сокращению. Совместное изменение не устанавливает перенос партий."),
        ("chapter3_4.md", "G04", "G04_implementation", "Предлагаемое распределение действий по этапам и ответственным", "Матрица разработана автором; фактическое распределение ролей определяется организацией."),
    ]
    for i, (name, token, image, title, explanation) in enumerate(placements, 1):
        path = HERE / name
        s = path.read_text()
        assert (HERE / f"chapter3_figures/{image}.svg").exists()
        block = f"<!-- BEGIN FIG {token} -->\n![{title}](chapter3_figures/{image}.svg)\n\nРисунок 3.{i} — {title}\n\nИсточник: составлено автором. {explanation}\n<!-- END FIG {token} -->"
        if "{{" + token + "}}" in s:
            s = s.replace("{{" + token + "}}", block)
        else:
            s, count = re.subn(rf"<!-- BEGIN FIG {token} -->.*?<!-- END FIG {token} -->", lambda _: block, s, flags=re.S)
            assert count == 1
        path.write_text(s, encoding="utf8")

    old = json.loads((HERE / "chapter1_sources.json").read_text())["citations"]
    c2 = json.loads((HERE / "chapter2_sources.json").read_text())["citations"]
    notes = {}

    def note(key, ids, text, scope, files=(), urls=(), kind="external"):
        notes[key] = {"source_ids": ids, "text": text, "supported_scope": scope, "kind": kind, "source_files": list(files), "urls": list(urls)}

    def copy(key, prior, scope):
        v = old[prior]
        note(key, v["source_ids"], v["text"], scope)

    copy("C3METADATA", "ESTATDEF", "Определения статистического охвата; паспорт и процедура мониторинга предложены автором.")
    copy("C3ROTTERDAM", "ROTTERDAM", "Страна учёта не обязательно совпадает с конечным рынком и физическим маршрутом.")
    copy("C3QUALITY", "QUALITY", "Средняя стоимость и качество; прочитано введение WP 2012 года, цена неизменного качества не оценивалась.")
    copy("C3BARWICK", "PORTFOLIO", "Учет спроса и решений многопродуктовых фирм; параметры не переносятся. Прочитаны разделы WP 35334, а не только метаданные.")
    copy("C3DOU", "DOU", "Неоднородность рынков и сценарные предпосылки по принятой авторской версии Nature Energy; не недоступный полный текст Joule.")
    note("C3MACRO", ["S03", "S04"], old["IMF"]["text"] + " " + old["USITC"]["text"], "Необходимость более широких производственных данных для отраслевых последствий; прочитаны указанные методические разделы.")
    v = c2["C2DEFINITIVE"]
    note("C3SCOPE", v["source_ids"], v["text"], "Исторический ex-CN/TARIC-охват и более широкий CN8; конкретное текущее применение требует соответствующей редакции.", urls=v["urls"])
    note("C3GUIDANCE", ["O09"], "European Commission. Commission issues Guidance Document on submission of price undertaking offers for battery electric vehicles from China. Официальное сообщение от 12.01.2026 (дата обращения: 28.10.2026).", "Проверено официальное сообщение о содержании предложений. Полный текст связанного руководства в данном шаге не представлен прочитанным.", urls=["https://policy.trade.ec.europa.eu/news/commission-issues-guidance-document-submission-price-undertaking-offers-battery-electric-vehicles-2026-01-12_en"])
    note("C3JOINT", ["O10"], "European Commission. Joint Statement at the second meeting of the EU-China Trade and Investment Consultations. Beijing, 09.10.2026. Annex, points 2–4 (дата обращения: 28.10.2026).", "Последующий контекст: понимание по гибридам и процедуры обязательств BEV; заявление не устанавливает численную квоту и дату её применения.", urls=["https://ec.europa.eu/commission/presscorner/api/files/document/print/en/statement_26_2122/STATEMENT_26_2122_EN.pdf"])
    note("C3ACEA", ["O08"], "ACEA. New car registrations: +1.8% in 2025; battery-electric 17.4% market share. Press release car registrations December 2025, 27.01.2026. С. 4, строка European Union (дата обращения: 28.10.2026).", "Первичная таблица регистраций BEV ЕС-27 за 2024/2025. Совокупности отличаются от импорта по происхождению; их отношение не представлено рыночной долей.", files=["data/chapter3_public/acea_eu_bev_registrations.csv", "data/chapter3_public/acea_source.json"], urls=["https://www.acea.auto/files/Press_release_car_registrations_December_2025.pdf"])
    own = {
        "C3DATA": ("Eurostat. Comext DS-045409. Выгрузка 26.10.2026, январь 2021 — декабрь 2025 года, три кода новых автомобилей. Авторский аудит и расчёты главы 2.", ["results/full/data_audit.json", "results/full/panel.csv", "manuscript/chapter3_evidence.json"]),
        "C3GEOGRAPHY": ("Eurostat Comext; авторские разложения концентрации, базы 2023/2024 и конечный 2025 год. Результаты рассмотрены в параграфе 2.4.", ["results/full/entry_concentration.csv", "results/geography_focus/pooled_HHI_product_geography.csv"]),
        "C3VALUATION": ("Eurostat Comext; авторская независимая проверка 24 месячных значений NL BEV и географическая чувствительность без NL/BE_NL, 27.10.2026.", ["results/chapter2_revision/valuation_diagnostic.json"]),
        "C3EXPOSURE": ("Расчёты автора по таможенно учтённым количествам 2025 года: шесть исходных сценариев и 18 комбинаций условного переноса. Параметры α и ρ заданы для иллюстрации; вероятности и фактическая способность переноса не оценены.", ["results/augmented/clearance_jurisdiction_exposure.csv", "results/chapter3_application/scenario_transfer.csv"]),
        "C3MODEL": ("Авторская предпочтительная PPML CN/REST по количеству и стоимости, результаты и чувствительности второй главы. Период 2021–2025; базовая технология BEV.", ["results/augmented/rest_preferred_quantity.json", "results/augmented/rest_preferred_value.json", "results/augmented/paired_block_summary.json", "results/augmented/coefficients.csv"]),
        "C3HISTORY": ("Eurostat Comext; авторский ретроспективный разбор всех 48 годовых квартальных сопоставлений 2022–2025 годов и 20 случаев сокращения потока BE/NL. Совместные изменения не являются оценкой перенаправления или свободной мощности.", ["results/chapter3_application/historical_quarter_changes.csv", "results/chapter3_application/historical_quarter_summary.csv", "manuscript/chapter3_extension_evidence.json"]),
    }
    for key, (text, paths) in own.items():
        note(key, ["O01", "AUTHOR_CALCULATIONS"], text, "Собственные расчёты и прикладные выводы; не внешний причинный результат.", files=paths, kind="own_calculation")
    for value in notes.values():
        value["source_sha256"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in value["source_files"]}

    body = "# " + TITLE + "\n\n" + "\n\n".join(p.read_text().strip() for p in sections) + "\n"
    keys = re.findall(r"\[\^([^\]]+)\]", body); unique = list(dict.fromkeys(keys))
    assert set(unique) == set(notes)
    assert "{{" not in body and "\ufffd" not in body
    assert len(re.findall(r"^## 3\.[1-4] ", body, re.M)) == 4
    assert re.findall(r"^Таблица (3\.[1-6]) —", body, re.M) == ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6"]
    assert len(re.findall(r"^Рисунок 3\.[1-4] —", body, re.M)) == 4
    assert body.count(r"\[") == body.count(r"\]") == 3
    assert not re.search(r"\b(?:TODO|TBD|FIXME)\b", body)
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body):
        assert (HERE / target).exists()
    manifest = json.loads((HERE / "chapter3_figures/figure_manifest.json").read_text())
    assert len(manifest["figures"]) == 4
    for figure in manifest["figures"]:
        for path, expected in figure["source_sha256"].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        assert hashlib.sha256((HERE / "chapter3_figures" / (figure["id"] + ".svg")).read_bytes()).hexdigest() == figure["svg_sha256"]
    definitions = "\n".join(f"[^{key}]: {notes[key]['text']}" for key in unique)
    (HERE / "chapter3_content.md").write_text(body + "\n" + definitions + "\n", encoding="utf8")
    (HERE / "chapter3_sources.json").write_text(json.dumps({"date": "2026-10-28", "citations": notes, "first_use_order": unique, "footnote_occurrences": len(keys)}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    external = [notes[k]["text"] for k in unique if notes[k]["kind"] == "external"]
    (HERE / "chapter3_bibliography.md").write_text("# Источники третьей главы\n\n" + "\n\n".join(f"{i}. {v}" for i, v in enumerate(external, 1)) + "\n\nСобственные расчёты, их источники и контрольные суммы перечислены в chapter3_sources.json. Даты документов 2026 года относятся к последующему контексту, отдельно от панели 2021–2025.\n", encoding="utf8")
    checks = {"date": "2026-10-28", "format": "Markdown", "chapter_complete": True,
              "sections": 4, "conclusions": True, "tables": 6, "figures": 4, "scenario_combinations": 18,
              "historical_quarter_comparisons": 48, "historical_pair_declines": 20, "public_registration_totals": 2,
              "all_citations_resolved": True, "distinct_footnote_definitions": len(unique), "footnote_occurrences": len(keys),
              "cyrillic_words_including_tables_captions": len(re.findall(r"[А-Яа-яЁё]+(?:[-–][А-Яа-яЁё]+)*", body)),
              "figure_source_and_svg_hashes_verified": True, "regressions_refitted": False,
              "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sections, HERE / "chapter3_content.md"]},
              "limits": ["Scenario inputs are author-specified conditions, not probabilities or fitted behavior.", "The chapter proposes a procedure; actual operational adoption or realized financial benefits are not claimed.", "Word layout awaits assembly of the complete thesis."]}
    (HERE / "chapter3_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in checks.items() if k != "sha256"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
