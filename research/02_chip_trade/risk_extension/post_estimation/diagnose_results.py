"""Exploratory follow-up of the frozen primary estimates; no manuscript output."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from analyze_monthly import GOODS, SEED, cube, growth, periods, shapley, weights

OUT = HERE / 'results'
NBOOT = 1999
BITS = list(itertools.product((0, 1), repeat=3))
INDEX = {b: j for j, b in enumerate(BITS)}
ORIGINAL = [INDEX[b] for b in ((0, 0, 0), (1, 1, 0), (0, 0, 1), (1, 1, 1))]
PRODUCTS = {854231: 'Processors and controllers', 854232: 'Memories',
            854233: 'Amplifiers', 854239: 'Other integrated circuits', 854290: 'Parts'}


def grouped_weights(w0, p0, w1, p1, memory_index):
    """Eight structures: memory share, relative non-memory mix, geography."""
    vectors = []
    other = np.arange(len(w0)) != memory_index
    m = (w0[memory_index], w1[memory_index])
    proportions = (w0[other] / (1-m[0]), w1[other] / (1-m[1]))
    for im, ir, ip in BITS:
        w = np.empty_like(w0)
        w[memory_index] = m[im]
        w[other] = (1-m[im])*proportions[ir]
        vectors.append((w[:, None]*(p0, p1)[ip]).ravel())
    a = np.stack(vectors, axis=1)
    assert np.allclose(a.sum(axis=0), 1) and np.all(a >= 0)
    return a


def grouped_split(v):
    """Nested symmetric allocation, preserving the original geographic effect."""
    memory = 0.0
    nonmemory = 0.0
    for p in (0, 1):
        v00, v10, v01, v11 = (v[..., INDEX[b]] for b in
            ((0, 0, p), (1, 0, p), (0, 1, p), (1, 1, p)))
        memory = memory + .25*((v10-v00)+(v11-v01))
        nonmemory = nonmemory + .25*((v01-v00)+(v11-v10))
    delta, mix, geo = shapley(v[..., ORIGINAL])
    assert np.allclose(memory+nonmemory, mix, rtol=1e-9, atol=1e-10)
    return np.stack((memory, nonmemory, geo), axis=-1)


def cell_split(cov_a, a):
    mix = .5*((a[:, 1]-a[:, 0])*(cov_a[..., 1]+cov_a[..., 0])
              +(a[:, 3]-a[:, 2])*(cov_a[..., 3]+cov_a[..., 2]))
    geo = .5*((a[:, 2]-a[:, 0])*(cov_a[..., 2]+cov_a[..., 0])
              +(a[:, 3]-a[:, 1])*(cov_a[..., 3]+cov_a[..., 1]))
    return np.stack((mix, geo), axis=-1)


def prepare(data, row):
    case, reporter = row['case'], int(row['reporter'])
    goods = (*GOODS, 854290) if case == 'include_parts' else GOODS
    directions = [int(x) for x in row['directions'].split(';')]
    if case == 'cn_hk_combined':
        data = data.copy()
        data.loc[data.partnerCode.eq(344), 'partnerCode'] = 156
    x = cube(data, reporter, goods, directions, 2024)
    years = periods(2024)//100
    endpoints = []
    for year in (int(row['initial_year']), int(row['final_year'])):
        amounts = x[years == year].sum(axis=0)
        w = amounts.sum(axis=1)/amounts.sum()
        p = amounts/amounts.sum(axis=1)[:, None]
        endpoints.append((w, p))
    (w0, p0), (w1, p1) = endpoints
    a8 = grouped_weights(w0, p0, w1, p1, goods.index(854232))
    a4 = weights(x, years, int(row['initial_year']), int(row['final_year']))
    assert np.allclose(a8[:, ORIGINAL], a4, atol=1e-14)
    quarterly = case == 'quarterly_yoy'
    lag = 1 if case == 'monthly_lag1' else (4 if quarterly else 12)
    if quarterly:
        x = x.reshape(-1, 3, len(goods), len(directions)+1).sum(axis=1)
        dates = periods(2024)[2::3]
    else:
        dates = periods(2024)
    kind = 'ordinary' if case == 'ordinary_pct_yoy' else 'symmetric'
    g = growth(x, lag, kind).reshape(len(x)-lag, -1)
    dates = dates[lag:]
    select = (dates//100 >= int(row['sigma_start'])) & (dates//100 <= int(row['sigma_end']))
    g, dates = g[select], dates[select]
    used = a8.max(axis=1) > 0
    assert np.isfinite(g[:, used]).all()
    g = np.nan_to_num(g, nan=0)
    assert len(g) == int(row['n'])
    return dict(g=g, dates=dates, a8=a8, a4=a4, goods=goods,
                directions=directions, quarterly=quarterly,
                memory_initial=float(w0[goods.index(854232)]),
                memory_final=float(w1[goods.index(854232)]))


def resample(g, a8, a4, block):
    rng = np.random.default_rng(SEED)
    n = len(g)
    nb = int(np.ceil(n/block))
    starts = rng.integers(0, n, size=(NBOOT, nb))
    indices = ((starts[:, :, None]+np.arange(block)) % n).reshape(NBOOT, -1)[:, :n]
    group_out = []
    cell_out = []
    v4_out = []
    diagonal_out = []
    for start in range(0, NBOOT, 200):
        z = g[indices[start:start+200]]
        z = z-z.mean(axis=1, keepdims=True)
        y8 = z@a8
        v8 = (y8*y8).sum(axis=1)/(n-1)
        cov_a = np.matmul(z.transpose(0, 2, 1), y8[:, :, ORIGINAL])/(n-1)
        cells = cell_split(cov_a, a4)
        v4 = v8[:, ORIGINAL]
        _, mix, geo = shapley(v4)
        assert np.allclose(cells.sum(axis=1), np.stack((mix, geo), axis=-1), atol=1e-10)
        group_out.append(grouped_split(v8))
        cell_out.append(cells)
        v4_out.append(v4)
        diagonal_out.append((z*z).sum(axis=1)/(n-1) @ (a4*a4))
    return (np.concatenate(group_out), np.concatenate(cell_out),
            np.concatenate(v4_out), np.concatenate(diagonal_out))


def main():
    OUT.mkdir(exist_ok=True)
    plan = json.loads((HERE/'diagnostic_plan.json').read_text())
    panel = ROOT/'data/monthly_panel_full.csv.gz'
    panel_sha = hashlib.sha256(panel.read_bytes()).hexdigest()
    assert panel_sha == plan['source_panel_sha256']
    quality = json.loads((ROOT/'results/monthly/data_quality.json').read_text())
    assert quality['analysis_ready']
    data = pd.read_csv(panel)
    summary = pd.read_csv(ROOT/'results/monthly/risk_summary.csv')
    old_intervals = pd.read_csv(ROOT/'results/monthly/risk_intervals.csv')
    old_drivers = pd.read_csv(ROOT/'results/monthly/risk_drivers.csv')
    labels = data[['partnerCode', 'partnerDesc']].drop_duplicates('partnerCode').set_index('partnerCode').partnerDesc.to_dict()
    labels[-1] = 'All remaining destinations'
    memory_rows, product_rows, destination_rows, cell_rows, status_rows = [], [], [], [], []
    loo_rows, bridge_rows = [], []
    covariance_rows = []
    max_reproduction_error = 0.0
    max_interval_error = 0.0
    for row in summary.to_dict('records'):
        case, reporter = row['case'], int(row['reporter'])
        if row['status'] != 'ok':
            status_rows.append(dict(case=case, reporter=reporter, status=row['status'],
                                    unobserved_growth_cells=int(row['unobserved'])))
            continue
        inp = prepare(data, row)
        g, a8, a4 = inp['g'], inp['a8'], inp['a4']
        cov = np.cov(g, rowvar=False, ddof=1)
        v8 = np.einsum('ij,ik,kj->j', a8, cov, a8)
        v4 = v8[ORIGINAL]
        delta, mix, geo = shapley(v4)
        expected = np.array([row[k] for k in ('delta_variance_pp2', 'mix_variance_pp2', 'geography_variance_pp2')])
        error = float(np.abs(np.array([delta, mix, geo])*10000-expected).max())
        max_reproduction_error = max(error, max_reproduction_error)
        assert np.allclose(np.array([delta, mix, geo])*10000, expected, rtol=1e-10, atol=1e-8)
        cells = cell_split(cov@a4, a4)*10000
        old = old_drivers[old_drivers['case'].eq(case) & old_drivers.reporter.eq(reporter)]
        assert np.allclose(cells, old[['mix_variance_pp2', 'geography_variance_pp2']], rtol=1e-10, atol=1e-8)
        grouped = grouped_split(v8)*10000
        for months in (12, 6):
            block = months//3 if inp['quarterly'] else months
            bgroups, bcells, bv4, bdiagonal = resample(g, a8, a4, block)
            assert np.allclose(np.stack(shapley(bdiagonal), axis=-1)+
                np.stack(shapley(bv4-bdiagonal), axis=-1),
                np.stack(shapley(bv4), axis=-1), rtol=1e-9, atol=1e-10)
            bgroups, bcells = bgroups*10000, bcells*10000
            group_ci = np.quantile(bgroups, [.025, .975], axis=0)
            for j, factor in enumerate(('memory_share', 'within_nonmemory_mix', 'geography')):
                memory_rows.append(dict(case=case, reporter=reporter, factor=factor, n=len(g),
                    initial_year=int(row['initial_year']), final_year=int(row['final_year']),
                    memory_share_initial=inp['memory_initial'], memory_share_final=inp['memory_final'],
                    estimate_variance_pp2=float(grouped[j]), ci_low=float(group_ci[0, j]), ci_high=float(group_ci[1, j]),
                    block_months=months, block_observations=block, repetitions=NBOOT, exploratory=True))
            point_diagonal = np.diag(cov) @ (a4*a4)
            for component, point_v, boot_v in (
                ('own_variances', point_diagonal, bdiagonal),
                ('cross_covariances', v4-point_diagonal, bv4-bdiagonal)):
                point_effects = np.array(shapley(point_v))*10000
                boot_effects = np.stack(shapley(boot_v), axis=-1)*10000
                component_ci = np.quantile(boot_effects, [.025, .975], axis=0)
                for j, effect in enumerate(('total_change', 'product_mix', 'geography')):
                    covariance_rows.append(dict(case=case, reporter=reporter, component=component,
                        factor=effect, estimate_variance_pp2=float(point_effects[j]),
                        ci_low=float(component_ci[0, j]), ci_high=float(component_ci[1, j]),
                        block_months=months, repetitions=NBOOT, exploratory=True))
            shapes = (len(inp['goods']), len(inp['directions'])+1, 2)
            product_point = cells.reshape(shapes).sum(axis=1)
            bproduct = bcells.reshape((NBOOT, *shapes)).sum(axis=2)
            product_ci = np.quantile(bproduct, [.025, .975], axis=0)
            for j, code in enumerate(inp['goods']):
                for f, factor in enumerate(('product_mix', 'geography')):
                    product_rows.append(dict(case=case, reporter=reporter, cmdCode=code, product=PRODUCTS[code],
                        factor=factor, estimate_variance_pp2=float(product_point[j, f]),
                        ci_low=float(product_ci[0, j, f]), ci_high=float(product_ci[1, j, f]),
                        block_months=months, repetitions=NBOOT, exploratory=True))
            if case == 'primary':
                destination_point = cells.reshape(shapes).sum(axis=0)
                bdestination = bcells.reshape((NBOOT, *shapes)).sum(axis=1)
                destination_ci = np.quantile(bdestination, [.025, .975], axis=0)
                cell_ci = np.quantile(bcells, [.025, .975], axis=0)
                for j, code in enumerate([*inp['directions'], -1]):
                    for f, factor in enumerate(('product_mix', 'geography')):
                        destination_rows.append(dict(case=case, reporter=reporter, destination=code,
                            destination_label=labels[code], factor=factor,
                            estimate_variance_pp2=float(destination_point[j, f]),
                            ci_low=float(destination_ci[0, j, f]), ci_high=float(destination_ci[1, j, f]),
                            block_months=months, repetitions=NBOOT, exploratory=True))
                for j, (code, destination) in enumerate(itertools.product(inp['goods'], [*inp['directions'], -1])):
                    for f, factor in enumerate(('product_mix', 'geography')):
                        cell_rows.append(dict(case=case, reporter=reporter, cmdCode=code, destination=destination,
                            destination_label=labels[destination], factor=factor,
                            estimate_variance_pp2=float(cells[j, f]), ci_low=float(cell_ci[0, j, f]),
                            ci_high=float(cell_ci[1, j, f]), block_months=months,
                            repetitions=NBOOT, exploratory=True))
                # Different implementation reproduces the original total intervals.
                bd, bm, bgeo = shapley(bv4)
                stats = dict(delta_variance_pp2=bd*10000, mix_variance_pp2=bm*10000,
                    geography_variance_pp2=bgeo*10000,
                    delta_sd_pp=100*(np.sqrt(bv4[:, 3])-np.sqrt(bv4[:, 0])))
                for metric, values in stats.items():
                    oldrow = old_intervals[old_intervals.reporter.eq(reporter) &
                        old_intervals.block_months.eq(months) & old_intervals.metric.eq(metric)].iloc[0]
                    bounds = np.quantile(values, [.025, .975])
                    err = float(np.abs(bounds-oldrow[['ci_low', 'ci_high']].to_numpy(dtype=float)).max())
                    max_interval_error = max(max_interval_error, err)
                    assert np.allclose(bounds, oldrow[['ci_low', 'ci_high']].to_numpy(dtype=float), rtol=1e-9, atol=1e-8)
        status_rows.append(dict(case=case, reporter=reporter, status='ok', n=len(g)))
        if case in ('primary', 'ordinary_pct_yoy'):
            for year in range(2018, 2025):
                keep = inp['dates']//100 != year
                v = np.var(g[keep]@a4, axis=0, ddof=1)
                d, m, ge = shapley(v)
                loo_rows.append(dict(case=case, reporter=reporter, omitted_year=year, n=int(keep.sum()),
                    delta_variance_pp2=float(d*10000), mix_variance_pp2=float(m*10000),
                    geography_variance_pp2=float(ge*10000),
                    delta_sd_pp=float(100*(np.sqrt(v[3])-np.sqrt(v[0]))), exploratory=True))
        if case == 'primary':
            early = g[inp['dates']//100 <= 2020]
            late = g[inp['dates']//100 >= 2021]
            ne, nl = len(early), len(late)
            difference = early.mean(axis=0)-late.mean(axis=0)
            pieces = {'within_2018_2020':(ne-1)/(len(g)-1)*np.cov(early, rowvar=False, ddof=1),
                      'within_2021_2024':(nl-1)/(len(g)-1)*np.cov(late, rowvar=False, ddof=1),
                      'between_window_means':ne*nl/(len(g)*(len(g)-1))*np.outer(difference, difference)}
            assert np.allclose(sum(pieces.values()), cov, rtol=1e-10, atol=1e-12)
            for name, matrix in pieces.items():
                d, m, ge = shapley(np.einsum('ij,ik,kj->j', a4, matrix, a4))
                bridge_rows.append(dict(reporter=reporter, covariance_piece=name,
                    delta_variance_pp2=float(d*10000), mix_variance_pp2=float(m*10000),
                    geography_variance_pp2=float(ge*10000), exploratory=True))
        print(json.dumps(dict(case=case, reporter=reporter, status='diagnosed')), flush=True)
    frames = {'memory_share_decomposition':memory_rows, 'product_attribution_intervals':product_rows,
        'destination_attribution_intervals':destination_rows, 'cell_attribution_intervals':cell_rows,
        'diagnostic_status':status_rows, 'leave_one_year_out':loo_rows, 'covariance_window_bridge':bridge_rows,
        'covariance_attribution_intervals':covariance_rows}
    for name, rows in frames.items():
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv', index=False)
    by_destination = old_drivers.groupby(['case', 'reporter', 'destination'], as_index=False)[
        ['mix_variance_pp2', 'geography_variance_pp2']].sum()
    by_destination['destination_label'] = by_destination.destination.map(labels)
    by_destination.to_csv(OUT/'destination_attribution_all_cases.csv', index=False)
    components = pd.read_csv(ROOT/'results/monthly/risk_components.csv')
    changes = components.pivot(index=['case', 'reporter', 'component'], columns='state', values='variance_pp2')
    changes['delta_variance_pp2'] = changes['final']-changes['initial']
    changes['mix_variance_pp2'] = .5*((changes['product_change']-changes['initial'])+
                                     (changes['final']-changes['geography_change']))
    changes['geography_variance_pp2'] = .5*((changes['geography_change']-changes['initial'])+
                                           (changes['final']-changes['product_change']))
    for (case, reporter), rows in changes.groupby(level=['case', 'reporter']):
        target = summary[summary['case'].eq(case) & summary.reporter.eq(reporter)].iloc[0]
        for metric in ('delta_variance_pp2', 'mix_variance_pp2', 'geography_variance_pp2'):
            assert np.isclose(rows[metric].sum(), target[metric], rtol=1e-10, atol=1e-8)
    changes.reset_index().to_csv(OUT/'covariance_components_change.csv', index=False)
    output = dict(phase='Exploratory follow-up; frozen primary estimates retained',
        diagnostic_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        monthly_panel_sha256=panel_sha, primary_protocol_sha256=quality['protocol_sha256'],
        cases=summary['case'].nunique(), country_cases=len(status_rows),
        completed=sum(x['status']=='ok' for x in status_rows),
        unavailable=[x for x in status_rows if x['status']!='ok'],
        primary_points_reproduced=True, original_bootstrap_intervals_reproduced=True,
        max_point_reproduction_error_pp2=max_reproduction_error,
        max_original_interval_reproduction_error=max_interval_error,
        bootstrap_repetitions=NBOOT, bootstrap_seed=SEED,
        intervals='Pointwise exploratory percentiles, fixed weights and grids; no multiplicity adjustment',
        grouped_memory_adds_to_original_product_effect=True,
        covariance_component_shapley_add_up=True,
        covariance_window_identity_pass=True, price_quantity_identification=False,
        causal_identification=False, manuscript_written=False,
        outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.csv'))})
    (OUT/'validation.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
