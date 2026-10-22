"""Assemble the thesis. No model estimation or changes to source chapters."""
from pathlib import Path
import re, json, hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
paths={'chapter1':'chapter1/Chapter_1_US_Financial_Conditions_Euro_Area.md','chapter2':'chapter2/Chapter_2_Empirical_Analysis.md','chapter3':'chapter3/Chapter_3_Recommendations.md','appendix':'chapter2/Appendix_Chapter_2_Additional_Experiments.md'}
src={k:(ROOT/p).read_text() for k,p in paths.items()}
c1,bib=src['chapter1'].split('## Список использованных источников к главе 1',1)
c2,n2=src['chapter2'].split('## Источники и примечания к главе 2',1)
c3,n3=src['chapter3'].split('## Источники и примечания к главе 3',1)
def notes(t): return dict(re.findall(r'^\[\^([^\]]+)\]:\s*(.*)$',t,re.M))
notes2,notes3=notes(n2),notes(n3)
assert len(notes2)==26 and len(notes3)==16
m2={'1':'[46]','3':'[47]','4':'[48]','5':'[49; 50]','6':'[51]','7':'[52; 53]','8':'[54]','9':'[7]','10':'[55]','11':'[56–59][^calc2-11]','12':'[21]','14':'[40]','15':'[42]','17':'[43]','18':'[30]','22':'[9; 12]','26':'[26]'}
m3={'3-1':'[9]','3-2':'[12]','3-4':'[7; 51]','3-5':'[30]','3-7':'[47; 52; 53]','3-11':'[40]','3-12':'[42]','3-14':'[43]','3-15':'[26]'}
kept=[]
for k,v in notes2.items():
 if k not in m2 or k=='11':
  tag='calc2-'+k
  if k=='11': v='Восстановление выполнено по статистическим таблицам 2.1 «GDP and expenditure components» и 2.6 «Opinion surveys» выпусков ЕЦБ [56–59]. Полные выпуски и извлечённые значения сохранены; журнал — `revision18/results/bulletin_repairs.csv`. См. приложение А.3.'
  v=v.replace('chapter2/Appendix_Chapter_2_Additional_Experiments.md','приложение Б настоящей работы')
  kept.append(f'[^{tag}]: {v}')
  m2.setdefault(k,f'[^{tag}]')
for k,v in notes3.items():
 if k not in m3:
  tag='calc'+k
  v=v.replace('`chapter2/Appendix_Chapter_2_Additional_Experiments.md`','приложение Б настоящей работы').replace('в приложении ко второй главе','в приложении Б')
  if k=='3-10': v=v.replace('параграф 2.2','параграф 2.1')
  kept.append(f'[^{tag}]: {v}');m3[k]=f'[^{tag}]'
def citations(t,m):
 t=re.sub(r'\[\^([^\]]+)\]',lambda x:m[x[1]],t)
 for _ in range(3):t=re.sub(r'\[([\d; –]+)\]\[([\d; –]+)\]',lambda x:'['+x[1]+'; '+x[2]+']',t)
 return t
c2,c3=citations(c2,m2),citations(c3,m3)
changes=[
('Объектом исследования выступает совокупная экономическая динамика еврозоны.','Объектом исследования является совокупная экономическая динамика еврозоны в условиях международных финансовых взаимосвязей.'),
('с поправкой Holm;','с поправкой Holm [45];'),
('Статистическая часть теперь охватывает','Статистическая часть охватывает'),
('Международно-экономическая интерпретация теперь опирается','Международно-экономическая интерпретация опирается')]
for old,new in changes:
 assert c2.count(old)==1,old
 c2=c2.replace(old,new,1)
c2=c2.replace('приведены в приложении к главе','приведены в приложении Б').replace('вынесена в приложение.','вынесена в приложение Б.').replace('приведены в приложении.','приведены в приложении Б.').replace('представлены в приложении;','представлены в приложении Б;')
c3=c3.replace('Тексты комментариев составлены сейчас как реконструкция;','Тексты комментариев составлены в рамках исследования как реконструкция;')
bibliography='# Список использованных источников\n\n'+bib.strip()+'\n\n'+(HERE/'Additional_References.md').read_text().strip()+'\n'
(HERE/'Bibliography.md').write_text(bibliography)
app=src['appendix'].strip()
app=re.sub(r'^# Приложение к главе 2\..*$', '## Приложение Б. Полные результаты дополнительных проверок',app,flags=re.M)
app=re.sub(r'^## А\.(\d+)\.',r'### Б.\1.',app,flags=re.M)
app=re.sub(r'^### (?!Б\.)(.*)$',r'#### \1',app,flags=re.M)
app=app.replace('В новой главе результат','В основном тексте результат')
titles=['Конфигурации дополнительных проверок','Полные оценки качества: расширяющееся окно, один квартал','Полные оценки качества: расширяющееся окно, четыре квартала','Полные оценки качества: скользящее окно, один квартал','Полные оценки качества: скользящее окно, четыре квартала','Даты срабатывания ограничения лагового роста','Парные сравнения и влияние дат: расширяющееся окно, один квартал','Парные сравнения и влияние дат: расширяющееся окно, четыре квартала','Парные сравнения и влияние дат: скользящее окно, один квартал','Парные сравнения и влияние дат: скользящее окно, четыре квартала','Статистические сравнения: один квартал, HAC с четырьмя лагами','Статистические сравнения: один квартал, HAC с восемью лагами','Статистические сравнения: четыре квартала, HAC с четырьмя лагами','Статистические сравнения: четыре квартала, HAC с восемью лагами']
lines=[];in_table=False;count=0
for l in app.splitlines():
 if l.startswith('|') and not in_table:
  count+=1;lines.extend([f'Таблица Б.{count}. {titles[count-1]}',''])
 in_table=l.startswith('|');lines.append(l)
assert count==14
appendices='# Приложения\n\n'+(HERE/'Appendices_Additional.md').read_text().replace('<!-- APPENDIX_B_INSERT -->','\n'.join(lines)).replace('<!-- CALCULATION_NOTES_INSERT -->','\n\n'.join(kept))
(HERE/'Appendices.md').write_text(appendices)
parts=[('introduction',(HERE/'Introduction.md').read_text()),('chapter-1',c1),('chapter-2',c2),('chapter-3',c3),('conclusion',(HERE/'Conclusion.md').read_text()),('references',bibliography),('appendices',appendices)]
toc=['# Финансовые условия США в прогнозировании рисков роста еврозоны','','## Оглавление','']
for a,t in parts:
 title=t.splitlines()[0].lstrip('# ');toc.append(f'- [{title}](#{a})')
 if a.startswith('chapter-'):
  toc.extend('  - '+h for h in re.findall(r'^## (\d\.\d\..*)$',t,re.M))
 if a=='appendices':toc.extend('  - '+h for h in re.findall(r'^## (Приложение .*)$',t,re.M))
out=HERE/'Diploma_US_Financial_Conditions_Euro_Area.md'
out.write_text('\n'.join(toc)+'\n\n'+'\n\n'.join(f'<a id="{a}"></a>\n\n{t.strip()}' for a,t in parts)+'\n')
stats={'revision':28,'date':'2026-10-20','sources':59,'academic_works':45,'official_sources':14,'calculation_notes':len(kept),'words':{a:len(t.split()) for a,t in parts},'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths.values()},'chapter2_textual_changes':changes,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
(HERE/'ASSEMBLY.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'bytes':out.stat().st_size,'words':stats['words'],'sources':59},ensure_ascii=False))
