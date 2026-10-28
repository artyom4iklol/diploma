"""Thirty-two thesis figures from frozen evidence in the approved thesis style.

No collection, model refits or changes to the estimation sample are performed.
The original chapter plotters supply the already audited 16 figures. Their
artists are restyled before export; sixteen additional figures use the same
saved panel/results or explicitly labelled theoretical examples.
"""
from pathlib import Path
import hashlib
import json
import re
import io
import os
import tempfile
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_hex
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import plot_chapter2 as ch2
import plot_chapter3 as ch3

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / 'thesis_figures'
NAVY, RED, TEAL, PURPLE = '#0b2f73', '#e31b2d', '#338c86', '#8976ac'
INK, MUTED, GRID, BORDER, PALE = '#203653', '#52627c', '#dbe4ef', '#c3cfe0', '#f1f5fa'
COLORS = [NAVY, RED, TEAL]
CATS = ['BEV', 'PHEV', 'HEV']
NAMES = dict(AT='Австрия', BE='Бельгия', BG='Болгария', CY='Кипр', CZ='Чехия', DE='Германия', DK='Дания', EE='Эстония', ES='Испания', FI='Финляндия', FR='Франция', GR='Греция', HR='Хорватия', HU='Венгрия', IE='Ирландия', IT='Италия', LT='Литва', LU='Люксембург', LV='Латвия', MT='Мальта', NL='Нидерланды', PL='Польша', PT='Португалия', RO='Румыния', SE='Швеция', SI='Словения', SK='Словакия')
MANIFEST = []


def setup():
    plt.rcParams.update({'font.family':'Nimbus Sans', 'font.size':10,
        'text.color':INK, 'axes.labelcolor':MUTED, 'xtick.color':MUTED,
        'ytick.color':MUTED, 'axes.edgecolor':BORDER, 'axes.spines.top':False,
        'axes.spines.right':False, 'axes.linewidth':.65, 'axes.axisbelow':True,
        'grid.color':GRID, 'grid.linewidth':.55, 'legend.frameon':False,
        'legend.fontsize':9, 'svg.fonttype':'none',
        'svg.hashsalt':'auto-thesis-approved-style-v1', 'savefig.facecolor':'white'})


def fmt(value, n=1):
    return f'{value:.{n}f}'.replace('.', ',')


def read(name):
    return pd.read_csv(ROOT / name)


def panel(ax, label):
    ax.text(0, 1.045, label, transform=ax.transAxes, color=INK, weight='bold', size=10)


def series_color(label, fallback=0):
    labels={'BEV':NAVY, 'PHEV':RED, 'HEV':TEAL, 'Вся корзина':INK,
        'По количеству':NAVY, 'По стоимости':RED, 'Количество':NAVY,
        'Удельная стоимость':RED, 'Товарные веса':RED, 'География':NAVY,
        'Доли внутри категорий':NAVY, 'Продолжающие':NAVY,
        'Новые положительные':RED, 'Итог':INK, 'HAC(12)':NAVY,
        'Блочный интервал':RED, '10% потока BE/NL':NAVY, '25% потока BE/NL':RED,
        'Равенство роста сокращению':BORDER}
    return labels.get(label, COLORS[fallback % 3])


def restyle(fig, name):
    """Change presentation of the audited legacy artists, without their data."""
    for ai, ax in enumerate(fig.axes):
        ax.set_facecolor('white')
        for s in ax.spines.values(): s.set_color(BORDER); s.set_linewidth(.65)
        for line in ax.get_xgridlines()+ax.get_ygridlines(): line.set_color(GRID); line.set_linewidth(.55)
        for text in ax.texts:
            text.set_color(INK)
            if text.get_transform()==ax.transAxes: text.set_weight('bold')
        for li, line in enumerate(ax.lines):
            label=line.get_label()
            if name in ['G11_intervals','G12_sensitivity']:
                color=RED if line.get_linestyle()=='--' or line.get_marker()=='s' and name=='G11_intervals' else NAVY
                if to_hex(line.get_color()) in ['#808080','#999999']: color=BORDER
            elif name in ['G02_monthly']: color=COLORS[ai % 3] if len(line.get_xdata())>2 else BORDER
            elif name=='C3_G03_history': color=BORDER if len(line.get_xdata())==2 else COLORS[ai % 3]
            elif not label.startswith('_'): color=series_color(label,li)
            else: color=BORDER if to_hex(line.get_color()) in ['#808080','#999999'] else NAVY
            line.set_color(color)
            if line.get_markerfacecolor()!='white': line.set_markerfacecolor(color)
            line.set_markeredgecolor(color)
        for ci, container in enumerate(ax.containers):
            if hasattr(container, 'patches'):
                color=series_color(container.get_label(),ci)
                for p in container.patches: p.set_facecolor(color);p.set_edgecolor('white');p.set_linewidth(.4);p.set_hatch('')
        for collection in ([] if name=='G07_geography' else ax.collections):
            if hasattr(collection,'set_color'):
                collection.set_color(COLORS[ai%3] if name=='C3_G03_history' else INK)
        for im in ax.images:
            im.set_cmap(LinearSegmentedColormap.from_list('thesis_blues',['#f5f7fb',NAVY]))
        for patch in ax.patches:
            if isinstance(patch,FancyBboxPatch): patch.set_facecolor(PALE);patch.set_edgecolor(BORDER)
            if isinstance(patch,FancyArrowPatch): patch.set_color(NAVY)
        if name=='G04_mix':
            for text in ax.texts:
                x,y=text.get_position()
                for container in ax.containers:
                    for p in getattr(container,'patches',[]):
                        if p.get_x()<=x<=p.get_x()+p.get_width() and p.get_y()<=y<=p.get_y()+p.get_height():
                            text.set_color('white')
                            if text.get_bbox_patch(): text.get_bbox_patch().set_facecolor(p.get_facecolor())
        if name=='G07_geography':
            for text in ax.texts:
                try: value=float(text.get_text().replace(',','.'))
                except ValueError: value=0
                text.set_color('white' if value>55 else INK)
    legends=list(fig.legends)+[a.get_legend()for a in fig.axes if a.get_legend()]
    for leg in legends:
        for i,(handle,text)in enumerate(zip(leg.legend_handles,leg.texts)):
            color=series_color(text.get_text(),i);text.set_color(INK)
            if isinstance(handle,Patch): handle.set_facecolor(color);handle.set_edgecolor('white');handle.set_hatch('')
            elif isinstance(handle,Line2D): handle.set_color(color);handle.set_markeredgecolor(color);handle.set_markerfacecolor(color)


def atomic_write(path, payload):
    """Publish complete exports only, including on a remotely backed filesystem."""
    if isinstance(payload, str): payload = payload.encode('utf8')
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def save(fig, name, sources, data, kind='observed_or_saved_results', restyle_legacy=False):
    if restyle_legacy: restyle(fig,name)
    OUT.mkdir(exist_ok=True)
    fig.canvas.draw()
    for suffix in ['svg','png']:
        buffer = io.BytesIO()
        fig.savefig(buffer,format=suffix,dpi=240,bbox_inches='tight',pad_inches=.13,
            metadata={'Date':None}if suffix=='svg' else None)
        atomic_write(OUT/f'{name}.{suffix}', buffer.getvalue())
    if isinstance(data,pd.DataFrame): data=data.replace({np.nan:None}).to_dict('records')
    atomic_write(OUT/f'{name}.json',json.dumps(data,ensure_ascii=False,indent=2,default=lambda x:x.item()if isinstance(x,np.generic)else str(x))+'\n')
    if isinstance(data,list)and all(isinstance(x,dict)for x in data): atomic_write(OUT/f'{name}.csv',pd.json_normalize(data).to_csv(index=False))
    MANIFEST.append({'id':name,'kind':kind,'source_files':sources,
        'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in sources},
        'svg_sha256':hashlib.sha256((OUT/f'{name}.svg').read_bytes()).hexdigest(),
        'png_sha256':hashlib.sha256((OUT/f'{name}.png').read_bytes()).hexdigest()})
    plt.close(fig)


def legacy():
    def save2(fig,name,sources,data):
        if name=='G12_sensitivity': plt.close(fig);return
        save(fig,name,sources,data,restyle_legacy=True)
    ch2.OUT=OUT;ch2.save=save2;ch2.main()
    ch3.OUT=OUT;ch3.save=lambda fig,name,sources,data:save(fig,'C3_'+name,sources,data,
        kind='author_proposed_scheme'if name in ['G01_monitoring','G04_implementation']else 'saved_scenario_or_history',restyle_legacy=True)
    ch3.main()
    sensitivity()


def sensitivity():
    """Retain all original specifications and append the separate NL diagnostic."""
    co=read('results/augmented/coefficients.csv')
    nl=read('results/thesis_audit/exclude_NL_comparison.csv')
    assert len(nl)==4 and (nl.n==8140).all()
    variants=['rest_preferred','rest_no_trend','rest_no_season','four_origin_augmented','rest_since2022','rest_exclude_BE_NL','rest_observed_only']
    labels=['Основная','Без тренда','Без сезонности','Четыре происхождения','С 2022 года','Без BE/NL','Опубликованные пары','Без NL (доп.)']
    for cat,suffix,letter in [('PHEV','quantity','a'),('PHEV','value','b'),('HEV','quantity','c'),('HEV','value','d')]:
        d=co[(co.term==cat+'__definitive')&co.model.isin([v+'_'+suffix for v in variants])].set_index('model').loc[[v+'_'+suffix for v in variants]]
        outcome='quantity' if suffix=='quantity' else 'value_eur'
        extra=nl[(nl.category==cat)&(nl.outcome==outcome)]
        assert len(extra)==1
        row=extra.iloc[0]
        assert np.isclose(row.full_multiplier,d.iloc[0].multiplier,rtol=1e-12)
        d=d.reset_index().assign(post_analysis_diagnostic=False)
        diagnostic={'model':'rest_exclude_NL_'+suffix,'outcome':outcome,'n':int(row.n),
            'term':cat+'__definitive','beta':float(np.log(row.exclude_NL_multiplier)),
            'multiplier':float(row.exclude_NL_multiplier),'post_analysis_diagnostic':True,
            **{x:float(row[x]) for x in ['hac6_lo','hac6_hi','hac12_lo','hac12_hi']}}
        d=pd.concat([d,pd.DataFrame([diagnostic])],ignore_index=True)
        assert len(d)==8 and (d.hac12_lo>0).all() and (d.hac12_hi>=d.hac12_lo).all()
        fig,ax=plt.subplots(figsize=(6.7,3.45),layout='constrained')
        for i,row in enumerate(d.itertuples()):
            color=NAVY if i==0 else (TEAL if row.post_analysis_diagnostic else RED)
            ax.plot([row.hac12_lo,row.hac12_hi],[i,i],color=color,lw=1.2)
            ax.plot(row.multiplier,i,marker='s'if i==0 else ('D'if row.post_analysis_diagnostic else'o'),color=color,ms=5 if i==0 else 4)
        ax.set_yticks(range(8),labels);ax.invert_yaxis();ax.set_xscale('log');ax.axvline(1,color=BORDER,lw=.8);ax.grid(axis='x');ax.set_xlabel('Множитель; интервал HAC(12)')
        save(fig,'G12_'+letter,['results/augmented/coefficients.csv','results/thesis_audit/exclude_NL_comparison.csv'],d,
            kind='original_sensitivities_and_separate_post_analysis_diagnostic')


def audit_additions():
    """Visualize already saved audit outputs without refitting any model."""
    t=read('results/thesis_audit/baseline_presence_thresholds.csv')
    assert len(t)==16 and not t.duplicated(['base','category','baseline_threshold']).any()
    assert np.allclose(t.change_below_threshold+t.change_above_threshold,t.total_change,atol=1e-9)
    assert np.allclose(t.fraction_of_change_below_threshold,t.change_below_threshold/t.total_change,atol=1e-12)
    assert (t.end==2025).all() and (t.total_change>0).all()
    fig,axes=plt.subplots(1,2,figsize=(6.7,3.65),sharey=True,layout='constrained')
    thresholds=[1,10,100,1000]
    for ax,base,letter in zip(axes,[2023,2024],['а','б']):
        for cat,color,marker,ls in [('PHEV',RED,'o','-'),('HEV',TEAL,'s','--')]:
            d=t[(t.base==base)&(t.category==cat)].set_index('baseline_threshold').loc[thresholds]
            y=100*d.fraction_of_change_below_threshold.to_numpy()
            ax.plot(range(4),y,color=color,marker=marker,ls=ls,lw=1.5,ms=4,label=cat)
            for i,value in enumerate(y):
                offset=-13 if cat=='HEV' and (base==2024 or i==0) else 8
                ax.annotate(fmt(value,2),(i,value),xytext=(0,offset),textcoords='offset points',
                    ha='center',va='top'if offset<0 else'bottom',fontsize=8.5,color=color)
        ax.axhline(100,color=BORDER,ls=':',lw=.9)
        ax.set_xticks(range(4),['1','10','100','1000']);ax.set_xlim(-.22,3.22)
        ax.set_ylim(-21,115);ax.set_yticks([0,25,50,75,100]);ax.grid(axis='y')
        ax.spines['left'].set_bounds(0,100)
        ax.set_xlabel('Порог исходного количества, шт.',fontsize=9)
        panel(ax,f'{letter}) {base}–2025 годы')
    axes[0].set_ylabel('Доля чистого прироста, %',fontsize=9)
    fig.legend(*axes[0].get_legend_handles_labels(),ncol=2,loc='outside lower center')
    save(fig,'N09_baseline_presence',['results/thesis_audit/baseline_presence_thresholds.csv'],t,
        kind='saved_initial_presence_threshold_diagnostic')

    h=read('results/thesis_audit/hhi_leave_one_country.csv')
    full=read('results/thesis_audit/hhi_exclusions.csv')
    assert len(h)==108 and (h.change<0).all()
    assert not h.duplicated(['base','outcome','excluded']).any()
    assert np.allclose(h.product_component+h.geography_component,h.change,atol=1e-12)
    codes=sorted(NAMES,key=lambda c:NAMES[c]);assert set(h.excluded)==set(codes)
    fig,axes=plt.subplots(2,2,figsize=(6.7,7.3),sharex=True,layout='constrained')
    context=[]
    for ax,(base,outcome,letter) in zip(axes.flat,[(2023,'quantity','а'),(2023,'value_eur','б'),(2024,'quantity','в'),(2024,'value_eur','г')]):
        d=h[(h.base==base)&(h.outcome==outcome)].set_index('excluded').loc[codes]
        assert len(d)==27 and (d.countries==26).all()
        f=full[(full.base==base)&(full.outcome==outcome)&full.excluded.isna()]
        assert len(f)==1
        baseline=float(f.iloc[0].change);context.append({'base':base,'outcome':outcome,'full_panel_change':baseline})
        color=NAVY if outcome=='quantity'else RED
        ax.scatter(d.change,range(27),s=17,color=color,zorder=3)
        nearest=d.change.idxmax()
        if d.loc[nearest,'change']>-.005:
            ax.annotate(fmt(d.loc[nearest,'change'],4),
                (d.loc[nearest,'change'],codes.index(nearest)),xytext=(-8,7),
                textcoords='offset points',ha='right',fontsize=8,color=color,
                bbox={'facecolor':'white','edgecolor':'none','pad':.5})
        ax.axvline(baseline,color=TEAL,ls='--',lw=.9,zorder=2)
        ax.axvline(0,color=INK,lw=1,zorder=2)
        ax.set_yticks(range(27),codes,fontsize=8.6);ax.invert_yaxis();ax.set_ylim(26.7,-.7)
        ax.set_xlim(-.151,.005);ax.set_xticks([-.15,-.10,-.05,0]);ax.tick_params(axis='x',labelbottom=True,labelsize=8.5)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:fmt(x,2)));ax.grid(axis='x')
        for tick,code in zip(ax.get_yticklabels(),codes):
            if code in ['BE','NL']:tick.set_weight('bold')
        label='количество'if outcome=='quantity'else'стоимость'
        panel(ax,f'{letter}) {base}–2025, {label}')
        ax.set_xlabel('Изменение HHI',fontsize=9)
    handles=[Line2D([],[],color=NAVY,marker='o',ls='',label='Количество'),
        Line2D([],[],color=RED,marker='o',ls='',label='Стоимость'),
        Line2D([],[],color=TEAL,ls='--',label='Полная география ЕС-27')]
    fig.legend(handles=handles,ncol=3,loc='outside lower center',fontsize=8.5)
    merged=h.merge(pd.DataFrame(context),on=['base','outcome'],validate='many_to_one')
    save(fig,'N10_hhi_leave_one_country',['results/thesis_audit/hhi_leave_one_country.csv','results/thesis_audit/hhi_exclusions.csv'],merged,
        kind='saved_country_influence_diagnostic_not_confidence_intervals')


def box(ax,x,y,w,h,text,bold=False,color=PALE):
    patch=FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0,rounding_size=.007',facecolor=color,edgecolor=BORDER,lw=.8)
    ax.add_patch(patch);ax.text(x,y,text,ha='center',va='center',size=10,weight='bold'if bold else 'normal',color=NAVY if bold else INK,linespacing=1.35)
    return {'top':(x,y+h/2),'bottom':(x,y-h/2),'left':(x-w/2,y),'right':(x+w/2,y)}


def arrow(ax,start,end):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=10,lw=.9,color=NAVY,shrinkA=0,shrinkB=0))


def theory():
    fig,ax=plt.subplots(figsize=(6.7,3.65));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    xs=[.19,.50,.81]
    features=[('BEV','Электрическая тяга','Внешняя зарядка','Без ДВС'),('PHEV','Электротяга и ДВС','Внешняя зарядка','Два источника\nэнергии'),('HEV','Электротяга и ДВС','Без внешней\nзарядки','Топливо и\nрекуперация')]
    for x,col,color in zip(xs,features,COLORS):
        ax.text(x,.94,col[0],ha='center',color=color,weight='bold',size=12)
        for i,text in enumerate(col[1:]): box(ax,x,.74-.23*i,.28,.17,text)
    save(fig,'T01_technologies',['manuscript/chapter1_content.md'],[{'category':x[0],'features':list(x[1:])}for x in features],kind='conceptual_classification')
    fig,ax=plt.subplots(figsize=(6.7,4.3));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    top=box(ax,.5,.92,.70,.11,'Изменение условий торговли',True)
    middle=box(ax,.5,.68,.78,.14,'Затраты, относительные цены\nи ожидаемый доход поставщика')
    arrow(ax,top['bottom'],middle['top'])
    children=[]
    for x,text in [(.17,'Объём и\nассортимент'),(.5,'Источники\nпроизводства'),(.83,'Организация\nпоставок')]:
        b=box(ax,x,.39,.29,.16,text);children.append(b)
        # Orthogonal forks use a common horizontal connector and vertical arrows.
        ax.plot([.5,x],[.55,.55],color=NAVY,lw=.9);arrow(ax,(x,.55),b['top'])
    ax.plot([.5,.5],[middle['bottom'][1],.55],color=NAVY,lw=.9)
    bottom=box(ax,.5,.10,.86,.13,'Количество, стоимость, состав и география',True)
    for x,b in zip([.17,.5,.83],children):
        ax.plot([x,x],[b['bottom'][1],.23],color=NAVY,lw=.9);ax.plot([x,.5],[.23,.23],color=NAVY,lw=.9)
    arrow(ax,(.5,.23),bottom['top'])
    save(fig,'T02_adaptation',['manuscript/chapter1_content.md'],{'type':'possible_economic_mechanisms','causal_identification':False},kind='conceptual_scheme')
    d=pd.DataFrame([{'basket':'80 / 20','country_A':80,'country_B':20,'HHI':.68},{'basket':'50 / 50','country_A':50,'country_B':50,'HHI':.50}])
    fig,axes=plt.subplots(1,2,figsize=(6.7,3.0),layout='constrained')
    for ax,row in zip(axes,d.itertuples()):
        ax.bar([0],[row.country_A],color=NAVY,width=.55,label='Страна А');ax.bar([0],[row.country_B],bottom=[row.country_A],color=RED,width=.55,label='Страна Б')
        ax.text(0,row.country_A/2,str(row.country_A)+'%',ha='center',va='center',color='white')
        ax.text(0,row.country_A+row.country_B/2,str(row.country_B)+'%',ha='center',va='center',color='white')
        ax.set_xticks([0],[row.basket]);ax.set_ylim(0,100);ax.set_xlim(-.65,.65);ax.set_yticks([0,50,100]);ax.grid(axis='y');panel(ax,'HHI = '+fmt(row.HHI,2))
    axes[0].set_ylabel('Доля в общей корзине, %');fig.legend(*axes[0].get_legend_handles_labels(),ncol=2,loc='outside lower center')
    save(fig,'T03_hhi_example',['manuscript/chapter1_content.md'],d,kind='explicitly_hypothetical_example')


def additions():
    annual=read('results/full/annual_eu_flows.csv');member=read('results/full/annual_member_flows.csv');paneldata=read('results/full/panel.csv')
    cn=annual[annual.origin=='CN'];ext=annual[annual.origin=='EXT_EU27_2020']
    # Annual scale in the two original units, without a dual axis.
    fig,axes=plt.subplots(1,2,figsize=(6.7,3.45),layout='constrained');export=[]
    for ax,col,unit,label in zip(axes,['quantity','value_eur'],[1000,1e9],['а) Тыс. машин','б) Млрд евро']):
        pivot=cn.pivot(index='year',columns='category',values=col)[CATS]/unit;bottom=np.zeros(5)
        for cat,color in zip(CATS,COLORS):ax.bar(pivot.index,pivot[cat],bottom=bottom,color=color,width=.65,label=cat);bottom+=pivot[cat].to_numpy()
        ax.set_xticks(range(2021,2026),[str(x)[2:]for x in range(2021,2026)]);ax.set_ylim(bottom=0);ax.grid(axis='y');panel(ax,label)
        export.extend([{'year':int(y),'category':cat,'outcome':col,'value':float(pivot.loc[y,cat]*unit)}for y in pivot.index for cat in CATS])
    fig.legend(*axes[0].get_legend_handles_labels(),ncol=3,loc='outside lower center')
    save(fig,'N01_annual_scale',['results/full/annual_eu_flows.csv'],export)
    monthly=paneldata[(paneldata.origin=='CN')&(paneldata.reporter!='EU27_2020')].groupby(['month','category']).value_eur.sum().unstack()[CATS]
    fig,axes=plt.subplots(3,1,figsize=(6.7,5.4),sharex=True,layout='constrained')
    for ax,cat,color in zip(axes,CATS,COLORS):
        ax.plot(pd.to_datetime(monthly.index),monthly[cat]/1e9,color=color,lw=1.35)
        for date in ['2023-09-01','2024-07-01','2024-11-01']:ax.axvline(pd.Timestamp(date),color=BORDER,ls='--',lw=.7)
        ax.text(.015,.8,cat,transform=ax.transAxes,weight='bold');ax.set_ylabel('Млрд евро');ax.set_ylim(bottom=0);ax.grid(axis='y')
    axes[-1].set_xticks(pd.date_range('2021-01-01','2025-01-01',freq='YS'),[str(y)for y in range(2021,2026)])
    save(fig,'N02_monthly_value',['results/full/panel.csv'],monthly.reset_index())
    fig,axes=plt.subplots(1,2,figsize=(6.7,3.4),sharey=True,layout='constrained');rows=[]
    for ax,col,label in zip(axes,['quantity','value_eur'],['а) Количество','б) Стоимость']):
        for cat,color,ls in zip(CATS,COLORS,['-','--',':']):
            a=cn[cn.category==cat].set_index('year')[col];b=ext[ext.category==cat].set_index('year')[col];s=a/b*100
            ax.plot(s.index,s,color=color,lw=1.6,ls=ls,marker='o',ms=3,label=cat);rows.extend([{'category':cat,'year':int(y),'outcome':col,'share_pct':float(s[y])}for y in s.index])
        ax.set_xticks(range(2021,2026),[str(y)[2:]for y in range(2021,2026)]);ax.set_ylim(0,80);ax.grid(axis='y');panel(ax,label)
    axes[0].set_ylabel('Доля Китая внутри технологии, %');fig.legend(*axes[0].get_legend_handles_labels(),ncol=3,loc='outside lower center')
    save(fig,'N03_category_shares',['results/full/annual_eu_flows.csv'],rows)
    # Customs unit values are ratios of the exact observed annual sums.
    fig,axes=plt.subplots(1,2,figsize=(6.7,3.5),layout='constrained');rows=[]
    for cat,color in zip(CATS,COLORS):
        d=cn[cn.category==cat].set_index('year');s=d.value_eur/d.quantity/1000
        axes[0].plot(s.index,s,color=color,lw=1.45,marker='o',ms=3,label=cat)
        rows.extend([{'coverage':'EU27','category':cat,'year':int(y),'unit_value_eur':float(s[y]*1000)}for y in s.index])
    for excluded,label,color,ls in [([], 'ЕС-27',NAVY,'-'),(['NL'],'Без NL',RED,'--'),(['BE','NL'],'Без BE/NL',TEAL,':')]:
        d=member[(member.origin=='CN')&(member.category=='BEV')&~member.reporter.isin(excluded)].groupby('year')[['value_eur','quantity']].sum();s=d.value_eur/d.quantity/1000
        axes[1].plot(s.index,s,color=color,lw=1.45,ls=ls,marker='o',ms=3,label=label)
        rows.extend([{'coverage':label,'category':'BEV','year':int(y),'unit_value_eur':float(s[y]*1000)}for y in s.index])
    for ax,lab in zip(axes,['а) Три технологии','б) BEV при разных охватах']):
        ax.set_xticks(range(2021,2026),[str(y)[2:]for y in range(2021,2026)]);ax.set_ylim(bottom=0);ax.grid(axis='y');panel(ax,lab);ax.legend(loc='lower center',bbox_to_anchor=(.5,1.07),ncol=3,fontsize=8)
    axes[0].set_ylabel('Тыс. евро на автомобиль')
    save(fig,'N04_customs_unit_values',['results/full/annual_eu_flows.csv','results/full/annual_member_flows.csv'],rows)
    fig,axes=plt.subplots(1,3,figsize=(6.7,3.5),sharey=True,layout='constrained');rows=[]
    concentration=read('results/full/entry_concentration.csv')
    for ax,cat in zip(axes,CATS):
        active=member[(member.origin=='CN')&(member.category==cat)].assign(positive=lambda x:x.quantity>0).groupby('year').positive.sum()
        eff=concentration[(concentration.category==cat)&(concentration.outcome=='quantity')].set_index('year').effective_entry_countries
        ax.plot(active.index,active,color=NAVY,marker='o',ms=3,label='Положительный поток')
        ax.plot(eff.index,eff,color=RED,marker='s',ms=3,ls='--',label='Эффективное число')
        ax.set_xticks(range(2021,2026),[str(y)[2:]for y in range(2021,2026)]);ax.set_ylim(0,28);ax.grid(axis='y');panel(ax,cat)
        rows.extend([{'category':cat,'year':int(y),'positive_countries':int(active[y]),'effective_countries':float(eff[y])}for y in active.index])
    axes[0].set_ylabel('Число стран');fig.legend(*axes[0].get_legend_handles_labels(),ncol=2,loc='outside lower center')
    save(fig,'N05_active_effective',['results/full/entry_concentration.csv','results/full/annual_member_flows.csv'],rows)
    fig,axes=plt.subplots(3,1,figsize=(6.7,6.3),layout='constrained');rows=[]
    for ax,cat,color in zip(axes,CATS,COLORS):
        d=member[(member.origin=='CN')&(member.category==cat)&(member.year==2025)].set_index('reporter').quantity.sort_values(ascending=False)
        assert len(d)==27
        values=list(d.iloc[:6]/d.sum()*100)+[float(d.iloc[6:].sum()/d.sum()*100)];labels=[NAMES[x]for x in d.index[:6]]+['Остальные 21 страна']
        ax.barh(range(7),values,color=[color]*6+[BORDER],height=.65);ax.invert_yaxis();ax.set_yticks(range(7),labels);ax.set_xlim(0,max(values)*1.20);ax.grid(axis='x');panel(ax,cat)
        for i,v in enumerate(values):ax.text(v+.35,i,fmt(v)+'%',va='center',size=9,color=INK)
        rows.extend([{'category':cat,'country_group':name,'share_pct':v}for name,v in zip(labels,values)])
        assert np.isclose(sum(values),100)
    axes[-1].set_xlabel('Доля в количестве китайских поставок, %')
    save(fig,'N06_largest_entries',['results/full/annual_member_flows.csv'],rows)
    groups=read('results/geography_focus/category_HHI_group_shapley.csv');d=groups[(groups.outcome=='quantity')&(groups.start==2023)].set_index('category').loc[CATS]
    fig,axes=plt.subplots(3,1,figsize=(6.7,5.4),layout='constrained')
    keys=['between_groups_share_component','within_BE_NL_concentration_component','within_other25_concentration_component'];labels=['Доля BE/NL','Внутри BE/NL','Остальные 25 стран']
    for ax,cat in zip(axes,CATS):
        values=[float(d.loc[cat,k])for k in keys];span=max(abs(np.array(values)).max(),.01)
        ax.barh(range(3),values,color=COLORS,height=.60);ax.set_yticks(range(3),labels);ax.invert_yaxis();ax.axvline(0,color=BORDER,lw=.8);ax.grid(axis='x');panel(ax,cat+'   ΔHHI = '+fmt(d.loc[cat,'HHI_change'],4))
        ax.set_xlim(min(values)-.30*span,max(values)+.35*span);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:fmt(x,2)))
        for i,v in enumerate(values):ax.text(v+(1 if v>=0 else -1)*span*.035,i,fmt(v,4),va='center',ha='left'if v>=0 else 'right',size=9)
        assert np.isclose(sum(values),d.loc[cat,'HHI_change'],atol=1e-12)
    axes[-1].set_xlabel('Вклад в изменение HHI')
    save(fig,'N07_group_hhi',['results/geography_focus/category_HHI_group_shapley.csv'],d.reset_index())
    coeff=read('results/augmented/coefficients.csv');fig,axes=plt.subplots(1,2,figsize=(6.7,3.7),layout='constrained');rows=[]
    phases=['investigation','announcement','provisional','definitive'];labels=['Сигнал и\nрасследование','Объявление','Временная','Окончательная']
    for ax,cat in zip(axes,['PHEV','HEV']):
        for suffix,offset,color,marker,label in [('quantity',-.10,NAVY,'o','Количество'),('value',.10,RED,'s','Стоимость')]:
            z=coeff[(coeff.model=='rest_preferred_'+suffix)&coeff.term.isin([cat+'__'+x for x in phases])].set_index('term').loc[[cat+'__'+x for x in phases]]
            for i,row in enumerate(z.itertuples()):
                ax.plot([row.hac12_lo,row.hac12_hi],[i+offset]*2,color=color,lw=1.1);ax.plot(row.multiplier,i+offset,marker=marker,color=color,ms=4)
            rows.extend(z.reset_index().to_dict('records'))
        ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xscale('log');ax.axvline(1,color=BORDER,lw=.8);ax.grid(axis='x');ax.set_xlabel('Множитель; HAC(12)');panel(ax,cat)
    handles=[Line2D([],[],color=NAVY,marker='o',label='Количество'),Line2D([],[],color=RED,marker='s',label='Стоимость')];fig.legend(handles=handles,ncol=2,loc='outside lower center')
    save(fig,'N08_all_phases',['results/augmented/coefficients.csv'],rows)
    scenarios=read('results/chapter3_application/scenario_transfer.csv');fig,axes=plt.subplots(1,2,figsize=(6.7,3.25),sharey=True,layout='constrained')
    for ax,alpha in zip(axes,[.1,.25]):
        for cat,color in zip(CATS,COLORS):
            z=scenarios[(scenarios.alpha==alpha)&(scenarios.category==cat)].sort_values('rho');ax.plot(z.rho*100,z.remaining_share_pct,color=color,marker='o',ms=4,lw=1.5,label=cat)
        ax.set_xticks([0,50,100]);ax.set_ylim(0,14);ax.grid(axis='y');ax.set_xlabel('Заданный перенос ρ, %');panel(ax,'α = '+str(int(alpha*100))+'% потока пары')
    axes[0].set_ylabel('Неперенесённая часть, % категории');fig.legend(*axes[0].get_legend_handles_labels(),ncol=3,loc='outside lower center')
    save(fig,'R01_transfer',['results/chapter3_application/scenario_transfer.csv'],scenarios,kind='fixed_scenarios_not_estimated_probabilities')
    x=np.linspace(0,1,101);fig,ax=plt.subplots(figsize=(6.3,3.7),layout='constrained')
    ax.fill_between(x,0,1-x,color='#eaf0f8');ax.fill_between(x,1-x,1,color='#fcf0f1');ax.plot(x,1-x,color=NAVY,lw=1.7)
    ax.text(.12,.16,'Условие расходов\nвыполняется',color=NAVY,size=11);ax.text(.52,.74,'Порог превышен',color=RED,size=11)
    ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Фиксированная нагрузка F / (n d)');ax.set_ylabel('Дополнительные расходы c / d');ax.set_xticks([0,.25,.5,.75,1]);ax.set_yticks([0,.25,.5,.75,1]);ax.grid();ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:fmt(x,2)));ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:fmt(x,2)))
    save(fig,'R02_cost_boundary',['manuscript/chapter3_content.md'],pd.DataFrame({'fixed_cost_ratio':x,'maximum_variable_cost_ratio':1-x}),kind='normalized_theoretical_cost_criterion')
    acea=read('data/chapter3_public/acea_eu_bev_registrations.csv');vals=acea.iloc[:,1]if 'registrations'not in acea.columns else acea.registrations
    # Read explicit column names and assert the already documented observations.
    reg=[1447631,1880370];assert set(reg)<=set(acea.select_dtypes(include='number').to_numpy().ravel())
    q=cn[cn.category=='BEV'].set_index('year').quantity;changes=[(q[2025]/q[2024]-1)*100,(reg[1]/reg[0]-1)*100]
    fig,ax=plt.subplots(figsize=(6.7,2.65),layout='constrained');labels=['Импорт BEV из Китая\nв ЕС-27','Регистрации BEV всех\nпроисхождений в ЕС-27']
    ax.barh(range(2),changes,color=[NAVY,RED],height=.45);ax.set_yticks(range(2),labels);ax.invert_yaxis();ax.axvline(0,color=BORDER,lw=.8);ax.grid(axis='x');ax.set_xlim(-7,36);ax.set_xlabel('Изменение количества в 2025 году, % к 2024 году')
    for i,v in enumerate(changes):ax.text(v+(.7 if v>=0 else -.7),i,('+'if v>0 else '')+fmt(v)+'%',va='center',ha='left'if v>0 else 'right',color=INK)
    save(fig,'R03_import_registrations',['results/full/annual_eu_flows.csv','data/chapter3_public/acea_eu_bev_registrations.csv'],[{'series':label,'value_2024':int(a),'value_2025':int(b),'change_pct':float(c)}for label,a,b,c in zip(labels,[int(q[2024]),reg[0]],[int(q[2025]),reg[1]],changes)])


def main(audit_only=False):
    OUT.mkdir(exist_ok=True);setup();MANIFEST.clear()
    if audit_only:
        previous=json.loads((OUT/'figure_manifest.json').read_text())['figures']
        sensitivity();audit_additions()
        changes={x['id']:x for x in MANIFEST}
        MANIFEST[:]=[changes.pop(x['id'],x)for x in previous]+list(changes.values())
    else:
        legacy();theory();additions();audit_additions()
    assert len(MANIFEST)==35 # 32 logical figures; appendix A.3 has four panels.
    assert len({x['id']for x in MANIFEST})==35
    metadata={'date':'2026-10-28','logical_figures':32,'image_panels':35,'additional_logical_figures':16,
        'reference_style':{'palette':{'navy':NAVY,'red':RED,'teal':TEAL,'purple':PURPLE},'font':'Nimbus Sans (Arial-compatible)','background':'white','internal_titles':False,'caption':'external Word paragraph'},
        'no_data_collection':True,'no_model_refits':True,'figures':MANIFEST}
    atomic_write(OUT/'figure_manifest.json',json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'logical_figures':32,'image_panels':35,'no_model_refits':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only',action='store_true',help='Update only six audit-related image assets; retain other verified exports.')
    main(parser.parse_args().audit_only)
