"""Monochrome figures for Chapter 3: an author framework and computed scenarios."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent
OUT=HERE/'chapter3_assets';OUT.mkdir(exist_ok=True)
E=json.loads((HERE/'chapter3_evidence.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.titlesize':10,
 'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':9,'axes.spines.top':False,
 'axes.spines.right':False,'axes.linewidth':.65,'svg.fonttype':'none','savefig.facecolor':'white'})
manifest=[]

def save(fig,num,kind):
 for ext in ['png','svg']:
  fig.savefig(OUT/f'fig3_{num}.{ext}',dpi=250)
  if ext=='svg':
   target=OUT/f'fig3_{num}.{ext}'
   target.write_text('\n'.join(line.rstrip() for line in target.read_text().splitlines())+'\n')
 manifest.append(dict(number=f'3.{num}',path=f'chapter3_assets/fig3_{num}.png',kind=kind,
  sha256=hashlib.sha256((OUT/f'fig3_{num}.png').read_bytes()).hexdigest()))
 plt.close(fig)

def rect(ax,x,y,w,h,text,fill='white',fs=9):
 p=FancyBboxPatch((x,y),w,h,boxstyle='square,pad=0',facecolor=fill,edgecolor='.2',linewidth=.8)
 ax.add_patch(p);ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs,linespacing=1.4)

def arrow(ax,a,b,label=None):
 ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=.8,color='.2'))
 if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.025,label,ha='center',va='bottom',fontsize=8)

fig,ax=plt.subplots(figsize=(6.5,4.0));fig.subplots_adjust(left=.01,right=.99,top=.98,bottom=.02)
ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
labels=['Продукт и покупатель:\nсоответствие требованиям',
        'Источник спроса:\nсвязь с текущими продажами',
        'Экономика поставки:\nзатраты и альтернативы',
        'Пилотная поставка:\nоплата, повторный заказ']
ys=[.79,.55,.31,.07]
for y,l in zip(ys,labels):rect(ax,.04,y,.55,.16,l,fill='.96')
for i in range(3):arrow(ax,(.315,ys[i]),(.315,ys[i+1]+.16))
rect(ax,.71,.79,.27,.16,'Невыполнимо:\nотказ от входа',fs=8.7)
rect(ax,.71,.55,.27,.16,'Мало сведений:\nограничить пилот',fs=8.7)
rect(ax,.71,.31,.27,.16,'Невыгодно:\nдоработать / отказ',fs=8.7)
for y in ys[:3]:arrow(ax,(.59,y+.08),(.71,y+.08))
ax.text(.66,.06,'Расширение после\nпроверки результата',fontsize=9,va='bottom',ha='left')
arrow(ax,(.59,.15),(.68,.15))
save(fig,1,'author-proposed decision framework; no quantitative estimates')

fig,axes=plt.subplots(1,2,figsize=(6.5,3.25),sharex=True,sharey=True)
fig.subplots_adjust(left=.12,right=.98,top=.86,bottom=.20,wspace=.18)
fmt=FuncFormatter(lambda x,pos:f'{x:g}'.replace('-', '−').replace('.',','))
for ax,c,name in zip(axes,[392,410],['Япония','Республика Корея']):
 rows=[r for r in E['scenarios'] if r['reporter']==c]
 intervals={r['shift_pp']:r for r in E['paired_intervals'] if r['reporter']==c and r['block_months']==12}
 x=np.array([r['shift_pp'] for r in rows]);y=np.array([r['delta_sd_pp'] for r in rows])
 ax.plot(x,y,color='black',lw=.85,marker='o',ms=3.5)
 for r in rows:
  ci=intervals[r['shift_pp']];ax.vlines(r['shift_pp'],ci['ci_low'],ci['ci_high'],color='black',lw=1.05)
  ax.hlines([ci['ci_low'],ci['ci_high']],r['shift_pp']-.23,r['shift_pp']+.23,color='black',lw=.8)
 ax.axhline(0,color='.4',lw=.7,ls='--');ax.grid(axis='y',color='.88',lw=.5);ax.set_axisbelow(True)
 ax.set(title=name,xlim=(-5.8,5.8),ylim=(-2,2),xticks=[-5,-2.5,0,2.5,5],yticks=[-2,-1,0,1,2],xlabel='Сдвиг доли памяти, п.п.')
 ax.xaxis.set_major_formatter(fmt);ax.yaxis.set_major_formatter(fmt)
axes[0].set_ylabel('Изменение SD, п.п.')
save(fig,2,'computed paired historical scenarios; 95% pointwise intervals')

fig,ax=plt.subplots(figsize=(6.5,3.55));fig.subplots_adjust(left=.01,right=.99,top=.99,bottom=.01)
ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
ax.text(.02,.96,'Этап и ведущий участник',fontsize=9.5,weight='bold',va='top')
ax.text(.55,.96,'Условие следующего шага',fontsize=9.5,weight='bold',va='top')
left=['Отбор проекта\nФирма и инвестор','Разработка и образец\nИнженерная команда','Коммерческий пилот\nФирма и заказчик','Расширение поставок\nРуководство фирмы']
right=['Спрос, компетенции,\nпредварительная смета','Соответствие заданию,\nквалификация, себестоимость','Оплаченная поставка,\nповторный спрос, маржа','Проверка структуры,\nпокупателей и затрат']
ys=[.70,.48,.26,.04]
for y,l,r in zip(ys,left,right):
 rect(ax,.02,y,.43,.16,l,fill='.95');rect(ax,.55,y,.43,.16,r);arrow(ax,(.45,y+.08),(.55,y+.08))
for i in range(3):arrow(ax,(.235,ys[i]),(.235,ys[i+1]+.16))
save(fig,3,'author-proposed implementation stages and review gates')
(HERE/'chapter3_figures.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Created 3 monochrome figures (PNG and SVG)')
