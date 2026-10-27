"""Bounded descriptive sensitivity; no model/data replacement or refits."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/chapter2_revision"


def main():
    OUT.mkdir(exist_ok=True)
    raw_path = ROOT / "data/full_raw/eurostat_full.json"
    raw = json.loads(raw_path.read_text())
    panel = pd.read_csv(ROOT / "results/full/panel.csv")
    records = []
    # Independent mixed-radix JSON-stat lookup, not the panel loader.
    for month in pd.period_range("2025-01", "2025-12", freq="M").astype(str):
        row = {"month": month}
        for indicator, column in [("SUPPLEMENTARY_QUANTITY", "quantity"), ("VALUE_IN_EUROS", "value_eur")]:
            labels = dict(freq="M", reporter="NL", partner="CN", product="87038010", flow="1", indicators=indicator, time=month)
            index = 0
            for name, length in zip(raw["id"], raw["size"]):
                index = index * length + raw["dimension"][name]["category"]["index"][labels[name]]
            value = raw["value"][str(index)]
            saved = panel.loc[(panel.reporter == "NL") & (panel.origin == "CN") & (panel.category == "BEV") & (panel.month == month), column].item()
            assert value == saved, (month, column)
            row[column] = value
            row[column + "_raw_flat_index"] = index
        row["customs_eur_per_vehicle"] = row["value_eur"] / row["quantity"]
        records.append(row)
    a = pd.read_csv(ROOT / "results/full/annual_member_flows.csv")
    variants = {}
    for name, excluded in [("full_EU27", []), ("exclude_NL", ["NL"]), ("exclude_BE_NL", ["BE", "NL"])]:
        sample = a[~a.reporter.isin(excluded)]
        cn = sample[sample.origin == "CN"]
        extra = sample[sample.origin == "EXT_EU27_2020"]
        ct = cn.groupby("year")[["quantity", "value_eur"]].sum()
        et = extra.groupby("year")[["quantity", "value_eur"]].sum()
        shares = ct / et * 100
        hhi = {}
        for year in [2023, 2025]:
            yearly = cn[cn.year == year]
            hhi[str(year)] = {}
            for col in ["quantity", "value_eur"]:
                x = yearly.groupby("reporter")[col].sum()
                hhi[str(year)][col] = float(((x / x.sum()) ** 2).sum())
        bycat = cn.groupby(["year", "category"])[["quantity", "value_eur"]].sum()
        q0 = bycat.loc[2023, "quantity"]; q1 = bycat.loc[2025, "quantity"]
        u0 = bycat.loc[2023, "value_eur"] / q0; u1 = bycat.loc[2025, "value_eur"] / q1
        qpart = float(((u0 + u1) / 2 * (q1 - q0)).sum())
        upart = float(((q0 + q1) / 2 * (u1 - u0)).sum())
        dv = int(ct.loc[2025, "value_eur"] - ct.loc[2023, "value_eur"])
        assert abs(qpart + upart - dv) < 1e-4
        variants[name] = {
            "excluded_reporters": excluded, "denominator": "extraEU for exactly the same retained reporters and three CN8 codes",
            "years": {str(y): {"quantity": int(ct.loc[y, "quantity"]), "value_eur": int(ct.loc[y, "value_eur"]), "quantity_share_pct": float(shares.loc[y, "quantity"]), "value_share_pct": float(shares.loc[y, "value_eur"])} for y in [2023, 2025]},
            "quantity_share_change_pp": float(shares.loc[2025, "quantity"] - shares.loc[2023, "quantity"]),
            "value_share_change_pp": float(shares.loc[2025, "value_eur"] - shares.loc[2023, "value_eur"]),
            "quantity_growth_pct": float((ct.loc[2025, "quantity"] / ct.loc[2023, "quantity"] - 1) * 100),
            "value_growth_pct": float((ct.loc[2025, "value_eur"] / ct.loc[2023, "value_eur"] - 1) * 100),
            "value_change_eur": dv, "quantity_component_eur": qpart, "unit_value_component_eur": upart,
            "HHI_renormalized_within_retained_reporters": hhi,
        }
    result = {"date": "2026-10-27", "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
              "independent_raw_lookup_checks": 24, "all_match_saved_panel": True, "NL_BEV_2025_months": records,
              "variants": variants, "models_refitted": False,
              "interpretation": "Robustness of descriptive quantities to disclosed geographic exclusions; no value correction, no claim of source error, no price/causal inference.",
              "fresh_source_check": "An additional one-cell Eurostat API request via the research browser was not accessible; no fresh response was substituted for the frozen snapshot.",
              "economic_cause_of_low_NL_unit_value": "unresolved"}
    (OUT / "valuation_diagnostic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: {x: v[x] for x in ["value_growth_pct", "quantity_share_change_pp", "value_share_change_pp"]} for k, v in variants.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
