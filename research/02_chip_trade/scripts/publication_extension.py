"""Exploratory, post-pilot checks for a possible publication (2026-10-16).

Does not change the original protocol, raw data, or pilot results.
Attributions are accounting identities, not causal effects.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from analyze import CFG, LABELS, PRODUCTS, ROOT, decompose, read_source, state

OUT = ROOT / "results"


def load_sources():
    records = []
    for source in json.loads((ROOT / "data/sources_manifest.json").read_text()):
        body = read_source(source["raw_file"])
        assert hashlib.sha256(body).hexdigest() == source["sha256"]
        rows = json.loads(body)["data"]
        assert len(rows) == source["records"] < 500
        records.extend(rows)
    df = pd.DataFrame(records)
    df["cmdCode"] = df.cmdCode.astype(str)
    assert not df.duplicated(["reporterCode", "refYear", "cmdCode", "partnerCode"]).any()
    return df


def hhi_attribution(df, reporter, start, end):
    """Allocate the two-factor Shapley terms to product-destination cells.

    For a change in a share vector, ||b||^2 - ||a||^2 = (b-a)'(b+a).
    Average both replacement orders, as in the original decomposition.
    These are additive allocations within each factor, not a new many-player
    Shapley game. Signed contributions may offset one another.
    """
    w0, p0, destinations, _ = state(df, reporter, start)
    w1, p1, d1, _ = state(df, reporter, end)
    assert destinations == d1
    s00, s10, s01, s11 = w0 @ p0, w1 @ p0, w0 @ p1, w1 @ p1
    mix = 0.5 * (w1-w0)[:, None] * (
        p0 * (s10+s00)[None, :] + p1 * (s11+s01)[None, :])
    geography = 0.5 * (p1-p0) * (
        w0[:, None] * (s01+s00)[None, :] + w1[:, None] * (s11+s10)[None, :])
    reference = decompose(df, reporter, start, end, "HHI")
    np.testing.assert_allclose(mix.sum(), reference["product_mix"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(geography.sum(), reference["within_product_geography"], rtol=0, atol=1e-12)
    np.testing.assert_allclose((mix+geography).sum(axis=0), s11**2-s00**2, rtol=0, atol=1e-12)
    common = dict(reporter=reporter, country=LABELS[reporter], start=start, end=end)
    products = [dict(**common, product=g, initial_weight=w0[i], final_weight=w1[i],
                     product_mix=mix[i].sum(), within_product_geography=geography[i].sum(),
                     total_attribution=(mix[i]+geography[i]).sum())
                for i, g in enumerate(PRODUCTS)]
    markets = [dict(**common, destination=d, initial_share=s00[j], final_share=s11[j],
                    product_mix=mix[:, j].sum(), within_product_geography=geography[:, j].sum(),
                    total_attribution=(mix[:, j]+geography[:, j]).sum())
               for j, d in enumerate(destinations)]
    residual = max(abs(mix.sum()-reference["product_mix"]),
                   abs(geography.sum()-reference["within_product_geography"]))
    return products, markets, float(residual)


def quantity_audit(df):
    sub = df[df.cmdCode.isin(PRODUCTS) & (df.partnerCode != 0) & (df.primaryValue > 0)].copy()
    output = []
    for (reporter, year, product), block in sub.groupby(["reporterCode", "refYear", "cmdCode"]):
        positive = block.qty.notna() & (block.qty > 0) & (block.qtyUnitCode > 0)
        observed = positive & block.isQtyEstimated.eq(False)
        weight = block.netWgt.notna() & (block.netWgt > 0)
        observed_weight = weight & block.isNetWgtEstimated.eq(False)
        value = block.primaryValue.sum()
        output.append(dict(reporter=int(reporter), country=LABELS[int(reporter)], year=int(year),
                           product=product, positive_value_rows=len(block), exports_usd=value,
                           qty_positive_rows=int(positive.sum()), qty_not_estimated_rows=int(observed.sum()),
                           qty_units="|".join(map(str, sorted(block.loc[positive, "qtyUnitCode"].unique()))),
                           qty_positive_value_share=block.loc[positive, "primaryValue"].sum()/value,
                           qty_not_estimated_value_share=block.loc[observed, "primaryValue"].sum()/value,
                           net_weight_positive_value_share=block.loc[weight, "primaryValue"].sum()/value,
                           net_weight_not_estimated_value_share=block.loc[observed_weight, "primaryValue"].sum()/value))
    return pd.DataFrame(output)


def main():
    df = load_sources()
    annual, chains, product_rows, market_rows, residuals = [], [], [], [], []
    years = sorted(CFG["years"])
    for reporter in map(int, CFG["reporters"]):
        adjacent = [decompose(df, reporter, a, b, "HHI") for a, b in zip(years[:-1], years[1:])]
        annual.extend(adjacent)
        direct = decompose(df, reporter, years[0], years[-1], "HHI")
        chain_mix = sum(row["product_mix"] for row in adjacent)
        chain_geo = sum(row["within_product_geography"] for row in adjacent)
        np.testing.assert_allclose(chain_mix+chain_geo, direct["delta"], rtol=0, atol=1e-12)
        chains.append(dict(reporter=reporter, country=LABELS[reporter], start=years[0], end=years[-1],
                           delta=direct["delta"], endpoint_product_mix=direct["product_mix"],
                           endpoint_geography=direct["within_product_geography"],
                           chain_product_mix=chain_mix, chain_geography=chain_geo,
                           annual_opposing_signs=sum(row["product_mix"]*row["within_product_geography"] < 0
                                                    for row in adjacent), annual_comparisons=len(adjacent)))
        products, markets, residual = hhi_attribution(df, reporter, years[0], years[-1])
        product_rows.extend(products)
        market_rows.extend(markets)
        residuals.append(residual)
    annual = pd.DataFrame(annual)
    chains = pd.DataFrame(chains)
    products = pd.DataFrame(product_rows)
    markets = pd.DataFrame(market_rows)
    quantity = quantity_audit(df)
    for name, frame in [("annual_decomposition", annual), ("chain_comparison", chains),
                        ("drivers_product", products), ("drivers_destination", markets),
                        ("quantity_audit", quantity)]:
        frame.to_csv(OUT / f"publication_{name}.csv", index=False)
    audit = dict(status="PASS", analysis_status="exploratory post-pilot extension, 2026-10-16",
                 annual_decompositions=len(annual), product_attributions=len(products),
                 destination_attributions=len(markets), quantity_groups=len(quantity),
                 largest_attribution_residual=max(residuals),
                 chain_identity="PASS: both exporters",
                 destination_identity="PASS: all destination squared-share changes",
                 quantity_caveat="Positive unestimated quantity does not establish comparable chip quality or physical units across HS6.")
    (OUT / "publication_validation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n")
    print("ENDPOINT AND ANNUAL CHAIN")
    print(chains.to_string(index=False))
    print("PRODUCT ATTRIBUTIONS")
    print(products.to_string(index=False))
    print("ANNUAL DECOMPOSITIONS")
    print(annual[["country", "start", "end", "delta", "product_mix", "within_product_geography"]].to_string(index=False))
    for reporter, block in markets.groupby("reporter"):
        print("LARGEST GEOGRAPHY ATTRIBUTIONS", LABELS[reporter])
        top = block.reindex(block.within_product_geography.abs().sort_values(ascending=False).index).head(8)
        print(top[["destination", "initial_share", "final_share", "within_product_geography"]].to_string(index=False))
    for reporter, block in quantity.groupby("reporter"):
        print("QUANTITY COVERAGE", LABELS[reporter])
        print({column: float(np.average(block[column], weights=block.exports_usd))
               for column in ["qty_positive_value_share", "qty_not_estimated_value_share",
                              "net_weight_positive_value_share", "net_weight_not_estimated_value_share"]})
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
