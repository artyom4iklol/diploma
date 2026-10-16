"""Render research tables and monochrome scientific figures from verified results.

This script refuses partial panels and never substitutes synthetic observations.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/monthly'
FIG=OUT/'figures'
COUNTRIES={392:'Япония',410:'Республика Корея'}
STATE_LABELS={'initial':'Структура 2017', 'product_change':'Только товарные доли 2024',
              'geography_change':'Только география 2024', 'final':'Структура 2024'}
CASE_LABELS={'primary':'Основная оценка', 'top5':'Первые 5 кандидатов', 'top12':'Первые 12 кандидатов',
    'include_parts':'С частями HS854290', 'cn_hk_combined':'Китай и Гонконг вместе',
    'monthly_lag1':'Месячный рост, лаг 1', 'quarterly_yoy':'Квартальный рост г/г',
    'ordinary_pct_yoy':'Обычный процентный рост г/г', 'sigma_2018_2020':'Матрица 2018–2020',
    'sigma_2021_2024':'Матрица 2021–2024', 'temporal_2018_2020':'Веса 2017/2020: окно 2018–2020',
    'temporal_2021_2024':'Веса 2017/2020: окно 2021–2024', 'extension_2025':'Расширение до 2025'}


def number(x,digits=2):
    if pd.isna(x):return '—'
    return f'{x:,.{digits}f}'.replace(',',' ').replace('.',',')


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |',
                      *['| '+' | '.join(map(str,row))+' |' for row in rows]])


def interval_text(intervals,reporter,metric,block=12):
    row=intervals[(intervals.reporter.eq(reporter))&(intervals.metric.eq(metric))
                  &(intervals.block_months.eq(block))].iloc[0]
    return f"[{number(row.ci_low)}; {number(row.ci_high)}]"


def save_figure(fig,name):
    fig.savefig(FIG/f'{name}.png',dpi=190,facecolor='white',bbox_inches='tight')
    fig.savefig(FIG/f'{name}.svg',facecolor='white',bbox_inches='tight')
    plt.close(fig)


def figures(annual,observed,states,intervals,summary):
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(10,3.5),layout='constrained')
    for reporter,style in [(392,'-o'),(410,'--s')]:
        d=annual[annual.reporter.eq(reporter)&~annual.include_parts]
        axes[0].plot(d.year,d.hhi,style,color='black',markersize=3,label=COUNTRIES[reporter])
        axes[1].plot(d.year,100*d.memory_share,style,color='black',markersize=3,label=COUNTRIES[reporter])
    axes[0].set(title='Географическая концентрация',ylabel='HHI, все направления')
    axes[1].set(title='Доля памяти в готовых интегральных схемах',ylabel='% стоимости экспорта')
    for ax in axes:
        ax.grid(axis='y',color='.88',linewidth=.5);ax.set_xlabel('Год')
    axes[0].legend(frameon=False)
    save_figure(fig,'annual_structure')

    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained',sharey=True)
    labels=['2017','Товарные\nдоли 2024','География\n2024','2024']
    for ax,(reporter,country) in zip(axes,COUNTRIES.items()):
        d=states[states.reporter.eq(reporter)].set_index('state').loc[list(STATE_LABELS)]
        cis=intervals[intervals.reporter.eq(reporter)&intervals.block_months.eq(12)].set_index('metric')
        low=np.array([cis.loc[f'{state}_sd_pp','ci_low'] for state in STATE_LABELS])
        high=np.array([cis.loc[f'{state}_sd_pp','ci_high'] for state in STATE_LABELS])
        # Percentile limits are drawn directly; they need not surround the point estimate.
        for x,estimate,lo,hi in zip(range(4),d.sd_pp,low,high):
            ax.plot([x,x],[lo,hi],color='black',linewidth=1)
            ax.plot([x-.06,x+.06],[lo,lo],color='black',linewidth=1)
            ax.plot([x-.06,x+.06],[hi,hi],color='black',linewidth=1)
            ax.plot(x,estimate,'o',color='black',markersize=5)
        ax.set(title=country,xticks=range(4),xticklabels=labels,ylim=(0,None))
        ax.grid(axis='y',color='.88',linewidth=.5)
    axes[0].set_ylabel('Условное стандартное отклонение, п.п.')
    fig.suptitle('Фиксированные структуры; ковариация 2018–2024; 95% условные интервалы')
    save_figure(fig,'conditional_volatility')

    fig,axes=plt.subplots(1,2,figsize=(10,3.5),layout='constrained')
    metrics=['mix_variance_pp2','geography_variance_pp2']
    for ax,(reporter,country) in zip(axes,COUNTRIES.items()):
        d=summary[summary.reporter.eq(reporter)].iloc[0]
        cis=intervals[intervals.reporter.eq(reporter)&intervals.block_months.eq(12)].set_index('metric')
        for y,metric in enumerate(metrics):
            lo,hi=cis.loc[metric,['ci_low','ci_high']]
            ax.plot([lo,hi],[y,y],color='black')
            ax.plot(d[metric],y,'o',color='black')
        ax.axvline(0,color='.5',linewidth=.7)
        ax.set(title=country,yticks=[0,1],yticklabels=['Товарные доли','География'],ylim=(1.6,-.6),
               xlabel='Вклад в изменение дисперсии, п.п.²')
        ax.grid(axis='x',color='.88',linewidth=.5)
    fig.suptitle('Разложение Шепли; 95% интервалы, блок 12 месяцев')
    save_figure(fig,'variance_decomposition')

    fig,ax=plt.subplots(figsize=(10,3.5),layout='constrained')
    for reporter,style in [(392,'-'),(410,'--')]:
        d=observed[observed.reporter.eq(reporter)&~observed.include_parts&observed.lag.eq(12)]
        dates=pd.to_datetime(d.period.astype(str),format='%Y%m')
        ax.plot(dates,d.growth_pp,style,color='black',label=COUNTRIES[reporter],linewidth=1.1)
    ax.axhline(0,color='.6',linewidth=.7)
    ax.set(title='Фактический рост стоимости экспорта готовых интегральных схем',
           ylabel='Симметричный рост г/г, %',xlabel='Месяц')
    ax.legend(frameon=False,ncol=2);ax.grid(axis='y',color='.88',linewidth=.5)
    save_figure(fig,'observed_growth')


def main():
    quality=json.loads((OUT/'data_quality.json').read_text())
    validation=json.loads((OUT/'analysis_validation.json').read_text())
    assert quality['analysis_ready'],'Incomplete or unreconciled data'
    assert quality['monthly_panel_sha256']==validation['monthly_panel_sha256']
    assert hashlib.sha256((ROOT/'data/monthly_panel_full.csv.gz').read_bytes()).hexdigest()==validation['monthly_panel_sha256']
    states=pd.read_csv(OUT/'risk_states.csv')
    summary=pd.read_csv(OUT/'risk_summary.csv')
    intervals=pd.read_csv(OUT/'risk_intervals.csv')
    annual=pd.read_csv(OUT/'annual_indicators_from_months.csv')
    observed=pd.read_csv(OUT/'observed_growth.csv')
    components=pd.read_csv(OUT/'risk_components.csv')
    drivers=pd.read_csv(OUT/'risk_drivers.csv')
    grid=pd.read_csv(OUT/'risk_grid.csv')
    primary=summary[summary.case.eq('primary')]
    assert len(primary)==2 and primary.status.eq('ok').all(),'Primary estimates unavailable'
    ps=states[states.case.eq('primary')]
    pi=intervals[intervals.case.eq('primary')]
    figures(annual,observed,ps,pi,primary)
    data=pd.read_csv(ROOT/'data/monthly_panel_full.csv.gz')
    labels=data[['partnerCode','partnerDesc']].drop_duplicates('partnerCode').set_index('partnerCode').partnerDesc.to_dict()
    labels[-1]='Остальные направления (единая группа)'
    paragraphs=[]
    for _,r in primary.iterrows():
        reporter=int(r.reporter)
        d=ps[ps.reporter.eq(reporter)].set_index('state')
        ci=pi[(pi.reporter.eq(reporter))&pi.block_months.eq(12)&pi.metric.eq('delta_sd_pp')].iloc[0]
        uncertainty=('Условный интервал изменения включает ноль; знак точечной оценки не считается устойчиво установленным.'
                     if ci.ci_low<=0<=ci.ci_high else
                     'Условный интервал изменения не включает ноль при этом способе ресэмплирования; это не устраняет неопределенность модели и источника.')
        paragraphs.append(f"**{COUNTRIES[reporter]}.** При одной матрице колебаний 2018–2024 гг. стандартное отклонение синтетического индекса равно {number(d.loc['initial','sd_pp'])} п.п. для структуры 2017 г. и {number(d.loc['final','sd_pp'])} п.п. для структуры 2024 г. Изменение — {number(r.delta_sd_pp)} п.п.; 95% условный интервал {interval_text(pi,reporter,'delta_sd_pp')}. HHI на всех направлениях меняется с {number(d.loc['initial','hhi_all_destinations'],5)} до {number(d.loc['final','hhi_all_destinations'],5)}; на расчетной сетке — с {number(d.loc['initial','hhi_matched_grid'],5)} до {number(d.loc['final','hhi_matched_grid'],5)}. {uncertainty}")
    rows=[]
    for _,r in ps.iterrows():
        rows.append([COUNTRIES[int(r.reporter)],STATE_LABELS[r.state],number(r.sd_pp),number(r.mean_growth_pp),
                     number(r.hhi_all_destinations,5),number(r.hhi_matched_grid,5),number(100*r.residual_share)])
    states_table=table(['Страна','Структура','SD, п.п.','Средний рост индекса, %','HHI полный','HHI сетки','Остаток, %'],rows)
    decomposition_table=table(['Страна','Изменение дисперсии, п.п.²','Товарный вклад, п.п.²','95% интервал','Географический вклад, п.п.²','95% интервал'],
        [[COUNTRIES[int(r.reporter)],number(r.delta_variance_pp2),number(r.mix_variance_pp2),interval_text(pi,int(r.reporter),'mix_variance_pp2'),
          number(r.geography_variance_pp2),interval_text(pi,int(r.reporter),'geography_variance_pp2')] for _,r in primary.iterrows()])
    sensitivity_rows=[]
    for _,r in summary.iterrows():
        sensitivity_rows.append([CASE_LABELS.get(r.case,r.case),COUNTRIES[int(r.reporter)],r.status,
            number(r.get('delta_sd_pp')),number(r.get('mix_variance_pp2')),number(r.get('geography_variance_pp2')),
            number(r.n,0)])
    sensitivity_table=table(['Вариант','Страна','Статус','ΔSD, п.п.','Товарный вклад, п.п.²','Географический вклад, п.п.²','N'],sensitivity_rows)
    grid_rows=[]
    for _,r in grid[grid.case.eq('primary')].iterrows():
        grid_rows.append([f'{int(r.candidate)} — {labels.get(int(r.candidate),r.candidate)}',number(100*r.baseline_mean_share),
                          'Отдельно' if r.retained else 'В остатке',int(r.unobserved_growth_cells)])
    grid_table=table(['Кандидат','Начальная средняя доля, %','Решение','Ненаблюдаемые темпы'],grid_rows)
    component_rows=[]
    component_names={'diagonal':'Диагональные дисперсии','same_product_different_markets':'Один товар, разные рынки',
        'same_market_different_products':'Один рынок, разные товары','different_products_and_markets':'Разные товары и рынки'}
    for reporter in COUNTRIES:
        c=components[components.case.eq('primary')&components.reporter.eq(reporter)].pivot(index='component',columns='state',values='variance_pp2')
        for key,name in component_names.items():
            component_rows.append([COUNTRIES[reporter],name,number(c.loc[key,'initial']),number(c.loc[key,'final']),
                                   number(c.loc[key,'final']-c.loc[key,'initial'])])
    component_table=table(['Страна','Компонент','2017, п.п.²','2024, п.п.²','Изменение, п.п.²'],component_rows)
    driver_rows=[]
    d=drivers[drivers.case.eq('primary')].groupby(['reporter','cmdCode'])[['mix_variance_pp2','geography_variance_pp2']].sum().reset_index()
    for _,r in d.iterrows():
        driver_rows.append([COUNTRIES[int(r.reporter)],int(r.cmdCode),number(r.mix_variance_pp2),number(r.geography_variance_pp2)])
    driver_table=table(['Страна','HS6','Товарный вклад, п.п.²','Географический вклад, п.п.²'],driver_rows)
    annual_rows=[]
    for reporter in COUNTRIES:
        for year in [2017,2024]:
            r=annual[annual.reporter.eq(reporter)&~annual.include_parts&annual.year.eq(year)].iloc[0]
            annual_rows.append([COUNTRIES[reporter],year,number(r.export_usd/1e9,3),number(100*r.memory_share),number(r.hhi,5)])
    annual_table=table(['Страна','Год','Готовые ИС, млрд USD','Доля памяти, %','Географический HHI'],annual_rows)
    complete_months=quality['product_world_checks']
    limited=primary.grid_limited.astype(bool).any()
    warning=('\n\n**Ограниченная географическая сетка:** менее трех отдельных направлений. Детальный географический вывод ослаблен; нельзя считать это проверкой всех рынков.\n' if limited else '')
    report=f'''# Месячные результаты исследования экспорта интегральных схем

Основной период: 2017–2024 гг.; месячные темпы г/г: 2018–2024, по 84 наблюдения на экспортера. Расширение 2025 г.: {'собрано полностью и показано отдельным вариантом' if quality['complete_extension'] else 'неполно; не включено в основную оценку'}.

Вопрос: сопровождается ли изменение географической концентрации изменением условной волатильности, если раздельно заменить товарные доли и направления внутри товарных категорий? Все числа ниже вычислены из сохраненной месячной базы. Это историческое условное сравнение, не причинная оценка и не прогноз.

{chr(10).join(paragraphs)}{warning}

## Данные и контроль

Источник — UN Comtrade, прямые валовые экспортные стоимости Японии и Республики Корея в текущих долларах FOB. Основной объект — четыре вида готовых интегральных схем HS854231, 854232, 854233, 854239. Части HS854290 — чувствительность; HS8542 — контроль суммы. Это не вся полупроводниковая отрасль.

Проверено {quality['logical_request_checks']} логических ответов по стране, периоду и товару; {quality['unique_source_urls']} различных исходных URL; {quality['monthly_rows']} месячных строк, включая World. На полных срезах выполнено {complete_months} проверок суммы пяти HS6 против HS8542; максимальное относительное отклонение {quality['max_product_world_relative_gap']:.3g}. Проверок сумм по направлениям: {quality['product_partner_checks']}; непрошедших: {quality['product_partner_failures']}. Максимальное различие суммы месяцев и ранее сохраненной годовой стоимости: {number(100*quality['max_monthly_official_annual_relative_gap'],4)}%. Оно не исправлялось масштабированием; веса месячного анализа построены из месяцев.

{annual_table}

Китай и Гонконг разделены в основном варианте. `Other Asia, nes` сохраняет метку источника. Направления отражают заявленного партнера отгрузки, включая торговые узлы; это не распределение конечного потребления.

## Четыре состояния одной структуры

Для каждого экспортера матрица ковариаций одинакова во всех четырех состояниях. Темп ячейки: g = 2(x_t−x_{{t−12}})/(x_t+x_{{t−12}}). Фиксированная доля ячейки a_gd = w_g p_d|g. Дисперсия синтетического индекса V = a′Σa, стандартное отклонение S = 100√V. При двух нулях и положительном условном весе темп ненаблюдаем; он не заменяется нулевой волатильностью.

{states_table}

Остаточная группа не является единым экономическим рынком. Ее доля и различия двух HHI позволяют видеть цену агрегации. Средние темпы приведены описательно; снижение SD само по себе не означает рост доходности или благосостояния.

## Товарная структура и география

Два порядка замены усредняются по известному разложению Шепли. Вклады выражены в дисперсии (п.п.²); их сумма равна общему изменению. Они не суммируются как изменения стандартных отклонений.

{decomposition_table}

95% интервалы: парный круговой блочный бутстрэп, 1 999 повторов, блок 12 месяцев; все ячейки ресэмплируются совместно, сетка и веса фиксированы. Интервалы условны на исторической выборке и не включают всю неопределенность источника, модели, выбора периода и пересмотров. Перекрывающиеся годовые темпы и лишь семь лет дают мало независимых циклов. В `risk_intervals.csv` также сохранен блок 6 месяцев.

Вклады по товарным категориям:

{driver_table}

Разложение дисперсии на индивидуальные колебания и совместное движение:

{component_table}

Совместная компонента может иметь любой знак. Она отражает корреляцию номинальных отгрузок; из нее нельзя выделить экзогенный спрос или отдельно цены без дополнительных данных.

## Географическая сетка

Кандидаты ранжированы по средним страновым долям 2017–2020 гг. Для основной исторической оценки наблюдаемость проверяется по 2018–2024 гг. Рынки с ненаблюдаемыми темпами хотя бы по одному товару одной страны включены в общий остаток, без подбора замены по результату.

{grid_table}

Основная оценка использует всю историю для проверки наблюдаемости и не является прогнозом. Во временном разделении ниже сетка и веса 2017/2020 определяются только по начальному окну; данные при этом остаются позднее пересмотренными, а не историческими винтажами.

## Все предусмотренные варианты

{sensitivity_table}

Статус `unobserved_growth` означает отсутствие оценки из-за нулевого знаменателя при положительном условном весе. Такой вариант не удаляется из отчета. Чувствительности не независимы; простое число одинаковых знаков не заменяет статистическую проверку. Временное разделение сравнивает другие веса (2017/2020), поэтому его численный эффект не равен основному контрасту 2017/2024.

## Что можно утверждать для статьи

Получены количественные условные сравнения концентрации и волатильности конкретных структур. Их достаточность для публикации нужно оценивать по величине, интервалам и чувствительности географического вклада. Новый год, пара стран, HHI, ковариационная формула и разложение Шепли сами по себе новизной не являются. Ближайшие предшественники и границы сопоставления: `novelty_review.md`.

В работе нет идентификации эффекта экспортных ограничений, эффекта смены поставщиков на конечный спрос или оптимальной промышленной политики. Номинальная стоимость включает цены, качество, предложение и спрос; реэкспорт не позволяет определить конечного потребителя. HS854232 не разделяет DRAM, NAND и HBM на отдельные категории: результаты всей памяти нельзя приписывать одному из этих сегментов. Двух экспортеров нельзя превратить в большую независимую причинную панель числом товарно-рыночных ячеек.

## Рисунки

![Структура экспорта](results/monthly/figures/annual_structure.png)

![Условная волатильность](results/monthly/figures/conditional_volatility.png)

![Разложение дисперсии](results/monthly/figures/variance_decomposition.png)

![Фактический рост](results/monthly/figures/observed_growth.png)

## Воспроизведение

Сохраненные исходные пакеты, манифесты с URL и SHA256, `build_monthly_panel.py`, `analyze_monthly.py`, `build_monthly_report.py`. Точные проверки и числа: `results/monthly/`. SHA256 месячной панели: `{validation['monthly_panel_sha256']}`. Протокол: `monthly_analysis_protocol.md`; его сохраненный SHA256: `{validation['protocol_sha256']}`.
'''
    (ROOT/'monthly_results.md').write_text(report)
    print(json.dumps(dict(report=str(ROOT/'monthly_results.md'),figures=4,primary_estimates=2,
                          grid_limited=bool(limited)),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
