"""Monochrome figures from the saved exploratory diagnostics only."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results'
FIG = OUT/'figures'
COUNTRIES = {392:'Япония', 410:'Республика Корея'}


def save(fig, name):
    for extension in ('png', 'svg'):
        path = FIG/f'{name}.{extension}'
        fig.savefig(path, dpi=190, bbox_inches='tight', facecolor='white')
        if extension == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
        'axes.spines.top':False, 'axes.spines.right':False, 'svg.fonttype':'none'})
    d = pd.read_csv(OUT/'memory_share_decomposition.csv')
    d = d[d['case'].eq('primary') & d.block_months.eq(12)]
    factors = ['memory_share', 'within_nonmemory_mix', 'geography']
    labels = ['Доля памяти', 'Состав остальных схем', 'География']
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.6), layout='constrained')
    for ax, (reporter, name) in zip(axes, COUNTRIES.items()):
        rows = d[d.reporter.eq(reporter)].set_index('factor').loc[factors]
        for y, row in enumerate(rows.itertuples()):
            ax.plot([row.ci_low, row.ci_high], [y, y], color='black')
            ax.plot(row.estimate_variance_pp2, y, 'o', color='black', markersize=5)
        ax.axvline(0, color='.55', linewidth=.8)
        ax.set(title=name, yticks=range(3), yticklabels=labels, ylim=(2.6, -.6),
               xlabel='Вклад в изменение дисперсии, п.п.²')
        ax.grid(axis='x', color='.9', linewidth=.5)
    fig.suptitle('Дополнительное разложение: структуры 2017/2024; 95% условные интервалы\n'
                 'Анализ после основной оценки; блок 12 месяцев; доли и сетка фиксированы', fontsize=11)
    save(fig, 'memory_composition_attribution')

    loo = pd.read_csv(OUT/'leave_one_year_out.csv')
    loo = loo[loo['case'].eq('primary')]
    main_results = pd.read_csv(ROOT.parent/'results/monthly/risk_summary.csv')
    main_results = main_results[main_results['case'].eq('primary')].set_index('reporter')
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.6), layout='constrained')
    for ax, (reporter, name) in zip(axes, COUNTRIES.items()):
        rows = loo[loo.reporter.eq(reporter)]
        ax.plot(rows.omitted_year, rows.delta_sd_pp, '-o', color='black', markersize=4,
                label='После исключения года')
        ax.axhline(main_results.loc[reporter, 'delta_sd_pp'], color='.3', linestyle='--',
                   linewidth=1, label='Полная основная оценка')
        ax.axhline(0, color='.65', linewidth=.8)
        ax.set(title=name, xlabel='Исключенный год', ylabel='Изменение условного SD, п.п.',
               xticks=range(2018, 2025))
        ax.grid(axis='y', color='.9', linewidth=.5)
    axes[0].legend(frameon=False, fontsize=8, loc='lower left')
    fig.suptitle('Чувствительность к исключению одного года из истории колебаний\n'
                 'Структуры 2017/2024 и географическая сетка остаются фиксированными', fontsize=11)
    save(fig, 'year_omission_stability')
    print('Two monochrome diagnostic figures saved as PNG and SVG; no manuscript generated.')


if __name__ == '__main__':
    main()
