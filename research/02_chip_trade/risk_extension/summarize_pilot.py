"""Reconcile the limited monthly pilot against its raw cache and annual baseline."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def main():
    audit = pd.read_csv(RESULTS / "monthly_availability.csv")
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    assert len(audit) == len(manifest) == 34, "Incomplete availability pilot"
    records = []
    for m in manifest:
        if "sha256" not in m:
            continue
        name = f"{m['reporter']}_{m['flow']}_{m['period']}_854232.json.gz"
        raw = gzip.decompress((ROOT / "data" / "raw" / name).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == m["sha256"], name
        records += (json.loads(raw).get("data") or [])
    monthly = pd.DataFrame(records)
    monthly["period"] = pd.to_numeric(monthly["period"], errors="raise").astype(int)
    columns = ["reporterCode", "flowCode", "period", "classificationCode", "cmdCode",
               "partnerCode", "partnerISO", "partnerDesc", "primaryValue"]
    monthly[columns].to_csv(RESULTS / "monthly_panel.csv", index=False)
    annual = pd.read_csv(ROOT.parent / "data" / "trade_panel.csv.gz")
    memory = annual[annual.cmdCode.eq(854232) & annual.partnerCode.ne(0)].copy()
    markets = [156, 344, 490, 702, 608, 704, 458, 699]
    total = memory.groupby(["reporterISO", "refYear"]).primaryValue.sum()
    selected = memory[memory.partnerCode.isin(markets)].groupby(["reporterISO", "refYear"]).primaryValue.sum()
    coverage = (selected / total).rename("eight_market_share").reset_index()
    coverage.to_csv(RESULTS / "annual_market_coverage.csv", index=False)
    absent = audit.loc[audit.flow.eq("M") & audit.status.ne("available"), "reporter"].astype(int).tolist()
    missing_shares = (memory[memory.partnerCode.isin(absent)]
                      .groupby(["reporterISO", "refYear"]).primaryValue.sum() / total)
    missing_shares.rename("share_to_markets_with_empty_import_probe").reset_index().to_csv(
        RESULTS / "annual_missing_import_market_shares.csv", index=False)
    recon = []
    exports = monthly[monthly.flowCode.eq("X")]
    for reporter in [392, 410]:
        x = exports[exports.reporterCode.eq(reporter) & exports.period.between(202401, 202412)]
        world = x[x.partnerCode.eq(0)]
        assert world.period.nunique() == 12, "Missing export month"
        av = annual[annual.reporterCode.eq(reporter) & annual.refYear.eq(2024)
                    & annual.partnerCode.eq(0) & annual.cmdCode.eq(854232)].primaryValue.item()
        mv = float(world.primaryValue.sum())
        recon.append(dict(reporter=reporter, months=12, monthly_world_sum_usd=mv,
                          annual_world_usd=av, relative_gap=(mv-av)/av,
                          exact_within_1ppm=abs(mv-av)/av < 1e-6))
    pd.DataFrame(recon).to_csv(RESULTS / "monthly_annual_reconciliation.csv", index=False)
    w = annual[annual.partnerCode.eq(0) & annual.cmdCode.isin([8542,854232])]
    w = w.pivot(index=["reporterISO", "refYear"], columns="cmdCode", values="primaryValue")
    (w[854232]/w[8542]).rename("memory_share").reset_index().to_csv(RESULTS / "annual_memory_shares.csv", index=False)
    export_checks = audit[audit.flow.eq("X")]
    import_checks = audit[audit.flow.eq("M")]
    export_ok = bool(export_checks.status.eq("available").all() and all(
        export_checks[c].eq(True).all() for c in ["cap_ok", "unique_partners", "selection_ok", "reconciliation_ok"]))
    demand_ok = bool(import_checks.status.eq("available").all() and all(
        import_checks[c].eq(True).all() for c in ["cap_ok", "unique_partners", "selection_ok", "reconciliation_ok", "rest_of_world_nonnegative"]))
    summary = dict(pilot_requests=34, responses_with_data=int(audit.status.eq("available").sum()),
                   empty_responses=int(audit.status.eq("empty").sum()),
                   failed_requests=int(audit.status.eq("request_failed").sum()),
                   raw_records=len(records), export_responses=len(export_checks),
                   monthly_export_availability_gate=export_ok,
                   full_eight_market_demand_proxy_gate=demand_ok,
                   absent_import_reporters=import_checks.loc[import_checks.status.ne("available"), "reporter"].astype(int).tolist(),
                   max_world_partner_relative_gap=float(audit.world_relative_gap.max()),
                   minimum_annual_eight_market_coverage=float(coverage.eight_market_share.min()),
                   monthly_annual_reconciliation=recon,
                   estimated_risk=False, estimated_covariance=False,
                   limitation="Only HS854232, one complete calendar year plus Jan 2017; historical HS6 panel not collected.")
    (RESULTS / "pilot_validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
