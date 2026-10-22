"""Verify additions in chapter 2, revision 24, from the frozen results.

No network requests or estimation; all outputs are derived chapter evidence.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

P = Path(__file__).resolve().parent
E = P / 'evidence'
PAIRS = [
    ('NFCI / AR + ESI', 'AR_ESI_NFCI', 'AR_ESI'),
    ('ANFCI / AR + ESI', 'AR_ESI_ANFCI', 'AR_ESI'),
    ('NFCI / HIST', 'AR_ESI_NFCI', 'HIST'),
    ('ANFCI / HIST', 'AR_ESI_ANFCI', 'HIST'),
    ('ANFCI / NFCI', 'AR_ESI_ANFCI', 'AR_ESI_NFCI'),
]

def verify_review(text):
    f = pd.read_csv(P.parent / 'revision19/results/ANFCI_forecasts.csv')
    diagnostics = []
    for label, model, benchmark in PAIRS:
        row = [label]
        for h in [1, 4]:
            a = f.query("variant == 'expanding' and information == 'historical' and h == @h")
            w = a.pivot(index='origin', columns='model', values='loss')
            assert w.notna().all().all()
            d = w[model] - w[benchmark]
            row += [f'{d.mean():+.4f}'.replace('.', ','), f'{int((d < 0).sum())}/{len(d)}']
            diagnostics.append(dict(model=model, benchmark=benchmark, h=h, n=len(d),
                                    mean_difference=float(d.mean()), median_difference=float(d.median()),
                                    wins=int((d < 0).sum()), ties=int((d == 0).sum()),
                                    losses=int((d > 0).sum())))
        assert '| ' + ' | '.join(row) + ' |' in text, label
    pd.DataFrame(diagnostics).to_csv(E / 'forecast_comparison_breadth.csv', index=False)

    # Independently recompute the scope and effect of the existing local GDP check.
    r18 = P.parent / 'revision18/results'
    scenarios = pd.read_csv(r18 / 'GDP_rounding_scenarios.csv')
    effects = pd.read_csv(r18 / 'GDP_rounding_full_sample_effect.csv')
    old = pd.read_csv(r18 / 'pilot_forecasts.csv').query("information == 'historical_NFCI'")
    assert len(scenarios) == len(effects) == 144
    assert set(scenarios.origin) == {'2022Q2'}
    assert set(scenarios.model) == {'HIST', 'AR', 'AR_ESI', 'AR_ESI_NFCI'}
    assert set(scenarios.variant) == {'expanding', 'rolling52'}
    assert set(scenarios.h) == {1, 4}
    np.testing.assert_allclose(sorted(scenarios.qoq_scenario.unique()), [.55, .60, .65])
    np.testing.assert_allclose(sorted(scenarios.yoy_scenario.unique()), [5.35, 5.40, 5.45])
    keys = ['variant', 'h', 'model']
    means = old.groupby(keys).agg(base=('loss', 'mean'), n=('loss', 'size')).reset_index()
    single = old[old.origin.eq('2022Q2')][keys + ['loss']].rename(columns={'loss': 'old_loss'})
    calculated = scenarios.merge(means, on=keys, validate='many_to_one').merge(single, on=keys, validate='many_to_one')
    calculated['expected_mean'] = calculated.base + (calculated.loss - calculated.old_loss) / calculated.n
    both = calculated.merge(effects, on=keys + ['qoq_scenario', 'yoy_scenario'], validate='one_to_one')
    np.testing.assert_allclose(both.expected_mean, both.full_sample_mean_loss, atol=1e-12)
    maximum_change = float((both.full_sample_mean_loss - both.base).abs().max())
    old_maximum = json.loads((r18 / 'final_validation.json').read_text())['maximum_full_sample_mean_loss_change']
    assert abs(maximum_change - old_maximum) < 1e-12
    assert maximum_change < .0001

    # Check the concrete algebraic example directly from coefficients and predictor history.
    coeff = pd.read_csv(P.parent / 'revision19/results/ANFCI_coefficients.csv')
    coeff = coeff.query("variant == 'expanding' and information == 'historical' and origin == '2020Q4' and h == 4").set_index('model')
    hist = pd.read_csv(P.parent / 'revision19/results/vintaged_model_frames_ANFCI.csv')
    current = hist[hist.origin.eq('2020Q4') & hist.quarter.eq('2020Q4')].iloc[0]
    parts = {
        'base_growth_addend': float(coeff.loc['AR_ESI', 'gx'] * current.gx),
        'ANFCI_model_growth_addend': float(coeff.loc['AR_ESI_ANFCI', 'gx'] * current.gx),
        'ANFCI_direct_addend': float(coeff.loc['AR_ESI_ANFCI', 'anfci'] * current.anfci),
    }
    for key, expected in [('base_growth_addend', '47,43'), ('ANFCI_model_growth_addend', '4,10'), ('ANFCI_direct_addend', '1,94')]:
        assert f'{parts[key]:.2f}'.replace('.', ',') == expected
        assert expected in text
    assert parts['ANFCI_direct_addend'] > 0
    result = {
        'date': '2026-10-18', 'model_refit': False,
        'paired_comparisons_verified': len(diagnostics),
        'new_table_2_3_verified': True,
        'rounding_scenarios': len(scenarios),
        'rounding_check_origin': '2022Q2',
        'rounding_includes_ANFCI': False,
        'rounding_refits_future_dates': False,
        'maximum_local_rounding_mean_loss_change': maximum_change,
        'forecast_2021_01_15_h4_addends': parts,
    }
    (E / 'review_diagnostics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result

if __name__ == '__main__':
    E.mkdir(exist_ok=True)
    print(json.dumps(verify_review((P / 'Chapter_2_Empirical_Analysis.md').read_text()), ensure_ascii=False, indent=2))
