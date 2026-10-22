"""Print-legible replacements for figures 2.7, 3.4, Б.1 and Д.1.

Values are read from the verified graph CSV tables; no model is re-estimated.
Usage: --data <CSV dir> --fonts <HSE Sans OTF dir> --out <output dir>
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager,colors,patches
from matplotlib.ticker import FuncFormatter

BLUE='#0B2F73';RED='#E31B2D';INK='#26364C'
COUNTRIES=['Япония','Республика Корея']
GOODS=['Процессоры и контроллеры','Память','Усилители','Прочие интегральные схемы']
GOODS_LABEL=['Процессоры и\nконтроллеры','Память','Усилители','Прочие ИС']
MARKETS=['Китай','Гонконг','Прочая Азия, н.в.д. (490)','Вьетнам','Сингапур','Филиппины','США','Таиланд','Остальные направления']
LABELS=['Китай','Гонконг','Прочая Азия,\nн.в.д. (490)','Вьетнам','Сингапур','Филиппины','США','Таиланд','Остальные\nнаправления']
FMT=FuncFormatter(lambda x,pos:f'{x:g}'.replace('.',','))

def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--fonts',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 for f in a.fonts.glob('*.otf'):font_manager.fontManager.addfont(str(f))
 plt.rcParams.update({'font.family':'HSE Sans','font.size':9,'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'axes.titlesize':11,'axes.titleweight':'bold','axes.spines.top':False,'axes.spines.bottom':False,'axes.spines.left':False,'axes.spines.right':False,'svg.fonttype':'path','figure.facecolor':'white','savefig.facecolor':'white'})
 seq=colors.LinearSegmentedColormap.from_list('hse_blue',['#F5F7FB',BLUE])
 div=colors.LinearSegmentedColormap.from_list('hse_diverging',[BLUE,'#FFFFFF',RED])
 audit=[]
 def load(n):return pd.read_csv(next(a.data.glob(f'{n:02d}_*.csv')))
 def save(fig,name,values):
  path=a.out/(name+'.png');fig.savefig(path,dpi=400);fig.savefig(a.out/(name+'.svg'));plt.close(fig)
  audit.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'numeric_cells':int(np.size(values)),'values_sha256':hashlib.sha256(np.asarray(values,dtype='<f8').tobytes()).hexdigest()})
 def matrix(df,country,rows,cols):
  q=df.loc[df['Панель'].eq(country)];m=q.pivot(index='Строка',columns='Столбец',values='Значение').loc[rows,cols].to_numpy()
  assert len(q)==m.size and np.isfinite(m).all()
  # Pivot retains every source value in the requested order.
  assert all(m[i,j]==q.loc[q['Строка'].eq(row)&q['Столбец'].eq(col),'Значение'].iloc[0] for i,row in enumerate(rows) for j,col in enumerate(cols))
  return m
 def grid(ax,m,rows,cols,cmap,norm):
  im=ax.imshow(m,cmap=cmap,norm=norm,aspect='auto',interpolation='nearest')
  ax.set_yticks(np.arange(len(rows)),rows,fontsize=9);ax.set_xticks(np.arange(len(cols)),cols,fontsize=9)
  ax.tick_params(axis='both',which='both',length=0);ax.set_xticks(np.arange(len(cols)+1)-.5,minor=True);ax.set_yticks(np.arange(len(rows)+1)-.5,minor=True);ax.grid(which='minor',color='white',lw=1)
  return im
 def value_text(ax,m,norm,digits=1,large=False):
  for i,j in np.ndindex(m.shape):
   v=m[i,j];v=0 if abs(v)<.5*10**(-digits) else v
   white=norm(v)>.60
   ax.text(j,i,f'{v:.{digits}f}'.replace('.',','),ha='center',va='center',fontsize=10 if large else 9.5,color='white' if white else INK,weight='bold' if large and v>=100 else 'normal')

 # 2.7: rows become destinations, leaving only four short product columns.
 d=load(10);fig,axes=plt.subplots(2,1,figsize=(6.48,7.75));fig.subplots_adjust(left=.255,right=.985,top=.89,bottom=.13,hspace=.55);vals=[]
 for ax,c,color in zip(axes,COUNTRIES,[BLUE,RED]):
  m=matrix(d,c,GOODS,MARKETS).T;vals.extend(m.ravel());im=grid(ax,m,LABELS,GOODS_LABEL,seq,colors.Normalize(0,60));ax.xaxis.tick_top();ax.set_title(c,loc='left',pad=45,color=color);value_text(ax,m,im.norm)
 cb=fig.colorbar(im,cax=fig.add_axes([.30,.055,.63,.018]),orientation='horizontal',ticks=[0,15,30,45,60]);cb.outline.set_visible(False);cb.ax.xaxis.set_major_formatter(FMT);cb.set_label('Доля направления в экспорте товарной группы, %',fontsize=9)
 save(fig,'10_product_destination',vals)

 # 3.4: larger values and explicit outlines for at least doubling a cell.
 d=load(21);fig,axes=plt.subplots(2,1,figsize=(6.48,7.1));fig.subplots_adjust(left=.255,right=.985,top=.89,bottom=.17,hspace=.58);vals=[]
 norm=colors.FuncNorm((np.log1p,np.expm1),vmin=0,vmax=2000)
 for ax,c,color in zip(axes,COUNTRIES,[BLUE,RED]):
  m=matrix(d,c,MARKETS[:8],[GOODS[0],GOODS[2],GOODS[3]]);vals.extend(m.ravel());im=grid(ax,m,LABELS[:8],[GOODS_LABEL[0],GOODS_LABEL[2],GOODS_LABEL[3]],seq,norm);ax.xaxis.tick_top();ax.set_title(c,loc='left',pad=45,color=color);value_text(ax,m,norm,large=True)
  for i,j in np.ndindex(m.shape):
   if m[i,j]>=100:ax.add_patch(patches.Rectangle((j-.47,i-.47),.94,.94,fill=False,edgecolor='white' if norm(m[i,j])>.6 else BLUE,lw=1.4))
 cb=fig.colorbar(im,cax=fig.add_axes([.30,.085,.63,.018]),orientation='horizontal',ticks=[0,10,50,100,500,2000]);cb.outline.set_visible(False);cb.ax.xaxis.set_major_formatter(FMT);cb.set_label('Прирост стоимости ячейки, %; шкала log(1 + рост)',fontsize=8.5)
 fig.text(.255,.015,'Рамка: прирост не менее 100%',fontsize=9)
 save(fig,'21_cell_expansion',vals)

 # Б.1: one country per image; axis numbers map to fully named rows.
 d=load(24)
 for k,(c,color) in enumerate(zip(COUNTRIES,[BLUE,RED]),1):
  m=matrix(d,c,MARKETS,MARKETS);fig,ax=plt.subplots(figsize=(6.48,5.7));fig.subplots_adjust(left=.305,right=.985,top=.91,bottom=.22)
  im=grid(ax,m,[f'{i+1}  {s}' for i,s in enumerate(LABELS)],[str(i+1) for i in range(9)],div,colors.Normalize(-1,1));ax.set_title(c,loc='left',pad=14,color=color);ax.set_xlabel('Номера направлений соответствуют строкам',labelpad=9,fontsize=8.5)
  for i,j in np.ndindex(m.shape):
   v=m[i,j];v=0 if abs(v)<.005 else v
   ax.text(j,i,f'{v:.2f}'.replace('.',','),ha='center',va='center',fontsize=8.5,color='white' if abs(v)>.62 else INK,weight='bold' if i==j else 'normal')
  cb=fig.colorbar(im,cax=fig.add_axes([.33,.085,.60,.023]),orientation='horizontal',ticks=[-1,-.5,0,.5,1]);cb.outline.set_visible(False);cb.ax.xaxis.set_major_formatter(FMT);cb.set_label('Коэффициент корреляции Пирсона',fontsize=9)
  save(fig,f'24_destination_correlations_part{k}',m)

 # Д.1: taller product rows, readable labels and year boundaries.
 d=load(23);fig,axes=plt.subplots(2,1,figsize=(6.48,6.65));fig.subplots_adjust(left=.235,right=.985,top=.94,bottom=.15,hspace=.47);vals=[]
 for ax,c,color in zip(axes,COUNTRIES,[BLUE,RED]):
  q=d.loc[d['Страна'].eq(c)];dates=sorted(q['Месяц'].unique());m=q.pivot(index='Товар',columns='Месяц',values='Рост, п.п.').loc[GOODS,dates].to_numpy();assert m.shape==(4,84) and np.isfinite(m).all();vals.extend(m.ravel())
  im=ax.imshow(m,cmap=div,vmin=-200,vmax=200,aspect='auto',interpolation='nearest');ax.set_yticks(range(4),GOODS_LABEL,fontsize=9.5);ax.set_xticks(np.arange(7)*12+5.5,[str(y) for y in range(2018,2025)],fontsize=9);ax.set_title(c,loc='left',pad=14,color=color);ax.tick_params(axis='both',length=0)
  for x in np.arange(-.5,84,1):ax.axvline(x,color='white',lw=.18)
  for x in np.arange(-.5,84,12):ax.axvline(x,color='#7A8CA6',lw=.65)
  for y in np.arange(-.5,4,1):ax.axhline(y,color='white',lw=1.2)
 cb=fig.colorbar(im,cax=fig.add_axes([.30,.065,.63,.022]),orientation='horizontal',ticks=[-200,-100,0,100,200]);cb.outline.set_visible(False);cb.ax.xaxis.set_major_formatter(FMT);cb.set_label('Симметричный годовой рост, п.п.',fontsize=9)
 save(fig,'23_monthly_product_growth',vals)
 (a.out/'four_figures_validation.json').write_text(json.dumps({'source_numeric_cells':954,'numeric_values_changed':False,'matrices':audit,'body_font_pt_min':8.5,'global_titles':False,'correlation_split_by_country':True,'cell_outline_threshold_percent':100},ensure_ascii=False,indent=2)+'\n')
 print('Prepared five panels for four figures; 954 source values retained.')

if __name__=='__main__':main()
