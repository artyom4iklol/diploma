"""Extract two explicitly selected historical cases; no fitting or data retrieval."""
from pathlib import Path
import csv
import json
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'chapter3/evidence'
ORIGINS=['2020Q4','2024Q4']
MODELS=['HIST','AR','AR_ESI','AR_ESI_NFCI','AR_ESI_ANFCI']
LABELS={'HIST':'HIST','AR':'AR','AR_ESI':'AR + ESI','AR_ESI_NFCI':'AR + ESI + NFCI','AR_ESI_ANFCI':'AR + ESI + ANFCI'}

def read(path):
    return list(csv.DictReader((ROOT/path).open(encoding='utf-8',newline='')))

def one(data,**conditions):
    rows=[r for r in data if all(r[k]==str(v) for k,v in conditions.items())]
    assert len(rows)==1,(conditions,len(rows))
    return rows[0]

def save(path,rows):
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

def num(value,digits=2):
    return f'{float(value):.{digits}f}'.replace('.',',').replace('-','−')

def date(value):
    y,m,d=value.split('-');return f'{d}.{m}.{y}'

def main():
    OUT.mkdir(exist_ok=True)
    cal=read('revision18/results/forecast_calendar_59.csv')
    anfci=read('revision19/results/ANFCI_calendar_59.csv')
    targets=read('revision18/results/evaluation_targets.csv')
    forecasts=read('revision25/results/forecasts.csv')
    guard=read('revision25/results/growth_guard.csv')
    common=set(r['origin'] for r in forecasts if r['h']=='1') & set(r['origin'] for r in forecasts if r['h']=='4')
    assert max(common)=='2024Q4'
    inputs=[];selected=[];outcomes=[]
    for origin in ORIGINS:
        c=one(cal,origin=origin);a=one(anfci,origin=origin)
        g=one(guard,variant='expanding',h=1,origin=origin)
        assert c['gdp_public_available']<=c['forecast_date']
        assert c['esi_public_available']<=c['forecast_date']
        assert c['nfci_vintage']<=c['forecast_date']
        assert a['anfci_vintage']<=c['forecast_date']
        inputs.append({**c,'anfci':a['anfci'],'anfci_vintage':a['anfci_vintage'],
                       'last_anfci_observation_used':a['last_anfci_observation_used'],
                       'weekly_values_used':a['weekly_values_used'],
                       'training_gx_min_h1':g['minimum'],'training_gx_max_h1':g['maximum'],
                       'growth_outside_training_h1':g['changed']})
        for h in [1,4]:
            t=one(targets,origin=origin,h=h)
            raw=[]
            for config in ['Q_raw','Q_clip_g']:
                for model in MODELS:
                    row=one(forecasts,variant='expanding',config=config,origin=origin,h=h,model=model)
                    actual=float(row['actual']);q=float(row['forecast'])
                    assert abs(actual-float(t['actual']))<1e-10
                    loss=(.1-int(actual<q))*(actual-q)
                    assert abs(loss-float(row['loss']))<1e-10
                    assert int(actual<q)==int(row['hit'])
                    selected.append(row)
                    if config=='Q_raw':raw.append(row)
            winner=min(raw,key=lambda r:float(r['loss']))
            outcomes.append({**t,'forecast_date':c['forecast_date'],
                             'raw_winner':winner['model'],'winner_loss':winner['loss'],
                             'raw_hits':sum(int(x['hit']) for x in raw)})
    save(OUT/'case_inputs.csv',inputs)
    save(OUT/'case_forecasts.csv',selected)
    save(OUT/'case_outcomes.csv',outcomes)
    headers=['15.01.2021','15.01.2025']
    info=['Таблица 3.2. Информационная часть реконструированных квартальных выпусков',
          '',f'| Показатель | {headers[0]} | {headers[1]} |','| --- | --- | --- |']
    def add(label,values):info.append('| '+label+' | '+' | '.join(values)+' |')
    add('Исходный квартал',[r['origin'] for r in inputs])
    add('Последний известный квартал ВВП',[r['growth_observed_quarter'] for r in inputs])
    add('Дата регулярного выпуска этого ВВП',[date(r['gdp_actual_regular_release']) for r in inputs])
    add('Фиксация европейского снимка / публикация бюллетеня',[date(r['gdp_freeze'])+' / '+date(r['gdp_public_available']) for r in inputs])
    add('Лаговый рост, годовая логарифмическая шкала, %',[num(r['gx']) for r in inputs])
    add('Месяцы ESI',[r['esi_months'].replace(';','; ') for r in inputs])
    add('Даты публикаций этих месяцев ESI',['; '.join(date(v) for v in r['esi_release_dates'].split(';')) for r in inputs])
    add('Среднее ESI',[num(r['esi']) for r in inputs])
    add('Версия NFCI и ANFCI',[date(r['nfci_vintage']) for r in inputs])
    add('Последняя использованная неделя обоих индексов',[date(r['last_nfci_observation_used']) for r in inputs])
    add('Квартальные средние NFCI / ANFCI',[num(r['nfci'],3)+' / '+num(r['anfci'],3) for r in inputs])
    add('Диапазон лагового роста в обучении, h=1',['['+num(r['training_gx_min_h1'])+'; '+num(r['training_gx_max_h1'])+']' for r in inputs])
    add('Выход текущего роста за этот диапазон',['Да' if r['growth_outside_training_h1']=='True' else 'Нет' for r in inputs])
    info+=['','Примечание. Исторические данные представлены в версии, использованной в исследовании. Сопоставлены исходные квартальные агрегаты, без сокращения охвата до M2. Числа индексов округлены только для представления. Источник: расчёты автора по сохранённым календарям.[^3-16]']
    pred=['Таблица 3.3. Прогнозы десятого процентиля в реконструированных выпусках',
          '', '| Модель | 15.01.2021, h=1 | 15.01.2021, h=4 | 15.01.2025, h=1 | 15.01.2025, h=4 |',
          '| --- | ---: | ---: | ---: | ---: |']
    for model in MODELS:
        values=[num(one(selected,origin=o,h=h,config='Q_raw',model=model)['forecast']) for o in ORIGINS for h in [1,4]]
        pred.append('| '+LABELS[model]+' | '+' | '.join(values)+' |')
    pred+=['','Примечание. Расширяющееся окно, исходная процедура Q_raw. Все значения — проценты в годовой логарифмической шкале. Цели h=1 — I квартал соответствующего года; h=4 — интервал с I по IV квартал. Здесь показаны прогнозы, без использования последующего факта. Источник: сохранённые расчёты автора.[^3-16]']
    assess=['Таблица 3.4. Последующая оценка выбранных выпусков по факту с ограниченной зрелостью',
            '', '| Дата прогноза / h | Целевой интервал | Оценочный факт, % | Публикация оценочной версии | Наименьшая потеря среди пяти исходных моделей | Потеря |',
            '| --- | --- | ---: | --- | --- | ---: |']
    for r in outcomes:
        period=r['target_start'] if r['target_start']==r['target_end'] else r['target_start']+'–'+r['target_end']
        assess.append('| '+' | '.join([date(r['forecast_date'])+' / '+r['h'],period,num(r['actual']),date(r['matured_public_date']),LABELS[r['raw_winner']],num(r['winner_loss'],4)])+' |')
    assess+=['','Примечание. Ранжирование относится к одной дате и одному горизонту, а не ко всей выборке. Оценочный факт имеет установленную в исследовании ограниченную зрелость; это не первая публикация ВВП и не современная окончательная история. Потеря рассчитана по неокруглённым значениям. Источник: расчёты автора.[^3-16]']
    for name,lines in [('case_inputs_table.md',info),('case_forecasts_table.md',pred),('case_outcomes_table.md',assess)]:
        (OUT/name).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    stats={'selected_origins':ORIGINS,'forecast_rows':len(selected),'raw_and_diagnostic':True,
           'independent_validation':False,'new_model_fits':0,'selection':'known diagnostic date plus last common date',
           'last_common_origin_verified':max(common),'loss_and_hit_checks_passed':True}
    (OUT/'case_verification.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(stats,ensure_ascii=False))

if __name__=='__main__':main()
