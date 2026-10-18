"""Assemble descriptive evidence for Chapter 2 from saved data and estimates.

No network requests, model estimation or changes to the primary specification.
Run from any directory with the project's Python dependencies installed.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
REPO = PROJECT.parent.parent
RISK = PROJECT / "risk_extension"
GOODS = [854231, 854232, 854233, 854239]
INPUTS = {}


def read_csv(relative):
    path = RISK / relative
    INPUTS[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return pd.read_csv(path)


def records(frame):
    return json.loads(frame.to_json(orient="records", double_precision=15))


def main():
    panel = read_csv("data/monthly_panel_full.csv.gz")
    annual_saved = read_csv("results/monthly/annual_indicators_from_months.csv")
    grid = read_csv("results/monthly/risk_grid.csv")
    primary_grid = grid[grid["case"] == "primary"]
    # The primary summary is authoritative about retained separate directions.
    summary = read_csv("results/monthly/risk_summary.csv")
    direction_sets = summary.loc[summary.case.eq("primary"), "directions"].unique()
    assert len(direction_sets) == 1
    directions = [int(x) for x in direction_sets[0].split(";")]
    assert len(directions) == 8 and len(primary_grid) > 0

    data = panel.loc[panel.cmdCode.isin(GOODS) & panel.partnerCode.ne(0)].copy()
    assert data.refYear.between(2017, 2024).all()
    data["destination"] = data.partnerCode.where(data.partnerCode.isin(directions), -1)

    total = data.groupby(["reporterCode", "refYear"]).primaryValue.sum().rename("export_usd").reset_index()
    total["ordinary_annual_growth_pct"] = total.groupby("reporterCode").export_usd.pct_change() * 100
    annual_check = total.merge(annual_saved.loc[~annual_saved.include_parts],
                              left_on=["reporterCode", "refYear"], right_on=["reporter", "year"],
                              suffixes=("", "_saved"), validate="one_to_one")
    annual_error = float((annual_check.export_usd - annual_check.export_usd_saved).abs().max())
    assert annual_error < 0.1
    endpoint_totals = total.pivot(index="reporterCode", columns="refYear", values="export_usd")
    total_change = (100 * (endpoint_totals[2024] / endpoint_totals[2017] - 1)).rename("nominal_export_change_pct_2017_2024").reset_index()

    products = data.groupby(["reporterCode", "refYear", "cmdCode"]).primaryValue.sum().rename("export_usd").reset_index()
    products["share_pct"] = 100 * products.export_usd / products.groupby(["reporterCode", "refYear"]).export_usd.transform("sum")
    product_changes = products.pivot(index=["reporterCode", "cmdCode"], columns="refYear", values="export_usd")
    product_changes["change_usd"] = product_changes[2024] - product_changes[2017]
    product_changes["share_of_total_change_pct"] = 100 * product_changes.change_usd / product_changes.groupby(level=0).change_usd.transform("sum")
    product_changes = product_changes[["change_usd", "share_of_total_change_pct"]].reset_index()
    destinations = data.groupby(["reporterCode", "refYear", "destination"]).primaryValue.sum().rename("export_usd").reset_index()
    destinations["share_pct"] = 100 * destinations.export_usd / destinations.groupby(["reporterCode", "refYear"]).export_usd.transform("sum")
    within = data.groupby(["reporterCode", "refYear", "cmdCode", "destination"]).primaryValue.sum().rename("export_usd").reset_index()
    within["within_product_share_pct"] = 100 * within.export_usd / within.groupby(["reporterCode", "refYear", "cmdCode"]).export_usd.transform("sum")
    for table in (products, destinations):
        assert np.allclose(table.groupby(["reporterCode", "refYear"]).share_pct.sum(), 100)
    assert np.allclose(within.groupby(["reporterCode", "refYear", "cmdCode"]).within_product_share_pct.sum(), 100)

    growth = read_csv("results/monthly/observed_growth.csv")
    growth = growth.loc[~growth.include_parts & growth.lag.eq(12)]
    growth_stats = []
    for reporter, series in growth.groupby("reporter"):
        low = series.loc[series.growth_pp.idxmin()]
        high = series.loc[series.growth_pp.idxmax()]
        assert len(series) == 84
        growth_stats.append(dict(reporter=int(reporter), n=84,
                                 sd_pp=float(series.growth_pp.std(ddof=1)),
                                 mean_growth_pp=float(series.growth_pp.mean()),
                                 minimum_pp=float(low.growth_pp), minimum_period=int(low.period),
                                 maximum_pp=float(high.growth_pp), maximum_period=int(high.period)))

    states = read_csv("results/monthly/risk_states.csv")
    states = states.loc[states.case.eq("primary")]
    endpoint = annual_saved.loc[~annual_saved.include_parts & annual_saved.year.isin([2017, 2024])].copy()
    endpoint["state"] = endpoint.year.map({2017: "initial", 2024: "final"})
    endpoint = endpoint.merge(states[["reporter", "state", "hhi_matched_grid", "residual_share"]],
                              on=["reporter", "state"], validate="one_to_one")
    intervals = read_csv("results/monthly/risk_intervals.csv")
    retained = {
        "primary_states": records(states),
        "primary_intervals": records(intervals.loc[intervals.case.eq("primary")]),
        "all_specifications": records(summary),
    }
    for name in ("memory_share_decomposition", "covariance_attribution_intervals",
                 "destination_attribution_intervals", "cell_attribution_intervals",
                 "leave_one_year_out", "covariance_window_bridge", "diagnostic_status"):
        frame = read_csv(f"post_estimation/results/{name}.csv")
        if "case" in frame:
            frame = frame.loc[frame.case.eq("primary")]
        if "block_months" in frame:
            frame = frame.loc[frame.block_months.eq(12)]
        retained[name] = records(frame)
    extremes = read_csv("results/monthly/ordinary_growth_extremes.csv")
    bridge = read_csv("results/monthly/monthly_annual_bridge.csv")
    max_bridge = bridge.loc[bridge.relative_gap.abs().idxmax()].to_dict()

    out = {
        "purpose": "Chapter 2 descriptive aggregates and pointers to existing model outputs; no new model estimates",
        "goods": GOODS,
        "separate_directions": directions,
        "annual_totals": records(total),
        "endpoint_total_changes": records(total_change),
        "annual_products": records(products),
        "product_absolute_changes_2017_2024": records(product_changes),
        "annual_destination_grid": records(destinations),
        "within_product_destination_endpoints": records(within.loc[within.refYear.isin([2017, 2024])]),
        "endpoint_table": records(endpoint),
        "observed_growth_statistics": growth_stats,
        "largest_ordinary_growth_observations": records(extremes.head(5)),
        "maximum_annual_bridge_gap": max_bridge,
        "saved_results": retained,
        "checks": {
            "annual_export_max_abs_difference_from_saved_usd": annual_error,
            "all_product_and_destination_shares_sum_to_100": True,
            "all_within_product_shares_sum_to_100": True,
            "observed_growth_months_per_exporter": 84,
            "world_rows_excluded_from_direction_sums": True,
            "control_heading_and_parts_excluded_from_primary_descriptive_totals": True,
        },
        "input_sha256": INPUTS,
    }
    target = HERE / "chapter2_evidence.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved {target.name}: {len(INPUTS)} source files; annual total check {annual_error:.8g} USD")


if __name__ == "__main__":
    main()
