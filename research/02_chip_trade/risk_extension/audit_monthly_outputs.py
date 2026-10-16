"""Audit saved source bytes, numerical identities, and undefined growth cells.

This creates machine-readable diagnostics only; it does not write a report or
change the prespecified sample, grid, growth definition, or estimates.
"""
import gzip
import hashlib
import json

import numpy as np
import pandas as pd

from analyze_monthly import ROOT, GOODS, cube, growth, periods, weights


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / 'results/monthly'
    quality = json.loads((out / 'data_quality.json').read_text())
    analysis = json.loads((out / 'analysis_validation.json').read_text())
    assert quality['analysis_ready'] and quality['complete_primary']
    panel_path = ROOT / 'data/monthly_panel_full.csv.gz'
    panel_sha = sha(panel_path)
    assert panel_sha == quality['monthly_panel_sha256'] == analysis['monthly_panel_sha256']
    assert sha(ROOT / 'data/monthly_manifest.json') == quality['source_manifest_sha256']
    assert sha(ROOT / 'monthly_analysis_protocol.md') == quality['protocol_sha256'] == analysis['protocol_sha256']
    assert sha(ROOT / 'analyze_monthly.py') == analysis['analysis_script_sha256']

    archived = {}
    bundles = json.loads((ROOT / 'data/monthly_bundle_manifest.json').read_text())
    for bundle in bundles:
        path = ROOT / bundle['path']
        assert sha(path) == bundle['sha256'] and path.stat().st_size == bundle['bytes']
        count = 0
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                record = json.loads(line)
                meta = record['metadata']
                raw = record['raw_utf8'].encode('utf-8')
                assert hashlib.sha256(raw).hexdigest() == meta['sha256']
                assert len(raw) == meta['bytes']
                assert meta['task_id'] not in archived
                archived[meta['task_id']] = meta['sha256']
                count += 1
        assert count == bundle['requests']
    manifest = json.loads((ROOT / 'data/monthly_manifest.json').read_text())
    for meta in manifest:
        if meta.get('sha256'):
            assert archived[meta['task_id']] == meta['sha256']

    data = pd.read_csv(panel_path)
    keys = ['reporterCode', 'period', 'cmdCode', 'partnerCode']
    assert not data.duplicated(keys).any()
    primary_data = data[data.period.between(201701, 202412)]
    coverage = primary_data.groupby(['reporterCode', 'period', 'cmdCode']).size()
    assert len(coverage) == 1152
    summary = pd.read_csv(out / 'risk_summary.csv')
    states = pd.read_csv(out / 'risk_states.csv')
    series = pd.read_csv(out / 'risk_series.csv')
    intervals = pd.read_csv(out / 'risk_intervals.csv')
    checks = pd.read_csv(out / 'risk_checks.csv')
    expected_cases = 12 + int(quality['extension_analysis_ready'])
    assert summary['case'].nunique() == expected_cases and len(summary) == 2*expected_cases
    assert set(summary.status) <= {'ok', 'unobserved_growth'}
    primary = summary[summary['case'].eq('primary')]
    assert len(primary) == 2 and primary.status.eq('ok').all() and primary.n.eq(84).all()
    assert not primary.grid_limited.astype(bool).any()
    assert checks.variance_identity_max_error.max() < 1e-12
    assert checks.shapley_add_up_error.max() < 1e-12
    assert checks.weight_sum_max_error.max() < 1e-12
    direct_error = 0.0
    for (case, reporter), rows in states.groupby(['case', 'reporter']):
        values = series[series['case'].eq(case) & series.reporter.eq(reporter)]
        for row in rows.itertuples():
            direct = values[row.state].var(ddof=1) * 10000
            direct_error = max(direct_error, abs(direct - row.variance_pp2))
            assert np.isclose(direct, row.variance_pp2, rtol=1e-10, atol=1e-9)
            assert np.isclose(row.sd_pp**2, row.variance_pp2, rtol=1e-10)
        s = summary[summary['case'].eq(case) & summary.reporter.eq(reporter)].iloc[0]
        assert np.isclose(s.mix_variance_pp2 + s.geography_variance_pp2,
                          s.delta_variance_pp2, rtol=1e-10, atol=1e-9)
    assert len(intervals) == 32
    assert not intervals.duplicated(['case', 'reporter', 'metric', 'block_months']).any()
    assert set(intervals.block_months) == {6, 12}
    assert intervals.repetitions.eq(1999).all() and intervals.seed.eq(20261016).all()
    assert np.isfinite(intervals[['ci_low', 'ci_high']].to_numpy()).all()
    assert intervals.ci_low.le(intervals.ci_high).all()
    identity = pd.read_csv(out / 'aggregate_growth_identity.csv')
    assert identity.max_error.max() < 1e-12

    # Check that expanding the panel did not change the earlier, complete slice.
    training = pd.read_csv(ROOT / 'results/training_check/summary.csv')
    temporal = summary[summary['case'].eq('temporal_2018_2020')]
    numeric = ['delta_variance_pp2', 'mix_variance_pp2',
               'geography_variance_pp2', 'delta_sd_pp']
    for reporter in (392, 410):
        a = training[training.reporter.eq(reporter)][numeric].to_numpy(dtype=float)
        b = temporal[temporal.reporter.eq(reporter)][numeric].to_numpy(dtype=float)
        assert np.allclose(a, b, rtol=1e-10, atol=1e-10)

    undefined = []
    extremes = []
    grid = [int(x) for x in primary.iloc[0].directions.split(';')]
    labels = [(g, d) for g in GOODS for d in [*grid, -1]]
    for reporter in (392, 410):
        x = cube(data, reporter, GOODS, grid, 2024).reshape(96, -1)
        assert np.isfinite(x).all()
        a = weights(x.reshape(96, len(GOODS), len(grid) + 1), periods(2024)//100, 2017, 2024)
        used = a.max(axis=1) > 0
        for case, lag, kind in [('monthly_lag1', 1, 'symmetric'),
                                ('ordinary_pct_yoy', 12, 'ordinary')]:
            g = growth(x, lag, kind)
            for t, j in np.argwhere(np.isnan(g) & used[None, :]):
                product, destination = labels[j]
                undefined.append(dict(case=case, reporter=reporter, period=int(periods(2024)[t+lag]),
                    cmdCode=product, destination=destination,
                    previous_usd=float(x[t, j]), current_usd=float(x[t+lag, j]),
                    reason='zero_growth_denominator', positive_fixed_weight=True))
            if kind == 'ordinary':
                candidates = np.argwhere(np.isfinite(g) & used[None, :])
                order = np.argsort(np.abs(g[candidates[:, 0], candidates[:, 1]]))[-10:][::-1]
                for index in order:
                    t, j = candidates[index]
                    product, destination = labels[j]
                    extremes.append(dict(case=case, reporter=reporter, period=int(periods(2024)[t+lag]),
                        cmdCode=product, destination=destination,
                        previous_usd=float(x[t, j]), current_usd=float(x[t+lag, j]),
                        ordinary_growth_pp=float(100*g[t, j])))
    undefined_frame = pd.DataFrame(undefined)
    for row in summary[summary.status.eq('unobserved_growth')].itertuples():
        count = len(undefined_frame[undefined_frame['case'].eq(row.case) & undefined_frame.reporter.eq(row.reporter)])
        assert count == int(row.unobserved)
    undefined_frame.to_csv(out / 'growth_observability.csv', index=False)
    pd.DataFrame(extremes).to_csv(out / 'ordinary_growth_extremes.csv', index=False)
    payload = dict(primary_complete=True, primary_logical_cells=len(coverage),
        source_archives_verified=len(bundles), archived_logical_cells=len(archived),
        manifest_logical_cells=len(manifest), source_manifest_sha256=quality['source_manifest_sha256'],
        monthly_panel_sha256=panel_sha, protocol_sha256=quality['protocol_sha256'],
        cases=expected_cases, country_case_status_counts=summary.status.value_counts().to_dict(),
        interval_rows=len(intervals), bootstrap_repetitions=1999, bootstrap_blocks=[12, 6],
        max_saved_series_variance_error_pp2=direct_error,
        max_covariance_variance_identity_error=float(checks.variance_identity_max_error.max()),
        max_shapley_add_up_error=float(checks.shapley_add_up_error.max()),
        max_actual_aggregate_identity_error=float(identity.max_error.max()),
        initial_window_reproduced=True, undefined_growth_rows=len(undefined),
        optional_2025_ready=quality['extension_analysis_ready'], causal_identification=False,
        primary_delta_sd_intervals_include_zero={str(r):bool(((intervals.reporter.eq(r)) &
            intervals.metric.eq('delta_sd_pp') & intervals.block_months.eq(12) &
            intervals.ci_low.le(0) & intervals.ci_high.ge(0)).any()) for r in (392, 410)})
    (out / 'final_audit.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
