"""Research diagnostics from saved results, not illustrations of causality."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/full';FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
colors={'BEV':'#555555','PHEV':'#1673a5','HEV':'#c56b18'}
def save(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');plt.close(fig)

a=pd.read_csv(OUT/'annual_eu_flows.csv');cn=a[a.origin=='CN'];ext=a[a.origin=='EXT_EU27_2020']
fig,ax=plt.subplots(1,2,figsize=(11.8,4.6),layout='constrained')
bottom=np.zeros(5);years=np.arange(2021,2026)
for cat in ['BEV','PHEV','HEV']:
    y=cn[cn.category==cat].set_index('year').reindex(years).quantity.to_numpy()/1000
    ax[0].bar(years,y,bottom=bottom,label=cat,color=colors[cat],width=.65);bottom+=y
ax[0].set(ylabel='Тысяч новых автомобилей',xticks=years);ax[0].legend(ncol=3,frameon=False,loc='upper left')
for outcome,label,style in [('quantity','Доля по количеству','-o'),('value_eur','Доля по стоимости','--s')]:
    share=cn.groupby('year')[outcome].sum()/ext.groupby('year')[outcome].sum()*100
    ax[1].plot(years,share.reindex(years),style,label=label,color='#1673a5' if outcome=='quantity' else '#555555')
    ax[1].annotate(f'{share.loc[2025]:.2f}%',(2025,share.loc[2025]),xytext=(-10,8),textcoords='offset points',ha='right')
ax[1].set(ylabel='Доля Китая во внешнем импорте ЕС, %',xticks=years);ax[1].legend(frameon=False,loc='upper left');ax[1].grid(axis='y',alpha=.2)
fig.supxlabel('Только новые BEV и бензиновые PHEV/HEV; страна происхождения — Китай. Источник: Eurostat Comext.',fontsize=9)
save(fig,'01_quantities_and_value_shares')

dyn=json.loads((OUT/'dynamic_quantity.json').read_text());cs={x['term']:x for x in dyn['coefficients']}
quarters=pd.period_range('2021Q1','2025Q4',freq='Q');labels=[str(x) for x in quarters]
fig,axes=plt.subplots(2,1,figsize=(11.8,7),sharex=True,layout='constrained')
for ax,cat in zip(axes,['PHEV','HEV']):
    beta=[];lo=[];hi=[]
    for q in labels:
        if q=='2023Q2':b=l=h=0
        else:
            c=cs[cat+'__'+q];b=c['beta'];l,h=c['hac12']['beta_ci95']
        beta.append(b);lo.append(l);hi.append(h)
    x=np.arange(20);ax.fill_between(x,lo,hi,alpha=.16,color=colors[cat]);ax.plot(x,beta,'o-',color=colors[cat],ms=4,label=cat+' / BEV, Китай относительно JP/KR/US')
    ax.axhline(0,color='#444444',lw=.8);ax.axvline(10.7,color='#777777',ls=':',label='Начало расследования, сентябрь 2023')
    ax.axvline(13.35,color='#777777',ls='--',label='Объявление ставок, июнь 2024');ax.axvline(15.0,color='#111111',ls='-.',label='Первый полный месяц окончательных мер, ноябрь 2024')
    ax.set_ylabel('Логарифм условного\nотносительного множителя');ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,fontsize=8,loc='upper left')
axes[-1].set_xticks(np.arange(20),labels,rotation=45,ha='right')
fig.supxlabel('База — 2023Q2. Полосы: 95% HAC(12), месячные общие шоки. Малое временное покрытие квартала; диагностические интервалы.',fontsize=9)
save(fig,'02_dynamic_composition')

coef=pd.read_csv(OUT/'model_coefficients.csv')
models=[('primary_quantity','Основная'),('since2022_quantity','С 2022 года'),('exclude_BE_NL_quantity','Без BE и NL'),('observed_only_quantity','Только опубликованные потоки'),('omit_JP','Без Японии'),('omit_KR','Без Кореи'),('omit_US','Без США'),('origin_product_trends','Тренды происхождение × категория'),('investigation_phase','Отдельная фаза расследования')]
fig,axes=plt.subplots(1,2,figsize=(12,5.3),sharey=True,layout='constrained')
for ax,cat in zip(axes,['PHEV','HEV']):
    for i,(name,label) in enumerate(models):
        r=coef[(coef.model==name)&(coef.term==cat+'__definitive')].iloc[0];yy=len(models)-1-i
        ax.errorbar(r.multiplier,yy,xerr=np.array([[r.multiplier-r.hac12_lo],[r.hac12_hi-r.multiplier]]),fmt='o',color=colors[cat],capsize=3)
    ax.axvline(1,color='#777777',ls='--');ax.set_xscale('log');ax.set_xlabel(cat+': условный относительный множитель (лог. шкала)');ax.grid(axis='x',alpha=.2)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v,pos:f'{v:g}'))
axes[0].set_yticks(np.arange(len(models)),[x[1] for x in reversed(models)])
fig.supxlabel('Ноябрь 2024 — декабрь 2025 относительно базы до июня 2024; BEV — базовая категория. 95% HAC(12). Не причинный эффект пошлины.',fontsize=9)
save(fig,'03_specification_sensitivity')
print('Saved',len(list(FIG.glob('*'))),'diagnostic figures')
