"""Publication-style monochrome figures and appendices from frozen results."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent
RISK=HERE.parent/'risk_extension'
ASSETS=HERE/'chapter2_assets'
ASSETS.mkdir(exist_ok=True)
E=json.loads((HERE/'chapter2_evidence.json').read_text())
fmt=lambda x,n=2:f'{float(x):.{n}f}'.replace('.',',').replace('-','−')
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.titlesize':10,
                     'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':9,
                     'axes.spines.top':False,'axes.spines.right':False,
                     'axes.linewidth':.65,'svg.fonttype':'none','savefig.facecolor':'white'})
NAMES={392:'Япония',410:'Республика Корея'}
LABELS={156:'Китай',344:'Гонконг',490:'Other Asia, nes',704:'Вьетнам',702:'Сингапур',
        608:'Филиппины',842:'США',764:'Таиланд',-1:'Остальные'}
GOODS={854231:'Процессоры и контроллеры',854232:'Память',854233:'Усилители',854239:'Прочие схемы'}
manifest=[]

def clean(ax,axis='y'):
    ax.grid(axis=axis,color='.88',lw=.5,zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=3,width=.6)

def save(fig,num,caption,note):
    stem=f'fig2_{num}'
    for ext in ['png','svg']:
        fig.savefig(ASSETS/f'{stem}.{ext}',dpi=240)
        if ext == 'svg':
            svg_path = ASSETS/f'{stem}.{ext}'
            svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
    manifest.append({'number':f'2.{num}','path':f'chapter2_assets/{stem}.png',
                     'caption':caption,'note':note,'sha256':hashlib.sha256((ASSETS/f'{stem}.png').read_bytes()).hexdigest()})
    plt.close(fig)

def prepare_figures():
    annual=pd.DataFrame(E['annual_totals']);prod=pd.DataFrame(E['annual_products'])
    geo=pd.DataFrame(E['annual_destination_grid']);states=pd.DataFrame(E['saved_results']['primary_states'])
    ints=pd.DataFrame(E['saved_results']['primary_intervals']);ints=ints[ints.block_months.eq(12)].set_index(['reporter','metric'])
    summary=pd.DataFrame(E['saved_results']['all_specifications']);primary=summary[summary.case.eq('primary')].set_index('reporter')
    observed=pd.read_csv(RISK/'results/monthly/observed_growth.csv');observed=observed[(~observed.include_parts)&observed.lag.eq(12)]
    fig,axs=plt.subplots(2,1,figsize=(6.5,4.6));fig.subplots_adjust(left=.12,right=.98,bottom=.11,top=.89,hspace=.45)
    for c,color,style in [(392,'black','-'),(410,'.4','--')]:
        a=annual[annual.reporterCode.eq(c)]
        axs[0].plot(a.refYear,a.export_usd/1e9,color=color,ls=style,lw=1.5,marker='o',ms=3,label=NAMES[c])
        g=observed[observed.reporter.eq(c)]
        axs[1].plot(pd.to_datetime(g.period.astype(str),format='%Y%m'),g.growth_pp,color=color,ls=style,lw=1.15)
    axs[0].set(ylabel='Стоимость, млрд долл.',xticks=range(2017,2025),ylim=(0,135));axs[0].legend(frameon=False,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.02),ncol=2)
    axs[1].axhline(0,color='.2',lw=.7);axs[1].set(ylabel='Симметричный темп, п.п.',ylim=(-65,60),xlim=(pd.Timestamp('2018-01-01'),pd.Timestamp('2024-12-31')))
    for ax in axs:clean(ax)
    save(fig,1,'Стоимость экспорта и фактические годовые темпы его изменения','Верхняя панель — годовые суммы; нижняя — месячные темпы год к году. Четыре категории интегральных схем без частей; текущие доллары США.')

    fig,axs=plt.subplots(1,2,figsize=(6.5,3.6),sharey=True);fig.subplots_adjust(left=.09,right=.98,bottom=.29,top=.89,wspace=.16)
    for ax,c in zip(axs,NAMES):
        table=prod[prod.reporterCode.eq(c)].pivot(index='refYear',columns='cmdCode',values='share_pct')
        bottom=np.zeros(len(table))
        for code,color,hatch in zip(GOODS,['.85','.48','white','.68'],['','///','xx','..']):
            ax.bar(range(8),table[code],bottom=bottom,color=color,hatch=hatch,edgecolor='black',lw=.35,width=.73,label=GOODS[code]);bottom+=table[code]
        ax.set(title=NAMES[c],xticks=range(8),xticklabels=table.index.astype(str),ylim=(0,100));ax.tick_params(axis='x',rotation=45);clean(ax)
    axs[0].set_ylabel('Доля стоимости экспорта, %');handles,labels=axs[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,fontsize=8.5,bbox_to_anchor=(.53,.01))
    save(fig,2,'Изменение товарной структуры экспорта','Каждый столбец составляет 100% стоимости четырех товарных категорий; части HS854290 исключены.')

    directions=[156,344,490,704,702,608,842,764,-1]
    fig,axs=plt.subplots(1,2,figsize=(6.5,3.6),sharey=True);fig.subplots_adjust(left=.24,right=.98,bottom=.18,top=.9,wspace=.16)
    for ax,c in zip(axs,NAMES):
        x=geo[geo.reporterCode.eq(c)].pivot(index='destination',columns='refYear',values='share_pct').loc[directions]
        yy=np.arange(9)
        ax.hlines(yy,x[2017],x[2024],color='.5',lw=1)
        ax.scatter(x[2017],yy,marker='o',s=24,facecolors='white',edgecolors='black',zorder=3,label='2017')
        ax.scatter(x[2024],yy,marker='D',s=22,color='black',zorder=3,label='2024')
        ax.set(title=NAMES[c],xlim=(-1,46),xticks=[0,10,20,30,40],xlabel='Доля экспорта, %');clean(ax,'x')
    axs[0].set_yticks(range(9),[LABELS[d] for d in directions]);axs[0].invert_yaxis()
    h,l=axs[0].get_legend_handles_labels();fig.legend(h,l,ncol=2,loc='lower center',frameon=False,bbox_to_anchor=(.58,-.01))
    save(fig,3,'Перераспределение направлений экспорта между 2017 и 2024 годами','Доли рассчитаны по четырем категориям вместе. Остаток включает все направления вне восьми отдельно выделенных партнеров.')

    stnames=['initial','product_change','geography_change','final']
    fig,axs=plt.subplots(1,2,figsize=(6.5,2.8),sharey=True);fig.subplots_adjust(left=.12,right=.98,bottom=.22,top=.86,wspace=.18)
    for ax,c in zip(axs,NAMES):
        for y,st in enumerate(stnames):
            point=states[(states.reporter==c)&(states.state==st)].iloc[0].sd_pp;ci=ints.loc[(c,st+'_sd_pp')]
            ax.hlines(y,ci.ci_low,ci.ci_high,color='black',lw=1.2);ax.plot(point,y,'o',color='black',ms=4)
        ax.set(title=NAMES[c],xlim=(0,40),xticks=[0,10,20,30,40],xlabel='Стандартное отклонение, п.п.');clean(ax,'x')
    axs[0].set_yticks(range(4),['00','10','01','11']);axs[0].invert_yaxis()
    save(fig,4,'Условная волатильность четырех экспортных структур','Точки — оценки; отрезки — 95%-интервалы, блок 12 месяцев. Обозначения состояний даны в таблице 2.2; шкалы одинаковы. Интервалы уровней не заменяют интервал разности.')

    fig,axs=plt.subplots(1,2,figsize=(6.5,3.1));fig.subplots_adjust(left=.11,right=.98,bottom=.2,top=.87,wspace=.32)
    for ax,c in zip(axs,NAMES):
        q=primary.loc[c];s=states[states.reporter.eq(c)].set_index('state');v0=s.loc['initial','variance_pp2'];v1=s.loc['final','variance_pp2']
        vals=[v0,q.mix_variance_pp2,q.geography_variance_pp2,v1];levels=[v0,v0+vals[1],v1]
        for i,v in enumerate(vals):
            base=0 if i in [0,3] else min(levels[i-1],levels[i])
            ax.bar(i,abs(v),bottom=base,width=.62,color='.65' if i in [0,3] else 'white',hatch=None if i in [0,3] else ('///' if i==1 else '..'),edgecolor='black',lw=.7,zorder=3)
            top=base+abs(v);ax.annotate(('+' if v>0 and i in [1,2] else '')+fmt(v),xy=(i,top),xytext=(0,5),textcoords='offset points',ha='center',fontsize=8)
        for i in range(3):ax.plot([i+.31,i+1-.31],[levels[i]]*2,color='.4',lw=.7)
        ax.set(title=NAMES[c],xticks=range(4),xticklabels=['2017','Товары','География','2024'],ylim=(0,max(levels)*1.25),ylabel='Дисперсия, п.п.²');clean(ax)
    save(fig,5,'Разложение изменения условной дисперсии по Шепли','Шкалы стран различаются. Промежуточная высота каскада складывается из усредненных вкладов Шепли и не является отдельным наблюдаемым состоянием. Интервалы вкладов приведены в таблице 2.4.')

    cov=pd.DataFrame(E['saved_results']['covariance_attribution_intervals']);cov=cov[cov.factor.eq('geography')]
    fig,axs=plt.subplots(1,2,figsize=(6.5,2.75),sharey=True);fig.subplots_adjust(left=.25,right=.98,bottom=.23,top=.86,wspace=.2)
    for ax,c in zip(axs,NAMES):
        q=cov[cov.reporter.eq(c)].set_index('component')
        vals=[(q.loc[k,'estimate_variance_pp2'],q.loc[k,'ci_low'],q.loc[k,'ci_high']) for k in ['own_variances','cross_covariances']]
        ci=ints.loc[(c,'geography_variance_pp2')];vals.append((primary.loc[c,'geography_variance_pp2'],ci.ci_low,ci.ci_high))
        for y,(v,lo,hi) in enumerate(vals):ax.hlines(y,lo,hi,color='black',lw=1.1);ax.plot(v,y,'D' if y==2 else 'o',color='black',ms=4)
        ax.axvline(0,color='.4',lw=.8);ax.set(title=NAMES[c],xlabel='Вклад, п.п.²',xlim=(-28,12) if c==392 else (-90,230));clean(ax,'x')
    axs[0].set_yticks(range(3),['Собственные\nдисперсии','Перекрестные\nковариации','География\nв целом']);axs[0].invert_yaxis()
    save(fig,7,'Составляющие географического вклада','Точки и 95%-интервалы; шкалы стран различаются. Детализация выполнена после основной оценки. Интервалы компонентов не складываются в интервал суммы.')

    memory=pd.DataFrame(E['saved_results']['memory_share_decomposition'])
    fig,axs=plt.subplots(1,2,figsize=(6.5,2.45),sharey=True);fig.subplots_adjust(left=.25,right=.98,bottom=.27,top=.84,wspace=.2)
    for ax,c in zip(axs,NAMES):
        q=memory[memory.reporter.eq(c)].set_index('factor')
        for y,k in enumerate(['memory_share','within_nonmemory_mix']):
            z=q.loc[k];ax.hlines(y,z.ci_low,z.ci_high,color='black',lw=1.2);ax.plot(z.estimate_variance_pp2,y,'o',color='black',ms=4)
        ax.axvline(0,color='.4',lw=.8);ax.set(title=NAMES[c],xlabel='Вклад, п.п.²',xlim=(-10,12) if c==392 else (-260,20));clean(ax,'x')
    axs[0].set_yticks([0,1],['Доля памяти','Состав остальных\nкатегорий']);axs[0].invert_yaxis()
    save(fig,6,'Детализация товарного вклада','Вложенное симметричное разложение исходного товарного вклада; 95%-интервалы, блок 12 месяцев. Шкалы стран различаются. Дополнительные интервалы не скорректированы на множественные сравнения.')

    omit=pd.DataFrame(E['saved_results']['leave_one_year_out'])
    fig,axs=plt.subplots(1,2,figsize=(6.5,3.3),sharey=True);fig.subplots_adjust(left=.12,right=.98,bottom=.2,top=.88,wspace=.18)
    for ax,c in zip(axs,NAMES):
        d=omit[omit.reporter.eq(c)].sort_values('omitted_year')
        ax.axvline(0,color='.6',lw=.8);ax.axvline(primary.loc[c,'delta_sd_pp'],color='black',ls='--',lw=1,label='Полная история')
        ax.scatter(d.delta_sd_pp,np.arange(len(d)),s=23,color='black',zorder=3)
        ax.set(title=NAMES[c],xlim=(-2.2,.7),xlabel='Изменение SD, п.п.');ax.xaxis.set_major_formatter(FuncFormatter(lambda v,pos:fmt(v,1)));clean(ax,'x')
    axs[0].set_yticks(range(7),range(2018,2025));axs[0].set_ylabel('Исключенный год');axs[0].invert_yaxis()
    save(fig,8,'Изменение оценки при последовательном исключении года','Точки — оценки по 72 оставшимся наблюдениям; пунктир — основной расчет по 84 наблюдениям. Для исключений отдельные интервалы не рассчитывались.')
    manifest.sort(key=lambda x:x['number'])
    (HERE/'chapter2_figures.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

def prepare_appendices():
    geo=pd.DataFrame(E['annual_destination_grid'])
    states=pd.DataFrame(E['saved_results']['primary_states'])
    summary=pd.DataFrame(E['saved_results']['all_specifications'])
    directions=[156,344,490,704,702,608,842,764,-1]
    stnames=['initial','product_change','geography_change','final']

    def table(title,headers,rows,note=''):
        lines=['**'+title+'**','','| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
        lines+=['| '+' | '.join(str(x) for x in row)+' |' for row in rows]
        if note:lines+=['','Примечание: '+note]
        lines+=['','Источник: расчеты автора по UN Comtrade.','']
        return '\n'.join(lines)
    ann=pd.read_csv(RISK/'results/monthly/annual_indicators_from_months.csv');ann=ann[~ann.include_parts]
    out=['# Приложения ко второй главе','','## Приложение А Годовые характеристики экспорта','']
    rows=[[NAMES[int(z.reporter)],int(z.year),fmt(z.export_usd/1e9),fmt(100*z.memory_share),fmt(z.product_hhi,4),fmt(z.hhi,4)] for z in ann.itertuples()]
    out.append(table('Таблица А.1 — Стоимость и концентрация экспорта по годам',['Страна','Год','Млрд долл.','Память, %','HHI товаров','HHI географии'],rows,'Географический HHI рассчитан по всем исходным направлениям. Части исключены.'))
    out+=['## Приложение Б Структуры и направления поставок','']
    rows=[]
    for c in NAMES:
        for st,code in zip(stnames,['00','10','01','11']):
            z=states[(states.reporter==c)&(states.state==st)].iloc[0]
            rows.append([NAMES[c],code,fmt(z.variance_pp2),fmt(z.sd_pp),fmt(z.mean_growth_pp),fmt(100*z.residual_share)])
    out.append(table('Таблица Б.1 — Характеристики четырех условных состояний',['Страна','Код','V, п.п.²','SD, п.п.','Средний темп, п.п.','Остаток, %'],rows,'Коды состояний определены в таблице 2.2. Общая история 2018–2024 годов. Средний темп условного индекса не является CAGR.'))
    gp=geo.set_index(['reporterCode','refYear','destination'])
    rows=[[LABELS[d]]+[fmt(gp.loc[(c,y,d),'share_pct']) for c,y in [(392,2017),(392,2024),(410,2017),(410,2024)]] for d in directions]
    out.append(table('Таблица Б.2 — Доли направлений в экспорте четырех категорий',['Направление','Япония 2017','Япония 2024','Корея 2017','Корея 2024'],rows,'Доли в процентах. Остаток включает взаимные поставки Японии и Кореи.'))
    out+=['## Приложение В Полные результаты проверок устойчивости','']
    case_names={'primary':'Основной','top5':'Пять направлений','top12':'Двенадцать кандидатов','include_parts':'С частями','cn_hk_combined':'Китай и Гонконг вместе','monthly_lag1':'Месячный лаг 1','quarterly_yoy':'Квартальный годовой темп','ordinary_pct_yoy':'Обычный процентный темп','sigma_2018_2020':'Ковариации 2018–2020','sigma_2021_2024':'Ковариации 2021–2024','temporal_2018_2020':'2017/2020, раннее окно','temporal_2021_2024':'2017/2020, позднее окно'}
    for idx,c in enumerate(NAMES,1):
        rows=[]
        for z in summary[summary.reporter.eq(c)].itertuples():
            rows.append([case_names[z.case],int(z.n)]+([fmt(v) for v in [z.delta_sd_pp,z.delta_variance_pp2,z.mix_variance_pp2,z.geography_variance_pp2]] if z.status=='ok' else ['н/о']*4))
        out.append(table(f'Таблица В.{idx} — {NAMES[c]}',['Вариант','T','ΔSD, п.п.','ΔV, п.п.²','Товары, п.п.²','География, п.п.²'],rows,'н/о — оценка не определена из-за ненаблюдаемых темпов. T — длина предполагаемого ряда; для недоступных вариантов полный ряд не получен. Последние два варианта используют веса 2017/2020.'))
    out+=['## Приложение Г Детализация географического вклада','']
    da=pd.DataFrame(E['saved_results']['destination_attribution_intervals']);da=da[da.factor.eq('geography')].set_index(['reporter','destination'])
    rows=[]
    for d in directions:
        vals=[]
        for c in NAMES:
            z=da.loc[(c,d)];vals.append(f'{fmt(z.estimate_variance_pp2)} [{fmt(z.ci_low)}; {fmt(z.ci_high)}]')
        rows.append([LABELS[d],*vals])
    out.append(table('Таблица Г.1 — Вклады направлений в изменение дисперсии',['Направление','Япония, п.п.²','Корея, п.п.²'],rows,'В квадратных скобках — 95%-интервалы, блок 12 месяцев. Дополнительная поисковая атрибуция без поправки на множественные сравнения. Вклад включает ковариации ячеек направления с остальными потоками.'))
    out+=['## Приложение Д Изменчивость индексов памяти и остальных схем','',
          'Для каждого года весов построены два ряда на общей истории темпов 2018–2024 годов. Первый суммирует ячейки памяти с фиксированными долями направлений внутри HS854232. Второй объединяет три остальные категории с их географическими долями того же года; товарные веса внутри этой группы нормированы к единице. Это условные индексы, а не фактические темпы совокупного экспорта каждой группы.','']
    group=E['memory_and_remaining_fixed_indices']
    rows=[[NAMES[int(z['reporter'])],z['weight_year'],fmt(z['memory_sd_pp']),fmt(z['remaining_sd_pp']),fmt(z['correlation'])] for z in group]
    out.append(table('Таблица Д.1 — Волатильность и корреляция двух укрупненных индексов',['Страна','Год весов','SD памяти, п.п.','SD остальных, п.п.','Корреляция'],rows,'По 84 наблюдения для каждого ряда. Описательная детализация основной модели; отдельные интервалы для этих статистик не рассчитывались.'))
    out+=['Совокупный индекс точно восстанавливается как сумма индекса памяти, умноженного на ее долю, и индекса остальных схем, умноженного на оставшуюся долю. Его дисперсия равна сумме дисперсий групп с квадратами соответствующих весов и удвоенного произведения весов и ковариации групп. Для четырех сочетаний страны и года это равенство проверено по сохраненным основным оценкам.','',
          'Переход между строками 2017 и 2024 годов меняет географию и относительные пропорции остальных схем одновременно. Поэтому разность их стандартных отклонений не является отдельным вкладом доли памяти. Последний выделен вложенным разложением в разделе 2.3.','']
    out+=['## Приложение Е Воспроизводимость расчетов','',
          'Основная панель, исходные ответы, протокол и программы сохранены в репозитории artyom4iklol/diploma в разделе research/02_chip_trade/risk_extension. Параметры основного расчета зафиксированы в monthly_analysis_protocol.md. Файл analyze_monthly.py формирует условные индексы и интервалы; post_estimation/diagnose_results.py — дополнительные разложения. Результаты главы соответствуют полной панели 2017–2024 годов, полученной 16 октября 2026 года.','',
          'Проверены совпадение дисперсии индекса с квадратичной формой, сложение товарного и географического вкладов, сложение детальных атрибуций и согласованность исходных сумм. Описательные данные рисунков и таблиц подготовлены из сохраненной панели; при редакции главы основная модель не переоценивалась. Полный набор чисел, контрольные суммы и код визуализации находятся в каталоге documents рядом с текстом главы.','']
    (HERE/'chapter2_appendices.md').write_text('\n'.join(out))
    # Compact, fully numerical main robustness table.
    rows=[]
    for case in case_names:
        if case=='primary':continue
        qq=summary[summary.case.eq(case)].set_index('reporter');vals=[]
        for c in NAMES:vals.append(fmt(qq.loc[c,'delta_sd_pp']) if qq.loc[c,'status']=='ok' else 'н/о')
        rows.append([case_names[case],int(qq.loc[392,'n']),*vals])
    t=table('Таблица 2.5 — Чувствительность изменения стандартного отклонения',['Вариант','T','Япония, п.п.','Корея, п.п.'],rows,'T — число месячных либо квартальных темпов. н/о — оценка не определена; в корейских вариантах с лагом 1 и обычным ростом отсутствуют соответственно 6 и 22 значения темпов. Последние два варианта используют структуры 2017/2020. Двенадцать кандидатов дают одиннадцать отдельных направлений и остаток. Полное разложение приведено в приложении В.')
    p=HERE/'chapter2_4.md';text=p.read_text();start=text.index('**Таблица 2.5');end=text.index('Источник: расчеты автора по UN Comtrade.',start)+len('Источник: расчеты автора по UN Comtrade.')
    p.write_text(text[:start]+t.strip()+text[end:])
    print('Prepared six appendices and the main sensitivity table.')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--appendices-only',action='store_true')
    args=parser.parse_args()
    if not args.appendices_only:prepare_figures()
    prepare_appendices()
