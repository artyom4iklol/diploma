"""Bounded, post-estimation Chapter 3 scenarios; never modify the primary model."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RISK = HERE.parent / 'risk_extension'
sys.path.insert(0, str(RISK))
from analyze_monthly import cube, growth, periods, weights

GOODS = (854231, 854232, 854233, 854239)
SHIFTS = (-5., -2.5, 0., 2.5, 5.)
SEED, REPETITIONS = 20261019, 1999


def main():
    paths = [RISK/'data/monthly_panel_full.csv.gz',
             RISK/'results/monthly/risk_summary.csv',
             RISK/'results/monthly/risk_states.csv',
             HERE/'chapter3_scenario_protocol.md', RISK/'analyze_monthly.py']
    panel = pd.read_csv(paths[0])
    summary = pd.read_csv(paths[1])
    states = pd.read_csv(paths[2])
    dirs = summary.loc[summary.case.eq('primary'), 'directions'].unique()
    assert len(dirs) == 1
    directions = [int(x) for x in dirs[0].split(';')]
    records, interval_rows, window_rows, group_rows, check_rows = [], [], [], [], []
    for reporter in (392, 410):
        x = cube(panel, reporter, GOODS, directions, 2024)
        g = growth(x, 12)
        assert g.shape == (84, 4, 9) and np.isfinite(g).all()
        annual = x[periods(2024)//100 == 2024].sum(axis=0)
        a0 = annual.sum(axis=1)/annual.sum()
        b0 = annual/annual.sum(axis=1)[:, None]
        m0 = a0[1]
        aa = []
        for shift in SHIFTS:
            m = m0 + shift/100
            assert 0 < m < 1
            a = a0 * (1-m)/(1-m0)
            a[1] = m
            aa.append(a)
        aa = np.array(aa)
        w = (aa[:, :, None] * b0[None, :, :]).reshape(5, 36).T
        assert np.all(w >= 0) and np.allclose(w.sum(axis=0), 1, atol=1e-13)
        y = g.reshape(84, 36) @ w
        v = y.var(axis=0, ddof=1)*10000
        sd = np.sqrt(v)
        base = float(states.loc[states.case.eq('primary') & states.reporter.eq(reporter)
                               & states.state.eq('final'), 'variance_pp2'].iloc[0])
        base_error = abs(v[2]-base)
        assert base_error < 1e-8
        assert np.allclose(w[:, 2], weights(x, periods(2024)//100, 2017, 2024)[:, 3], atol=1e-13)
        product_index = (g*b0).sum(axis=2)
        other = np.array([0, 2, 3])
        memory = product_index[:, 1]
        rest = product_index[:, other] @ (a0[other]/(1-m0))
        vm, vo = np.var(memory, ddof=1)*10000, np.var(rest, ddof=1)*10000
        cov = np.cov(memory, rest, ddof=1)[0, 1]*10000
        group_rows.append(dict(reporter=reporter, memory_variance_pp2=vm,
            remaining_variance_pp2=vo, covariance_pp2=cov,
            correlation=float(np.corrcoef(memory, rest)[0, 1])))
        max_identity = 0.
        for i, shift in enumerate(SHIFTS):
            m = aa[i, 1]
            components = [m*m*vm, (1-m)**2*vo, 2*m*(1-m)*cov]
            error = abs(sum(components)-v[i])
            max_identity = max(max_identity, error)
            assert error < 1e-8
            records.append(dict(reporter=reporter, shift_pp=shift, memory_share_pct=m*100,
                sd_pp=sd[i], delta_sd_pp=sd[i]-sd[2], variance_pp2=v[i],
                product_hhi=float(np.square(aa[i]).sum()),
                product_shares=aa[i].tolist(), memory_component_pp2=components[0],
                remaining_component_pp2=components[1], cross_component_pp2=components[2],
                remaining_export_change_pct_if_memory_unchanged=100*((m0/(1-m0))*((1-m)/m)-1),
                total_export_change_pct_if_memory_unchanged=100*(m0/m-1),
                extra_remaining_export_usd_if_memory_unchanged=float(annual.sum()*(m0/m-1))))
        for block in (12, 6):
            rng = np.random.default_rng(SEED)
            starts = rng.integers(0, len(y), size=(REPETITIONS, int(np.ceil(len(y)/block))))
            idx = ((starts[:, :, None]+np.arange(block)) % len(y)).reshape(REPETITIONS, -1)[:, :len(y)]
            bs = np.std(y[idx], axis=1, ddof=1)*100
            diff = bs-bs[:, [2]]
            assert np.all(diff[:, 2] == 0)
            for i, shift in enumerate(SHIFTS):
                lo, hi = np.quantile(diff[:, i], [.025, .975])
                interval_rows.append(dict(reporter=reporter, shift_pp=shift, block_months=block,
                    ci_low=float(lo), ci_high=float(hi), repetitions=REPETITIONS, seed=SEED))
        years = periods(2024)[12:]//100
        for low, high in ((2018, 2020), (2021, 2024)):
            mask = (years >= low)&(years <= high)
            s = np.std(y[mask], axis=0, ddof=1)*100
            for i, shift in enumerate(SHIFTS):
                window_rows.append(dict(reporter=reporter, window=f'{low}–{high}', n=int(mask.sum()),
                    shift_pp=shift, sd_pp=float(s[i]), delta_sd_pp=float(s[i]-s[2])))
        check_rows.append(dict(reporter=reporter, observed_growth_cells=int(g.size),
            finite_all=True, baseline_error_pp2=base_error, variance_identity_error_pp2=max_identity,
            weights_nonnegative_and_sum_one=True, base_weights_equal_saved_model=True,
            zero_shift_bootstrap_exact_zero=True))
    out = dict(protocol='chapter3_scenario_protocol.md', purpose='Exploratory conditional historical scenarios, not a forecast or causal effect',
        weight_year=2024, growth_period='2018–2024', shifts_pp=SHIFTS,
        scenarios=records, paired_intervals=interval_rows, windows=window_rows,
        group_dynamics=group_rows, checks=check_rows,
        input_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (HERE/'chapter3_evidence.json').write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    flat = pd.DataFrame(records).drop(columns='product_shares')
    flat.to_csv(HERE/'chapter3_scenarios.csv', index=False, float_format='%.12g')
    pd.DataFrame(interval_rows).to_csv(HERE/'chapter3_scenario_intervals.csv', index=False, float_format='%.12g')
    pd.DataFrame(window_rows).to_csv(HERE/'chapter3_scenario_windows.csv', index=False, float_format='%.12g')
    print(flat[['reporter','shift_pp','memory_share_pct','sd_pp','delta_sd_pp','product_hhi','remaining_export_change_pct_if_memory_unchanged']].to_string(index=False))
    print(pd.DataFrame(interval_rows).query('block_months == 12').to_string(index=False))
    print(pd.DataFrame(window_rows).query('shift_pp == -5').to_string(index=False))


if __name__ == '__main__':
    main()
