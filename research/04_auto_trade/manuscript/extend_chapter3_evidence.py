"""Observed historical co-movements and a separately defined ACEA market context."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "results/chapter3_application"
PUBLIC = ROOT / "data/chapter3_public"


def number(x, n=0):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(map(str, row)) + " |" for row in rows)])


def main():
    OUT.mkdir(exist_ok=True); PUBLIC.mkdir(exist_ok=True)
    # Two manually transcribed EU BEV totals from the primary PDF, p. 4.
    # Only EU totals are used; no import/registration ratio is called a market share.
    acea = pd.DataFrame([
        {"year": 2024, "geography": "EU27", "technology": "BEV", "new_registrations": 1447631},
        {"year": 2025, "geography": "EU27", "technology": "BEV", "new_registrations": 1880370},
    ])
    acea.to_csv(PUBLIC / "acea_eu_bev_registrations.csv", index=False, lineterminator="\n")
    provenance = {
        "source": "ACEA", "title": "Press release car registrations December 2025", "published_on": "2026-01-27", "checked_on": "2026-10-28",
        "pdf_url": "https://www.acea.auto/files/Press_release_car_registrations_December_2025.pdf", "page": 4,
        "web_url": "https://www.acea.auto/pc-registrations/new-car-registrations-1-8-in-2025-battery-electric-17-4-market-share/",
        "extraction": "Two EU BEV totals manually transcribed from primary PDF and checked against EU annual table; 2025 total also agrees with official announcement.",
        "scope": "New BEV registrations in EU27, all origins and brands; not China-origin imports. Publication warns current-year data are provisional.",
        "limitations": "Year/version fixed to the cited release; no current-vintage registration history or model-level China-origin matching is claimed."
    }
    (PUBLIC / "acea_source.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    p = pd.read_csv(ROOT / "results/full/panel.csv")
    p = p[(p.origin == "CN") & (p.reporter != "EU27_2020")].copy()
    p["quarter"] = pd.PeriodIndex(p.month, freq="M").asfreq("Q")
    p["group"] = p.reporter.isin(["BE", "NL"]).map({True: "BE_NL", False: "other25"})
    q = p.groupby(["category", "group", "quarter"]).quantity.sum().unstack("group")
    all_rows = []; summaries = []
    for cat in ["BEV", "PHEV", "HEV"]:
        d = q.loc[cat].sort_index().copy()
        for col in ["BE_NL", "other25"]:
            d[col + "_lag4"] = d[col].shift(4)
            d[col + "_change"] = d[col] - d[col + "_lag4"]
        d = d[d.index >= pd.Period("2022Q1")]
        assert len(d) == 16 and d[["BE_NL_change", "other25_change"]].notna().all().all()
        d["total_change"] = d.BE_NL_change + d.other25_change
        for quarter, row in d.iterrows():
            decline = row.BE_NL_change < 0
            group = "no_pair_decline"
            if decline:
                group = "no_growth_outside" if row.other25_change <= 0 else ("outside_growth_smaller" if row.other25_change < -row.BE_NL_change else "outside_growth_at_least_decline")
                assert row.BE_NL_lag4 > 0
            all_rows.append({"category": cat, "quarter": str(quarter), **{k: float(row[k]) for k in d.columns},
                             "pair_decline": bool(decline), "pair_decline_pct": float(-row.BE_NL_change / row.BE_NL_lag4 * 100) if decline else None,
                             "co_movement_class": group})
        declines = [x for x in all_rows if x["category"] == cat and x["pair_decline"]]
        summaries.append({"category": cat, "comparisons": len(d), "pair_declines": len(declines),
                          "no_growth_outside": sum(x["co_movement_class"] == "no_growth_outside" for x in declines),
                          "outside_growth_smaller": sum(x["co_movement_class"] == "outside_growth_smaller" for x in declines),
                          "outside_growth_at_least_decline": sum(x["co_movement_class"] == "outside_growth_at_least_decline" for x in declines),
                          "min_observed_decline_pct": min(x["pair_decline_pct"] for x in declines),
                          "max_observed_decline_pct": max(x["pair_decline_pct"] for x in declines)})
    history = pd.DataFrame(all_rows)
    assert len(history) == 48 and history.pair_decline.sum() == 20
    for row in summaries:
        assert row["pair_declines"] == row["no_growth_outside"] + row["outside_growth_smaller"] + row["outside_growth_at_least_decline"]
    history.to_csv(OUT / "historical_quarter_changes.csv", index=False, lineterminator="\n")
    pd.DataFrame(summaries).to_csv(OUT / "historical_quarter_summary.csv", index=False, lineterminator="\n")
    # Independent annual cross-check for the added context.
    annual = pd.read_csv(ROOT / "results/full/annual_eu_flows.csv")
    cn = annual[(annual.origin == "CN") & (annual.category == "BEV")].set_index("year")
    regs = acea.set_index("year").new_registrations
    comparisons = [
        {"series": "CN_BEV_customs_imports_EU27", "2024": int(cn.loc[2024, "quantity"]), "2025": int(cn.loc[2025, "quantity"]), "growth_pct": float((cn.loc[2025, "quantity"] / cn.loc[2024, "quantity"] - 1) * 100)},
        {"series": "all_origin_BEV_registrations_EU27", "2024": int(regs.loc[2024]), "2025": int(regs.loc[2025]), "growth_pct": float((regs.loc[2025] / regs.loc[2024] - 1) * 100)}]
    t5 = table(["Категория", "Сравнения", "Сокращение BE/NL", "Вне пары роста нет", "Рост вне пары меньше сокращения", "Рост вне пары не меньше сокращения"], [[x[k] for k in ["category", "comparisons", "pair_declines", "no_growth_outside", "outside_growth_smaller", "outside_growth_at_least_decline"]] for x in summaries])
    t6 = table(["Ряд и охват", "2024, шт.", "2025, шт.", "Темп, %"], [[label, number(x["2024"]), number(x["2025"]), number(x["growth_pct"], 1)] for x, label in zip(comparisons, ["Импорт BEV происхождением из Китая, ЕС-27", "Регистрации новых BEV всех происхождений, ЕС-27"])])
    sources = ["results/full/panel.csv", "results/full/annual_eu_flows.csv", "data/chapter3_public/acea_eu_bev_registrations.csv", "data/chapter3_public/acea_source.json"]
    result = {"date": "2026-10-28", "period": "2022Q1–2025Q4 versus same quarter of prior year", "comparisons": 48, "decline_episodes": 20,
              "summaries": summaries, "market_context": comparisons, "tables": {"T05": t5, "T06": t6},
              "source_sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in sources},
              "interpretation": "Observed simultaneous changes, not identified rerouting or spare physical capacity. No causal or probability estimate.",
              "selection": "All 16 year-on-year quarters per category; decline subset is defined by negative BE/NL quantity change only. Design is retrospective after chapter 2.",
              "checks": {"complete_48_comparisons": True, "exhaustive_decline_classes": True, "no_import_registration_market_share_computed": True, "no_regression_refits": True}}
    (HERE / "chapter3_extension_evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"summaries": summaries, "context": comparisons}, ensure_ascii=False))


if __name__ == "__main__":
    main()
