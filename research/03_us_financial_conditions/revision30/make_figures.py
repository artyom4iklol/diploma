"""Five analytical figures. Only stored forecast values; no fabricated intervals."""
from pathlib import Path
import numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
P=Path(__file__).resolve().parent;R=P.parent;F=P/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2,'svg.fonttype':'none','savefig.facecolor':'white'})
C={'HIST':'#333f48','AR':'#999999','AR_ESI':'#2a7f62','AR_ESI_NFCI':'#2878b5','AR_ESI_ANFCI':'#d16e25'}
f=pd.read_csv(R/'revision25/results/forecasts.csv');b=f[(f.variant=='expanding')&(f.config=='Q_raw')].copy();b['date']=pd.PeriodIndex(b.origin,freq='Q').to_timestamp()
names=[]
def save(fig,name,note):
 fig.text(.01,.015,note,fontsize=9,color='#444444');fig.savefig(F/(name+'.png'),dpi=190,bbox_inches='tight');fig.savefig(F/(name+'.svg'),bbox_inches='tight');plt.close(fig);names.append(name)
def ticks(ax,dates,step=8):
 d=sorted(set(dates));idx=list(range(0,len(d),step));ax.set_xticks([d[i] for i in idx],[str(pd.Timestamp(d[i]).year) for i in idx])
fig,axs=plt.subplots(2,2,figsize=(12,7.5));fig.subplots_adjust(bottom=.16,top=.89,hspace=.4,wspace=.24);fig.suptitle('Накопленный выигрыш американских индексов',fontsize=15,y=.98)
for i,h in enumerate([1,4]):
 w=b[b.h==h].pivot(index='origin',columns='model',values='loss').sort_index();d=pd.PeriodIndex(w.index,freq='Q').to_timestamp()
 for j,bm in enumerate(['AR_ESI','HIST']):
  ax=axs[i,j]
  for m in ['AR_ESI_NFCI','AR_ESI_ANFCI']:ax.plot(d,(w[bm]-w[m]).cumsum(),color=C[m],lw=2,label=m.split('_')[-1])
  ax.axhline(0,color='black',lw=.7);ax.axvline(pd.Timestamp('2020-10-01'),ls=':',color='#777777');ax.set_title(f'h = {h}; ориентир '+bm.replace('_',' + '));ax.set_ylabel('Сумма разностей потерь');ticks(ax,d)
  if i==0 and j==0:ax.legend(frameon=False,ncol=2)
save(fig,'figure_2_1_cumulative_loss','Положительное значение: потери ориентира выше. Вертикаль: исходный квартал 2020Q4.\nИсточник: расчёты автора; расширяющееся окно, квартальный охват США. Это не денежный выигрыш.')
fig,axs=plt.subplots(2,2,figsize=(13,8));fig.subplots_adjust(bottom=.18,top=.86,hspace=.4,wspace=.24);fig.suptitle('Фактический рост и прогнозы десятого процентиля',fontsize=15,y=.98)
for i,h in enumerate([1,4]):
 for j,start in enumerate([None,'2022Q1']):
  v=b[b.h==h];v=v if start is None else v[v.origin>=start];ax=axs[i,j];a=v[v.model=='HIST'];ax.plot(a.date,a.actual,color='black',lw=1.8,label='Факт')
  for m in ['HIST','AR_ESI','AR_ESI_NFCI','AR_ESI_ANFCI']:
   a=v[v.model==m];ax.plot(a.date,a.forecast,color=C[m],lw=1.4,ls='--' if m=='HIST' else '-',label=m.replace('_',' + '))
  ax.set_title(f'h = {h}; '+('весь период' if start is None else 'исходные кварталы с 2022Q1'));ax.set_ylabel('Годовой логарифмический рост, %');ax.axhline(0,color='#777777',lw=.6)
  if start is None:ticks(ax,v.date)
  else:
   dates=sorted(set(v.date));ix=list(range(0,len(dates),4));ix+=([len(dates)-1] if len(dates)-1-ix[-1]>=2 else []);ax.set_xticks([dates[k] for k in ix],[str(pd.Timestamp(dates[k]).to_period('Q')) for k in ix],rotation=25)
hd,lb=axs[0,0].get_legend_handles_labels();fig.legend(hd,lb,loc='upper center',bbox_to_anchor=(.5,.94),ncol=5,frameon=False,fontsize=9)
save(fig,'figure_2_2_forecasts','По оси X — исходный квартал t; факт относится к будущему интервалу t+1 … t+h. Слева сохранены все экстремумы.\nСправа другой период и масштаб оси Y. Линии — отдельные квантили, а не доверительные интервалы. Источник: расчёты автора.')
fig,axs=plt.subplots(1,2,figsize=(12,5.8));fig.subplots_adjust(bottom=.23,top=.82,wspace=.16);fig.suptitle('Качество после диагностики экстремальной даты',fontsize=15,y=.98)
cases=[('Исходная оценка','Q_raw',[],'o',-.16),('Без 2020Q4','Q_raw',['2020Q4'],'s',0),('Ограничение роста','Q_clip_g',[],'D',.16)]
for ax,h in zip(axs,[1,4]):
 for title,cfg,omit,mk,off in cases:
  z=f[(f.variant=='expanding')&(f.config==cfg)&(f.h==h)&~f.origin.isin(omit)].groupby('model').loss.mean()
  for i,m in enumerate(['AR_ESI','AR_ESI_NFCI','AR_ESI_ANFCI']):ax.scatter(z[m]/z.HIST,i+off,color=C[m],marker=mk,s=65)
 ax.axvline(1,color='#444444',ls='--');ax.set_yticks(range(3),['AR + ESI','AR + ESI + NFCI','AR + ESI + ANFCI'] if h==1 else ['']*3);ax.set_xlabel('Средняя потеря / потеря HIST на тех же датах');ax.set_title(f'h = {h}');ax.set_ylim(2.5,-.5)
hd=[plt.Line2D([],[],color='#555555',marker=mk,linestyle='',label=title) for title,_,_,mk,_ in cases];fig.legend(handles=hd,loc='upper center',bbox_to_anchor=(.5,.92),ncol=3,frameon=False)
save(fig,'figure_2_3_extreme_sensitivity','Левее 1 — меньше потерь, чем у HIST. Исключение даты меняет только оценку сохранённых прогнозов.\nОграничение роста — ретроспективная диагностика. Статистические интервалы на рисунке не оцениваются.')
s=pd.read_csv(R/'revision25/results/scores.csv');mods=['HIST','AR','AR_ESI','AR_ESI_NFCI','AR_ESI_ANFCI'];rows=[(v,c) for v in ['expanding','rolling52'] for c in ['Q_raw','M2_raw','Q_clip_g','M2_clip_g']];mats=[]
for h in [1,4]:
 mat=[]
 for v,c in rows:
  z=s[(s.h==h)&(s.variant==v)&(s.config==c)].set_index('model').mean_loss;mat.append([z[m]/z.HIST for m in mods])
 mats.append(np.array(mat))
vs=np.concatenate([x.flatten() for x in mats]);norm=TwoSlopeNorm(vmin=min(.9,float(vs.min())-.03),vcenter=1.,vmax=float(vs.max())+.03)
fig,axs=plt.subplots(1,2,figsize=(13,7));fig.subplots_adjust(bottom=.21,top=.89,left=.2,right=.89,wspace=.22);fig.suptitle('Относительные потери во всех исходных конфигурациях',fontsize=15,y=.98)
ls=[('Расш.' if v=='expanding' else '52 кв.')+' / '+c.replace('_raw','').replace('_clip_g',' + огр.') for v,c in rows]
for ax,h,mat in zip(axs,[1,4],mats):
 im=ax.imshow(mat,cmap='RdYlBu_r',norm=norm,aspect='auto');ax.set_xticks(range(5),['HIST','AR','AR + ESI','+ NFCI','+ ANFCI'],rotation=25,ha='right');ax.set_yticks(range(8),ls if h==1 else ['']*8);ax.set_title(f'h = {h}');ax.grid(False)
 for i in range(8):
  for j in range(5):ax.text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',color='white' if mat[i,j]>norm.vmax*.84 else '#222222')
cax=fig.add_axes([.92,.24,.018,.6]);fig.colorbar(im,cax=cax,label='Потеря / HIST')
save(fig,'figure_2_4_robustness','Каждая ячейка нормирована на HIST в той же конфигурации и на том же горизонте; меньше 1 — лучше HIST.\nQ — квартальный охват США; M2 — первые два месяца; «огр.» — ограничение текущего роста. Источник: расчёты автора.')
s=pd.read_csv(P/'results/equity_scores.csv');cases=[('Исходная','all','raw'),('Без 2020Q4','omit_2020Q4','raw'),('Ограничение роста','all','clip_g')]
fig,axs=plt.subplots(1,2,figsize=(12,6));fig.subplots_adjust(bottom=.23,top=.83,wspace=.18);fig.suptitle('Американские индексы после учёта европейского рынка акций',fontsize=14,y=.98)
for ax,h in zip(axs,[1,4]):
 for i,(lab,sample,guard) in enumerate(cases):
  z=s[(s.h==h)&(s['sample']==sample)&(s.guard==guard)].set_index('model')
  for off,m,mk,color in [(-.13,'AR_ESI_EQ_NFCI','o','#2878b5'),(.13,'AR_ESI_EQ_ANFCI','D','#d16e25')]:ax.scatter(float(z.loc[m,'ratio_AR_ESI_EQ']),i+off,s=80,marker=mk,color=color,label=m.replace('AR_ESI_EQ_','') if i==0 else None)
 ax.axvline(1,color='#444444',ls='--');ax.set_yticks(range(3),[c[0] for c in cases] if h==1 else ['']*3);ax.set_ylim(2.5,-.5);ax.set_title(f'h = {h}');ax.set_xlabel('Потеря / потеря AR + ESI + EQ')
hd,lb=axs[0].get_legend_handles_labels();fig.legend(hd,lb,loc='upper center',bbox_to_anchor=(.5,.93),ncol=2,frameon=False)
save(fig,'figure_2_5_equity_extension','Левее 1 — улучшение базы с EQ. Сравнения описательные; расширение сформировано после основного эксперимента.\nEQ — изменение усреднённого EURO STOXX 50. Улучшение этой базы не означает превосходства над HIST.')
(F/'README.md').write_text('# Рисунки диплома\n\nPNG: 190 dpi; SVG: вектор. Источники — сохранённые прогнозы.\n\n'+''.join('- '+n+'.png / '+n+'.svg\n' for n in names)+'\nВоспроизведение: python revision30/make_figures.py\n');print('Created',len(names),'figures')
