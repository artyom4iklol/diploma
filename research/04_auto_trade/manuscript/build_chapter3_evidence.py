"""Application arithmetic for chapter 3; frozen inputs, no regression refits."""
from pathlib import Path
import hashlib
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "results/chapter3_application"


def fmt(x, n=1):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(map(str, row)) + " |" for row in rows)])


def main():
    OUT.mkdir(exist_ok=True)
    sources = {}
    register = json.loads((ROOT / "writing/evidence_register.json").read_text())
    for record in register["records"]:
        for path, expected in record["source_sha256"].items():
            actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            assert actual == expected, path
            sources[path] = actual
    original_count = len(sources)
    plan = json.loads((HERE / "chapter3_planning_sources.json").read_text())
    for path, expected in plan["internal_files_sha256"].items():
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert actual == expected, path
        sources[path] = actual
    basepath = "results/augmented/clearance_jurisdiction_exposure.csv"
    base = pd.read_csv(ROOT / basepath)
    member = pd.read_csv(ROOT / "results/full/annual_member_flows.csv")
    member = member[(member.origin == "CN") & (member.year == 2025)]
    rows = []
    for row in base.itertuples(index=False):
        cat = row.category
        q = member[member.category == cat].quantity.sum()
        pair = member[(member.category == cat) & member.reporter.isin(["BE", "NL"])].quantity.sum()
        assert q == row.EU_registered_units and pair == row.BE_NL_registered_units
        alpha = row.assumed_fraction_disrupted_in_BE_NL_clearance
        assert math.isclose(alpha * pair, row.mechanically_exposed_units, rel_tol=1e-12)
        for rho in [0.0, 0.5, 1.0]:
            exposed = alpha * pair
            remaining = exposed * (1 - rho)
            transferred = exposed * rho
            assert math.isclose(remaining + transferred, exposed, abs_tol=1e-9)
            assert 0 <= remaining <= exposed <= q
            rows.append({"category": cat, "year": 2025, "alpha": alpha, "rho": rho,
                         "EU_quantity": int(q), "BE_NL_quantity": int(pair), "exposed_quantity": float(exposed),
                         "assumed_transferred_quantity": float(transferred), "remaining_quantity": float(remaining),
                         "remaining_share_pct": float(remaining / q * 100)})
    d = pd.DataFrame(rows)
    assert len(d) == 18 and len(d.drop_duplicates(["category", "alpha", "rho"])) == 18
    for _, g in d.groupby(["category", "alpha"]):
        assert g.sort_values("rho").remaining_quantity.is_monotonic_decreasing
    d.to_csv(OUT / "scenario_transfer.csv", index=False, lineterminator="\n")
    rows_table = []
    for cat in ["BEV", "PHEV", "HEV"]:
        for alpha in [.1, .25]:
            sub = d[(d.category == cat) & (d.alpha == alpha)].set_index("rho")
            rows_table.append([cat, fmt(alpha * 100, 0) + "%", fmt(sub.loc[0, "remaining_quantity"]), fmt(sub.loc[.5, "remaining_quantity"]), fmt(sub.loc[.5, "remaining_share_pct"], 2) + "%"])
    main_table = table(["Технология", "Условный масштаб α", "Без переноса, расчётных шт.", "При переносе 50%, расчётных шт.", "После переноса, доля всей категории"], rows_table)
    (HERE / "chapter3_generated_tables.json").write_text(json.dumps({"T02": main_table}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    sources["results/full/annual_member_flows.csv"] = hashlib.sha256((ROOT / "results/full/annual_member_flows.csv").read_bytes()).hexdigest()
    evidence = {"date": "2026-10-28", "frozen_register_files_verified": original_count, "source_sha256": sources,
                "scenario_rows": 18, "alpha_values": [.1, .25], "rho_values": [0, .5, 1],
                "parameter_status": "Author-specified illustrative conditions, not estimated probabilities or actual rerouting capacity.",
                "interpretation": "Customs accounting jurisdictions, not physical ports, lost sales, delayed deliveries or welfare.",
                "regressions_refitted": False, "rows": d.to_dict("records"),
                "checks": {"all_existing_scenarios_reproduced": True, "annual_member_sums_match": True,
                           "full_18_combination_grid": True, "bounds_and_conservation": True, "monotonicity": True}}
    (HERE / "chapter3_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    (OUT / "validation.json").write_text(json.dumps({k: v for k, v in evidence.items() if k not in ["rows", "source_sha256"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"verified_original_files": original_count, "scenarios": len(d), "model_refits": 0}))


if __name__ == "__main__":
    main()
