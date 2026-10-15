"""Validate trade data and decompose destination concentration.

The decomposition is accounting-based and estimates no policy treatment effect.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text())
OUT = ROOT / "results"
PRODUCTS = CFG["product_codes"]
EU = set(CFG["eu27_iso"])
LABELS = {392: "Япония", 410: "Республика Корея"}


def read_source(filename: str) -> bytes:
    path = ROOT / "data/raw" / filename
    compressed_path = path.with_suffix(path.suffix + ".gz")
    if compressed_path.exists():
        return gzip.decompress(compressed_path.read_bytes())
    return path.read_bytes()


def load_and_validate():
    manifest = json.loads((ROOT / "data/sources_manifest.json").read_text())
    records, source_counts = [], []
    for source in manifest:
        body = read_source(source["raw_file"])
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Source hash mismatch: {source['raw_file']}")
        obj = json.loads(body)
        assert len(obj["data"]) == source["records"] < 500
        records.extend(obj["data"])
        source_counts.append(source["records"])
    df = pd.DataFrame.from_records(records)
    df["cmdCode"] = df.cmdCode.astype(str)
    key = ["reporterCode", "refYear", "cmdCode", "partnerCode"]
    assert not df.duplicated(key).any(), "Duplicate observation key"
    assert df.primaryValue.notna().all() and (df.primaryValue >= 0).all()
    assert np.isfinite(df.primaryValue).all()
    assert set(df.cmdCode) == set(PRODUCTS + ["8542"])
    assert set(df.reporterCode) == {int(x) for x in CFG["reporters"]}
    assert set(df.refYear) == set(CFG["years"])
    assert df.isOriginalClassification.all(), "Converted classification in input"
    assert set(df.classificationCode).issubset({"H5", "H6"})
    geography_codes = df[["partnerCode", "partnerISO"]].drop_duplicates()
    assert geography_codes.partnerCode.is_unique and geography_codes.partnerISO.is_unique
    for name, expected in [("flowCode", "X"), ("partner2Code", 0),
                           ("motCode", 0), ("customsCode", "C00"),
                           ("freqCode", "A"), ("typeCode", "C")]:
        assert (df[name] == expected).all(), f"Unexpected {name}"
    assert (df.fobvalue - df.primaryValue).abs().max() <= 0.01
    checks = []
    tolerance = CFG["reconciliation_relative_tolerance"]
    for r in CFG["reporters"]:
        for y in CFG["years"]:
            block = df[(df.reporterCode == int(r)) & (df.refYear == y)]
            assert set(block.cmdCode) == set(PRODUCTS + ["8542"])
            assert block.classificationCode.nunique() == 1
            world = block[block.partnerCode == 0].set_index("cmdCode").primaryValue
            assert len(world) == 6 and (world > 0).all()
            for g in PRODUCTS + ["8542"]:
                partners = block[(block.cmdCode == g) & (block.partnerCode != 0)].primaryValue.sum()
                relative_error = abs(partners - world[g]) / world[g]
                checks.append(dict(reporter=int(r), year=y, test="partners_equal_world",
                                   product=g, relative_error=relative_error))
                assert relative_error <= tolerance, (r, y, g, relative_error)
            relative_error = abs(world[PRODUCTS].sum() - world["8542"]) / world["8542"]
            checks.append(dict(reporter=int(r), year=y, test="hs6_equal_hs4",
                               product="8542", relative_error=relative_error))
            assert relative_error <= tolerance, (r, y, relative_error)
            by_partner = block[block.cmdCode.isin(PRODUCTS)].groupby("partnerCode").primaryValue.sum()
            hs4 = block[block.cmdCode == "8542"].set_index("partnerCode").primaryValue
            all_partners = by_partner.index.union(hs4.index)
            gap = by_partner.reindex(all_partners, fill_value=0) - hs4.reindex(all_partners, fill_value=0)
            relative_error = gap.abs().sum() / world["8542"]
            checks.append(dict(reporter=int(r), year=y, test="hs6_equal_hs4_by_partner",
                               product="8542", relative_error=relative_error))
            assert relative_error <= tolerance, (r, y, relative_error)
    checks = pd.DataFrame(checks)
    checks.to_csv(OUT / "data_checks.csv", index=False)
    columns = ["reporterCode", "reporterISO", "reporterDesc", "refYear",
               "classificationCode", "cmdCode", "cmdDesc", "partnerCode",
               "partnerISO", "partnerDesc", "primaryValue"]
    df[columns].sort_values(key).to_csv(ROOT / "data/trade_panel.csv.gz", index=False,
                                     compression={"method": "gzip", "mtime": 0})
    audit = dict(source_files=len(manifest), source_records=len(df),
                 hs6_partner_observations=int(((df.partnerCode != 0) & df.cmdCode.isin(PRODUCTS)).sum()),
                 country_years=len(df[["reporterCode", "refYear"]].drop_duplicates()),
                 product_years=len(df[df.cmdCode.isin(PRODUCTS)][["reporterCode", "refYear", "cmdCode"]].drop_duplicates()),
                 checks=len(checks), largest_reconciliation_relative_error=float(checks.relative_error.max()),
                 largest_source_response=max(source_counts), preview_cap=500,
                 classification_by_year=df[["refYear", "classificationCode"]].drop_duplicates().sort_values("refYear").to_dict("records"),
                 partner_categories=df[df.partnerCode != 0][["partnerCode", "partnerISO", "partnerDesc"]].drop_duplicates().sort_values("partnerCode").to_dict("records"))
    return df, audit


def state(df, reporter, year, products=PRODUCTS, merge_china_hk=False):
    sub = df[(df.reporterCode == reporter) & (df.refYear == year)
             & df.cmdCode.isin(products) & (df.partnerCode != 0)].copy()
    if merge_china_hk:
        sub.loc[sub.partnerISO.isin(["CHN", "HKG"]), "partnerISO"] = "CHN_HKG"
    destinations = sorted(set(df.loc[df.partnerCode != 0, "partnerISO"]))
    if merge_china_hk:
        destinations = sorted((set(destinations) - {"CHN", "HKG"}) | {"CHN_HKG"})
    matrix = sub.pivot_table(index="cmdCode", columns="partnerISO", values="primaryValue",
                             aggfunc="sum", fill_value=0).reindex(index=products, columns=destinations, fill_value=0)
    x = matrix.to_numpy(dtype=float)
    totals = x.sum(axis=1)
    assert (totals > 0).all()
    w = totals / totals.sum()
    p = x / totals[:, None]
    np.testing.assert_allclose(w.sum(), 1, atol=1e-12)
    np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-12)
    return w, p, destinations, float(totals.sum())


def measure(w, p, destinations, metric):
    shares = w @ p
    if metric == "HHI":
        return float(shares @ shares)
    if metric == "CR3":
        return float(np.sort(shares)[-3:].sum())
    if metric == "effective_destinations":
        return float(1 / (shares @ shares))
    masks = {
        "US_share": {"USA"}, "EU27_share": EU,
        "China_share": {"CHN"}, "HongKong_share": {"HKG"},
        "China_HK_share": {"CHN", "HKG", "CHN_HKG"},
    }
    return float(shares[np.isin(destinations, list(masks[metric]))].sum())


def decompose(df, reporter, y0, y1, metric, products=PRODUCTS, merge_china_hk=False):
    w0, p0, d, _ = state(df, reporter, y0, products, merge_china_hk)
    w1, p1, d1, _ = state(df, reporter, y1, products, merge_china_hk)
    assert d == d1
    f00 = measure(w0, p0, d, metric)
    f10 = measure(w1, p0, d, metric)
    f01 = measure(w0, p1, d, metric)
    f11 = measure(w1, p1, d, metric)
    mix = ((f10-f00) + (f11-f01))/2
    geography = ((f01-f00) + (f11-f10))/2
    residual = f11-f00-mix-geography
    assert abs(residual) < 1e-12
    return dict(reporter=reporter, country=LABELS[reporter], start=y0, end=y1,
                metric=metric, initial=f00, final=f11, delta=f11-f00,
                product_mix=mix, within_product_geography=geography,
                fixed_initial_weights_final=f01, residual=residual)


def run_analysis(df):
    annual, products, destinations = [], [], []
    metrics = ["HHI", "CR3", "effective_destinations", "US_share", "EU27_share",
               "China_share", "HongKong_share", "China_HK_share"]
    for reporter in map(int, CFG["reporters"]):
        for year in CFG["years"]:
            w, p, d, total = state(df, reporter, year)
            row = dict(reporter=reporter, country=LABELS[reporter], year=year, exports_usd=total)
            row.update({m: measure(w, p, d, m) for m in metrics})
            annual.append(row)
            for code, weight, distributions in zip(PRODUCTS, w, p):
                products.append(dict(reporter=reporter, year=year, product=code,
                                     product_share=weight, HHI=float(distributions @ distributions)))
            for iso, share in zip(d, w @ p):
                if share > 0:
                    destinations.append(dict(reporter=reporter, year=year, destination=iso, share=share))
    annual = pd.DataFrame(annual)
    annual.to_csv(OUT / "annual_indicators.csv", index=False)
    pd.DataFrame(products).to_csv(OUT / "product_indicators.csv", index=False)
    pd.DataFrame(destinations).to_csv(OUT / "destination_shares.csv", index=False)
    # Independent calculation from HS4 exports, bypassing HS6 weights.
    for row in annual.itertuples():
        direct = df[(df.reporterCode == row.reporter) & (df.refYear == row.year)
                    & (df.cmdCode == "8542") & (df.partnerCode != 0)].primaryValue.to_numpy()
        direct_shares = direct / direct.sum()
        np.testing.assert_allclose(row.HHI, direct_shares @ direct_shares, atol=1e-9)
    decomposition = pd.DataFrame([decompose(df, r, a, b, m) for r in map(int, CFG["reporters"])
                                  for a, b in CFG["comparisons"] for m in metrics])
    decomposition.to_csv(OUT / "decomposition.csv", index=False)
    sensitivity = []
    for name, codes, merge in [("exclude_parts", PRODUCTS[:-1], False),
                               ("merge_china_hk", PRODUCTS, True),
                               ("exclude_parts_merge_china_hk", PRODUCTS[:-1], True)]:
        for r in map(int, CFG["reporters"]):
            for a, b in CFG["comparisons"]:
                for m in ["HHI", "CR3", "China_HK_share", "US_share", "EU27_share"]:
                    entry = decompose(df, r, a, b, m, codes, merge)
                    entry["specification"] = name
                    sensitivity.append(entry)
    pd.DataFrame(sensitivity).to_csv(OUT / "sensitivity.csv", index=False)
    fixed = []
    for r in map(int, CFG["reporters"]):
        w0, _, d0, _ = state(df, r, 2017)
        for y in CFG["years"]:
            _, p, d, _ = state(df, r, y)
            assert d == d0
            fixed.append(dict(reporter=r, year=y,
                              HHI_fixed_2017_weights=measure(w0, p, d, "HHI")))
    fixed = pd.DataFrame(fixed)
    fixed.to_csv(OUT / "fixed_weights.csv", index=False)
    return annual, decomposition, fixed


def plot(annual, decomposition, fixed):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, r in zip(axes, map(int, CFG["reporters"])):
        sub = annual[annual.reporter == r]
        fix = fixed[fixed.reporter == r]
        ax.plot(sub.year, sub.HHI, marker="o", color="#245b78", label="Фактический HHI")
        ax.plot(fix.year, fix.HHI_fixed_2017_weights, linestyle="--", marker="s",
                color="#b66a2a", label="Товарные доли 2017 г.")
        ax.set(title=LABELS[r], xlabel="Год", xticks=[2017, 2019, 2021, 2024])
        ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Концентрация направлений экспорта, HHI")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("Интегральные схемы: география при фактическом и фиксированном товарном составе")
    fig.text(.01, .01, "Источник: UN Comtrade, HS 8542; расчеты по стоимостным долям. Пунктир — условный расчет, не прогноз.", fontsize=8)
    fig.tight_layout(rect=[0, .05, 1, .94])
    fig.savefig(OUT / "hhi_fixed_weights.png", dpi=170)
    plt.close(fig)
    main = decomposition[(decomposition.start == 2017) & (decomposition.end == 2024)
                         & (decomposition.metric == "HHI")]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(main))
    ax.bar(x-.24, main.delta, width=.23, color="#243c4b", label="Общее изменение")
    ax.bar(x, main.product_mix, width=.23, color="#b66a2a", label="Товарная структура")
    ax.bar(x+.24, main.within_product_geography, width=.23, color="#319a99", label="География внутри групп")
    ax.axhline(0, color="#777777", linewidth=.7)
    ax.set_xticks(x, main.country)
    ax.set_ylabel("Изменение HHI, 2017–2024 гг.")
    ax.set_title("Что составляло изменение концентрации экспорта?")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=.2)
    fig.text(.01, .01, "Источник: UN Comtrade; симметричное разложение Шепли. Отрицательное значение означает снижение HHI.", fontsize=8)
    fig.tight_layout(rect=[0, .06, 1, 1])
    fig.savefig(OUT / "hhi_decomposition.png", dpi=170)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df, audit = load_and_validate()
    annual, decomposition, fixed = run_analysis(df)
    plot(annual, decomposition, fixed)
    audit["independent_hs4_hhi_check"] = "PASS: all 16 exporter-years"
    audit["decomposition_identity_check"] = "PASS: all reported comparisons and sensitivities"
    (OUT / "validation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    main = decomposition[(decomposition.start == 2017) & (decomposition.end == 2024)
                         & decomposition.metric.isin(["HHI", "China_HK_share", "US_share", "EU27_share"])]
    print(main.to_string(index=False))
    print(f"PASS: {audit['source_records']} records; {audit['checks']} reconciliation checks; "
          f"max relative error {audit['largest_reconciliation_relative_error']:.3g}")


if __name__ == "__main__":
    main()
