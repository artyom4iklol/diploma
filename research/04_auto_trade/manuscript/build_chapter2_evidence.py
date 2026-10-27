"""Prepare chapter-two tables from frozen results; never refit a model."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def number(x, decimals=0):
    return f"{float(x):,.{decimals}f}".replace(",", " ").replace(".", ",")


def table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(map(str, row)) + " |" for row in rows),
    ])


def main():
    files = {}
    for record in load("writing/evidence_register.json")["records"]:
        for path, expected in record["source_sha256"].items():
            actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            assert actual == expected, path
            files[path] = actual
    original_count = len(files)
    raw_path = "data/full_raw/eurostat_full.json"
    raw_hash = hashlib.sha256((ROOT / raw_path).read_bytes()).hexdigest()
    assert raw_hash == load("data/full_raw/request.json")["response_sha256"]
    files[raw_path] = raw_hash
    extra = [
        "results/full/annual_eu_flows.csv", "results/full/annual_member_flows.csv",
        "results/full/panel.csv", "results/full/entry_concentration.csv",
        "results/geography_focus/pooled_HHI_product_geography.csv",
        "results/geography_focus/category_HHI_group_shapley.csv",
        "results/augmented/conditional_share_equivalence.json",
        "results/augmented/output_validation.json", "results/augmented/coefficients.csv",
    ]
    for path in extra:
        files[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    a = pd.read_csv(ROOT / "results/full/annual_eu_flows.csv")
    m = pd.read_csv(ROOT / "results/full/annual_member_flows.csv")
    p = pd.read_csv(ROOT / "results/full/panel.csv")
    cn = a[a.origin == "CN"].copy()
    national = m[m.origin == "CN"].groupby(["category", "year"])[["quantity", "value_eur"]].sum().sort_index()
    aggregate = cn.set_index(["category", "year"])[["quantity", "value_eur"]].sort_index()
    assert national.equals(aggregate)
    monthly = p[(p.origin == "CN") & (p.reporter != "EU27_2020")].copy()
    monthly["year"] = monthly.month.str[:4].astype(int)
    sums = monthly.groupby(["category", "year"])[["quantity", "value_eur"]].sum().sort_index()
    assert sums.equals(aggregate)
    totals = cn.groupby("year")[["quantity", "value_eur"]].sum()
    ext = a[a.origin == "EXT_EU27_2020"].groupby("year")[["quantity", "value_eur"]].sum()
    shares = totals / ext * 100
    rows = []
    for year in range(2021, 2026):
        for cat in ["BEV", "PHEV", "HEV"]:
            row = cn[(cn.year == year) & (cn.category == cat)].iloc[0]
            rows.append([str(year), cat, number(row.quantity), number(row.value_eur / 1e9, 3), number(row.customs_eur_per_vehicle)])
        rows.append([str(year), "Всего", number(totals.loc[year, "quantity"]), number(totals.loc[year, "value_eur"] / 1e9, 3), "—"])
    tables = {"T03": table(["Год", "Категория", "Количество, шт.", "Стоимость, млрд евро", "Средняя стоимость, евро/шт."], rows)}
    h = pd.read_csv(ROOT / "results/geography_focus/pooled_HHI_product_geography.csv")
    group_h = pd.read_csv(ROOT / "results/geography_focus/category_HHI_group_shapley.csv")
    assert (group_h.identity_error.abs() < 1e-12).all()
    accounts = load("results/full/accounting_decompositions.json")
    assert all(abs(x["two_factor"]["identity_error_pp"]) < 1e-10 for x in accounts)
    values = load("results/full/china_value_change_accounting.json")
    assert all(abs(x["identity_error_eur"]) < 1e-4 for x in values)
    assert load("results/augmented/output_validation.json")["passed"]
    rows = []
    for _, r in h.iterrows():
        rows.append([f"{r.start}–{r.end}", "Количество" if r.outcome == "quantity" else "Стоимость",
                     *[number(r[k], 4) for k in ["HHI_start", "fixed_start_product_mix_end_geography_HHI", "end_product_mix_fixed_start_geography_HHI", "HHI_end"]]])
    t4a = table(["Период", "Показатель", "H(b₀,G₀)", "H(b₀,G₁)", "H(b₁,G₀)", "H(b₁,G₁)"], rows)
    rows = []
    for _, r in h.iterrows():
        assert abs(r.HHI_change - r.product_mix_component - r.within_product_geography_component) < 1e-12
        rows.append([f"{r.start}–{r.end}", "Количество" if r.outcome == "quantity" else "Стоимость", *[number(r[k], 4) for k in ["HHI_change", "product_mix_component", "within_product_geography_component"]]])
    t4b = table(["Период", "Показатель", "Изменение HHI", "Товарные веса", "География внутри технологий"], rows)
    tables["T04"] = "Панель А. Наблюдаемые и стандартизованные корзины\n\n" + t4a + "\n\nПанель Б. Симметричные вклады в изменение HHI\n\n" + t4b
    block = load("results/augmented/paired_block_summary.json")
    preferred = {}
    rows = []
    for outcome, suffix in [("quantity", "quantity"), ("value_eur", "value")]:
        model = load(f"results/augmented/rest_preferred_{suffix}.json")
        b = {x["term"]: x for x in block["outcomes"][outcome]["coefficients"]}
        preferred[outcome] = []
        for c in model["coefficients"]:
            if not c["term"].endswith("__definitive"):
                continue
            cat = c["term"].split("__")[0]
            ci = c["hac12"]["multiplier_ci95"]
            bi = b[c["term"]]["multiplier_ci95"]
            preferred[outcome].append({"category": cat, "multiplier": c["multiplier"], "hac12": ci, "block": bi})
            rows.append([cat, "Количество" if outcome == "quantity" else "Стоимость", number(c["multiplier"], 3), f"[{number(ci[0],3)}; {number(ci[1],3)}]", f"[{number(bi[0],3)}; {number(bi[1],3)}]"])
    tables["T05"] = table(["Категория", "Показатель", "Множитель", "95%-интервал HAC(12)", "Блочный интервал, 2,5–97,5%"], rows)
    # Annual customs-unit-value flag: observed source values, not imputed data.
    nl = m[(m.origin == "CN") & (m.reporter == "NL") & (m.category == "BEV") & (m.year == 2025)].iloc[0]
    monthly["quarter"] = pd.PeriodIndex(monthly.month, freq="M").asfreq("Q").astype(str)
    quarters = monthly.groupby(["category", "quarter"])[["quantity", "value_eur"]].sum().reset_index()
    evidence = {
        "date": "2026-10-27", "models_refitted": False,
        "original_register_files_verified": original_count, "file_sha256": files,
        "annual_CN": cn.to_dict("records"),
        "annual_CN_totals": totals.reset_index().to_dict("records"),
        "annual_CN_share_of_selected_extraEU_pct": shares.reset_index().to_dict("records"),
        "quarterly_CN": quarters.to_dict("records"),
        "preferred_definitive": preferred,
        "share_accounting": accounts,
        "value_accounting": values,
        "pooled_HHI": h.to_dict("records"),
        "unit_value_flag_NL_BEV_2025": {
            "quantity": int(nl.quantity), "value_eur": int(nl.value_eur),
            "customs_eur_per_vehicle": float(nl.customs_eur_per_vehicle),
            "interpretation": "Low observed customs unit value; retained and disclosed. Source agreement does not establish an economic explanation or constant-quality price.",
        },
        "checks": {"CN_annual_equals_national_sum": True, "CN_annual_equals_monthly_sum": True,
                   "HHI_component_identities": True, "frozen_source_hashes_match": True,
                   "all_12_group_HHI_identities": True,
                   "all_4_share_accounting_identities": True,
                   "both_value_identities_within_0_0001_euro": True,
                   "saved_augmented_model_validation_passed": True,
                   "raw_response_matches_retrieval_sha256": True},
    }
    (OUT / "chapter2_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "chapter2_generated_tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified_files": len(files), "totals": evidence["annual_CN_totals"], "NL_flag": evidence["unit_value_flag_NL_BEV_2025"], "quarters2025": quarters[quarters.quarter.str.startswith("2025")].to_dict("records")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
