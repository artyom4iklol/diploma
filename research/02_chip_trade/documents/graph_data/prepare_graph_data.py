"""Prepare all 30 figure datasets from saved evidence. No network or re-estimation.

Usage: python prepare_graph_data.py /tmp/chip_graph_xlsx/graph_data.json
The companion artifact-tool builder creates the Excel workbook from this spec.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
REPO = PROJECT.parents[1]
DOC = PROJECT / "documents"
RISK = PROJECT / "risk_extension"
COUNTRIES = {392: "Япония", 410: "Республика Корея"}
GOODS = {854231: "Процессоры и контроллеры", 854232: "Память", 854233: "Усилители", 854239: "Прочие интегральные схемы"}
DIRS = {156: "Китай", 344: "Гонконг", 490: "Прочая Азия, н.в.д. (490)", 704: "Вьетнам", 702: "Сингапур", 608: "Филиппины", 842: "США", 764: "Таиланд", -1: "Остальные направления"}
SHEETS, CATALOG, SOURCES, CHECKS = [], [], [], []
N = '#,##0.00;[Black]-#,##0.00;0.00'
P = '0.0%;[Black]-0.0%;0.0%'
I = '0'

def read(rel, kind="json"):
    p = PROJECT / rel
    key = f"S{len(SOURCES)+1:02d}"
    SOURCES.append([key, str(p.relative_to(REPO)), hashlib.sha256(p.read_bytes()).hexdigest()])
    return (json.loads(p.read_text()) if kind == "json" else pd.read_csv(p)), key

def f(formula, expected):
    assert math.isfinite(float(expected)), (formula, expected)
    return {"formula": formula, "expected": float(expected)}

def date(period):
    return {"date": f"{int(period)//100:04d}-{int(period)%100:02d}-01"}

def col(n):
    out = ""
    while n:
        n, k = divmod(n-1, 26)
        out = chr(65+k) + out
    return out

def sheet(name, title, note, source="", figure=None, visual="", status="Расчёт по наблюдениям"):
    s = dict(name=name, title=title, note=note, source=source, sections=[], next_row=6)
    SHEETS.append(s)
    if figure:
        CATALOG.append(dict(figure=figure, title=title, sheet=name, visual=visual, status=status, obj=s))
    return s

def section(s, label, headers, rows, formats=None, widths=None, row=None):
    r = row or s["next_row"]
    sec = dict(label=label, header_row=r, headers=headers, rows=rows, formats=formats or {}, widths=widths or {})
    s["sections"].append(sec)
    s["next_row"] = r + len(rows) + 4
    return r+1

def ci(metric, reporter, block=12):
    return next(x for x in SAV["primary_intervals"] if x["reporter"]==reporter and x["metric"]==metric and x["block_months"]==block)

E, SE = read("documents/chapter2_evidence.json")
E3, S3 = read("documents/chapter3_evidence.json")
M, SM = read("documents/chapter3_market_evidence.json")
PANEL, SP = read("risk_extension/data/monthly_panel_full.csv.gz", "csv")
ANNUAL, SA = read("risk_extension/results/monthly/annual_indicators_from_months.csv", "csv")
SERIES, SS = read("risk_extension/results/monthly/risk_series.csv", "csv")
BRIDGE, SB = read("risk_extension/results/monthly/monthly_annual_bridge.csv", "csv")
RCHECKS, SC = read("risk_extension/results/monthly/risk_checks.csv", "csv")
SAV = E["saved_results"]
D = PANEL.loc[PANEL.cmdCode.isin(GOODS) & PANEL.partnerCode.ne(0)].copy()
assert D.refYear.between(2017, 2024).all()
assert not D.duplicated(["reporterCode", "period", "cmdCode", "partnerCode"]).any()
D["destination"] = D.partnerCode.where(D.partnerCode.isin(DIRS), -1)
MP = D.groupby(["reporterCode", "period", "cmdCode"]).primaryValue.sum().unstack("cmdCode").reindex(columns=GOODS)
MD = D.groupby(["reporterCode", "period", "destination"]).primaryValue.sum().unstack("destination").reindex(columns=DIRS)
assert MP.shape==(192,4) and MD.shape==(192,9) and MP.notna().all().all() and MD.notna().all().all()
assert np.allclose(MP.sum(axis=1), MD.sum(axis=1), atol=.01)
assert (MP > 0).all().all() and (MD > 0).all().all()
MONTHS = sorted(D.period.unique())
TOTAL = MP.sum(axis=1)
AP = {(int(x["reporterCode"]), int(x["refYear"]), int(x["cmdCode"])): x["export_usd"] for x in E["annual_products"]}
AT = {(x["reporterCode"],x["refYear"]):x["export_usd"] for x in E["annual_totals"]}
PRIMARY = {x["reporter"]:x for x in SAV["all_specifications"] if x["case"]=="primary"}
for (r,y),v in AT.items():
    assert abs(float(TOTAL.loc[r].loc[lambda x:x.index//100==y].sum())-v)<.1
OBS_G = {r:200*(TOTAL.loc[r].iloc[12:].to_numpy()-TOTAL.loc[r].iloc[:-12].to_numpy())/(TOTAL.loc[r].iloc[12:].to_numpy()+TOTAL.loc[r].iloc[:-12].to_numpy()) for r in COUNTRIES}
MPR = {(r,int(p)):7+i for i,(r,p) in enumerate(MP.index)}
MDR = {(r,int(p)):7+i for i,(r,p) in enumerate(MD.index)}

# Chapter 1: two conceptual diagrams and one explicit mathematical example.
s=sheet("1_1_Цепочка", "1.1 Международная цепочка создания интегральных схем", "Таблицы блоков и связей для схемы. Количественных долей производства здесь нет.", "OECD (2025), Mapping the Semiconductor Value Chain, DOI 10.1787/4154cdbf-en; глава 1.", "1.1", "Схема стадий и обеспечивающих ресурсов", "Концептуальная схема")
section(s,"Блоки",["ID","Блок","Роль"],[['DES','Проектирование','Архитектура и разработка схемы'],['FAB','Изготовление пластин','Производство кристаллов'],['ATP','Корпусирование и тестирование','Сборка, контроль и испытания'],['APP','Применение','Включение в конечное оборудование'],['EDA','Средства проектирования и IP','Обеспечивающий ресурс'],['EQUIP','Оборудование','Обеспечивающий ресурс'],['MAT','Материалы','Обеспечивающий ресурс']],widths={1:15,2:40,3:55})
section(s,"Связи",["Из блока","В блок","Подпись"],[['DES','FAB','Передача проекта'],['FAB','ATP','Кристаллы'],['ATP','APP','Готовые схемы'],['EDA','DES','Средства и лицензии'],['EQUIP','FAB','Технологическое оснащение'],['EQUIP','ATP','Средства сборки и тестирования'],['MAT','FAB','Производственные материалы'],['MAT','ATP','Материалы корпусирования']],widths={1:15,2:40,3:55})
s=sheet("1_2_Механизм", "1.2 Структура экспорта и условная волатильность", "Схема расчётных связей. Стрелки не обозначают установленный причинный эффект.", "Авторская схема по главе 1 и методике основной модели.", "1.2", "Блок-схема весов и совместной динамики", "Концептуальная схема")
section(s,"Блоки",["ID","Блок","Определение"],[['P','Товарные доли p','Доли четырёх кодов в экспорте'],['Q','География внутри товара q','Доли девяти направлений внутри каждого кода'],['W','Веса ячеек w','w = p × q'],['G','Рост ячеек g','Симметричный рост к тому же месяцу прошлого года'],['SIG','Ковариационная матрица Σ','История 2018–2024, 36 ячеек'],['V','Условная дисперсия V','V = w′Σw'],['SD','Условная волатильность','SD = √V']],widths={1:14,2:40,3:65})
section(s,"Связи",["Из блока","В блок","Подпись"],[['P','W','Товарная структура'],['Q','W','География'],['G','SIG','Совместная динамика'],['W','V','Фиксированные веса'],['SIG','V','Собственные дисперсии и ковариации'],['V','SD','Квадратный корень']],widths={1:14,2:40,3:65})
s=sheet("1_3_Учебный_пример", "1.3 Число рынков и корреляция: учебный пример", "Равные веса и одинаковая индивидуальная волатильность. Это не оценка по данным Японии или Кореи.", "Математическое тождество Var среднего равно σ²[ρ+(1−ρ)/N].", "1.3", "Три линии волатильности по числу рынков", "Условный учебный пример")
section(s,"Редактируемые параметры",["Параметр","Значение"],[["Индивидуальная SD, п.п.",10],["Корреляция ρ₁",0],["Корреляция ρ₂",.5],["Корреляция ρ₃",.9]],{2:"0.00"},{1:34,2:23})
rows=[]
for i,n in enumerate(range(1,21),15):
    rows.append([n]+[f(f'=$B$7*SQRT($B${j}+(1-$B${j})/A{i})',10*math.sqrt(rho+(1-rho)/n)) for j,rho in [(8,0),(9,.5),(10,.9)]])
section(s,"Данные кривых",["Число рынков","SD при ρ₁, п.п.","SD при ρ₂, п.п.","SD при ρ₃, п.п."],rows,{1:I,2:N,3:N,4:N},{1:34,2:23,3:23,4:23},row=14)

# Chapter 2: data and fixed saved model estimates.
s=sheet("2_01_Экспорт", "2.1 Экспорт и наблюдаемый месячный рост", "Номинальная стоимость в долларах США. Симметричный рост = 200 × (xₜ−xₜ₋₁₂)/(xₜ+xₜ₋₁₂), п.п.", SP, "2.1", "Две панели: стоимость и симметричный рост")
rows=[]
for i,p in enumerate(MONTHS,7):
    row=[date(p)]
    for r in COUNTRIES:
        sr=MPR[r,p]; row.append(f(f"='Месяцы_товары'!G{sr}/10^9",TOTAL.loc[r,p]/1e9))
    for r in COUNTRIES:
        if p<201801: row.append(None)
        else:
            a=MPR[r,p]; b=MPR[r,p-100]
            row.append(f(f"=200*('Месяцы_товары'!G{a}-'Месяцы_товары'!G{b})/('Месяцы_товары'!G{a}+'Месяцы_товары'!G{b})",200*(TOTAL.loc[r,p]-TOTAL.loc[r,p-100])/(TOTAL.loc[r,p]+TOTAL.loc[r,p-100])))
    rows.append(row)
section(s,"Месячные ряды",["Месяц","Япония, млрд долл.","Корея, млрд долл.","Рост Японии, п.п.","Рост Кореи, п.п."],rows,{1:'yyyy-mm',2:N,3:N,4:N,5:N},{1:16,2:24,3:24,4:24,5:24})
s=sheet("2_02_Товарные_индексы", "2.2 Индексы экспорта четырёх товарных групп", "Годовая номинальная стоимость. Для каждой страны и товара 2017 год = 100.", SE, "2.2", "Четыре линии в каждой из двух панелей")
for r,cn in COUNTRIES.items():
    start=s["next_row"]+1; rows=[]
    for k,y in enumerate(range(2017,2025)):
        rr=start+k
        rows.append([y]+[AP[r,y,g] for g in GOODS]+[f(f'={col(j)}{rr}/${col(j)}${start}*100',AP[r,y,g]/AP[r,2017,g]*100) for j,g in enumerate(GOODS,2)])
    section(s,cn,["Год"]+[f"{g}, долл." for g in GOODS]+[f"{GOODS[g]}, индекс" for g in GOODS],rows,{1:I,**{k:N for k in range(2,10)}},{1:14,**{k:24 for k in range(2,10)}})
s=sheet("2_03_Товарные_доли", "2.3 Товарная структура экспорта", "Доли четырёх кодов в общей стоимости их экспорта. Каждая строка даёт 100%.", SE, "2.3", "Столбцы с накоплением до 100%")
for r,cn in COUNTRIES.items():
    src=next(x for x in SHEETS if x["name"]=="2_02_Товарные_индексы")["sections"][list(COUNTRIES).index(r)]
    start=src["header_row"]+1; rows=[]
    for i,y in enumerate(range(2017,2025)):
        rr=start+i
        rows.append([y]+[f(f"='2_02_Товарные_индексы'!{col(j)}{rr}/SUM('2_02_Товарные_индексы'!B{rr}:E{rr})",AP[r,y,g]/AT[r,y]) for j,g in enumerate(GOODS,2)])
    section(s,cn,["Год"]+list(GOODS.values()),rows,{1:I,**{k:P for k in range(2,6)}},{1:15,2:28,3:20,4:20,5:28})
s=sheet("2_04_Прирост_экспорта", "2.4 Товарный вклад в прирост стоимости экспорта", "Разница 2024 и 2017 годов, млрд долл. Это изменение номинальной стоимости, а не разложение Шепли.", SE, "2.4", "Водопад от стоимости 2017 к стоимости 2024")
for r,cn in COUNTRIES.items():
    start=s["next_row"]+1; rows=[]
    vals=[AT[r,2017]/1e9]+[(AP[r,2024,g]-AP[r,2017,g])/1e9 for g in GOODS]+[AT[r,2024]/1e9]
    labels=["Экспорт 2017"]+list(GOODS.values())+["Экспорт 2024"]
    for i,(lab,v) in enumerate(zip(labels,vals)):
        rr=start+i
        if i in (0,5): rows.append([lab,"Итог",v,None,None,v])
        else:
            g=list(GOODS)[i-1]; rows.append([lab,"Изменение",f(f'=(E{rr}-D{rr})/10^9',v),AP[r,2017,g],AP[r,2024,g],f(f'=F{rr-1}+C{rr}',sum(vals[:i+1]))])
    section(s,cn,["Элемент","Роль столбца","Величина, млрд долл.","Товар 2017, долл.","Товар 2024, долл.","Накопленный итог, млрд долл."],rows,{3:N,4:N,5:N,6:N},{1:33,2:18,3:24,4:25,5:25,6:28})
s=sheet("2_05_Концентрация", "2.5 Товарная и географическая концентрация", "HHI от 0 до 1. Географический HHI рассчитан по всем отдельным партнёрам до объединения в остаток.", SA, "2.5", "Две панели HHI по годам")
rows=[]
for x in ANNUAL.loc[~ANNUAL.include_parts].to_dict("records"):
    rows.append([COUNTRIES[x["reporter"]],int(x["year"]),x["product_hhi"],x["hhi"]])
section(s,"Годовые показатели",["Страна","Год","Товарный HHI","Географический HHI"],rows,{2:I,3:'0.0000',4:'0.0000'},{1:26,2:14,3:25,4:28})
s=sheet("2_06_Рынки_2017_2024", "2.6 Изменение долей направлений экспорта", "Восемь отдельных направлений и остаток. Код 490 сохранён как Other Asia, nes.", SE, "2.6", "Парные точки 2017 и 2024 по направлениям")
ad={(x["reporterCode"],x["refYear"],x["destination"]):x for x in E["annual_destination_grid"]}
for r,cn in COUNTRIES.items():
    start=s["next_row"]+1; rows=[]
    for i,(d,dn) in enumerate(DIRS.items()):
        a,b=ad[r,2017,d],ad[r,2024,d]; rr=start+i
        rows.append([dn,str(d),a["share_pct"]/100,b["share_pct"]/100,f(f'=(D{rr}-C{rr})*100',b["share_pct"]-a["share_pct"]),a["export_usd"],b["export_usd"]])
    section(s,cn,["Направление","Код","Доля 2017","Доля 2024","Изменение, п.п.","Экспорт 2017, долл.","Экспорт 2024, долл."],rows,{3:P,4:P,5:N,6:N,7:N},{1:33,2:12,3:18,4:18,5:22,6:25,7:25})
within={(x["reporterCode"],x["refYear"],x["cmdCode"],x["destination"]):x for x in E["within_product_destination_endpoints"]}
s=sheet("2_07_Товар_рынок", "2.7 География внутри товарных групп в 2024 году", "Доля направления внутри каждого товара. Сумма по строке равна 100%.", SE, "2.7", "Две тепловые карты 4 × 9")
for r,cn in COUNTRIES.items():
    rows=[[GOODS[g]]+[within[r,2024,g,d]["within_product_share_pct"]/100 for d in DIRS] for g in GOODS]
    section(s,cn,["Товар"]+list(DIRS.values()),rows,{k:P for k in range(2,11)},{1:32,**{k:22 for k in range(2,11)}})
s=sheet("2_08_Эпизоды", "2.8 Экспорт в двух сопоставляемых эпизодах", "Квартальная сумма. IV квартал 2018 / 2022 года = 100. Без сезонной корректировки и причинной интерпретации.", SP, "2.8", "Четыре линии по относительному кварталу")
qtot={}
for r in COUNTRIES:
    for p in MONTHS:
        key=(r,int(p)//100,((int(p)%100)-1)//3+1); qtot[key]=qtot.get(key,0)+TOTAL.loc[r,p]
for r,cn in COUNTRIES.items():
    for base in (2018,2022):
        start=s["next_row"]+1; rows=[]
        for k in range(9):
            yy=base+(k+3)//4; qq=(k+3)%4+1; val=qtot[r,yy,qq]; rr=start+k
            rows.append([k,f'{yy} Q{qq}',val,f(f'=C{rr}/$C${start}*100',val/qtot[r,base,4]*100)])
        section(s,f'{cn}, база {base} Q4',["Кварталов от базы","Квартал","Экспорт, долл.","Индекс, база = 100"],rows,{1:I,3:N,4:N},{1:26,2:20,3:29,4:29})
states={"initial":"Товар 2017, география 2017","product_change":"Товар 2024, география 2017","geography_change":"Товар 2017, география 2024","final":"Товар 2024, география 2024"}
s=sheet("2_09_Четыре_структуры", "2.9 Волатильность четырёх условных структур", "Одна история 2018–2024, 84 месяца. 95% точечные интервалы, круговой блочный бутстрэп, блок 12 месяцев.", SE, "2.9", "Точки и 95% интервалы", "Сохранённые оценки модели")
rows=[]
for x in SAV["primary_states"]:
    z=ci(x["state"]+"_sd_pp",x["reporter"]);rr=7+len(rows)
    rows.append([COUNTRIES[x["reporter"]],states[x["state"]],x["sd_pp"],z["ci_low"],z["ci_high"],f(f'=C{rr}-D{rr}',x["sd_pp"]-z["ci_low"]),f(f'=E{rr}-C{rr}',z["ci_high"]-x["sd_pp"]),x["variance_pp2"],x["n"]])
section(s,"Состояния",["Страна","Структура","SD, п.п.","Нижняя 95%, п.п.","Верхняя 95%, п.п.","Ошибка вниз, п.п.","Ошибка вверх, п.п.","Дисперсия, п.п.²","Месяцев"],rows,{**{k:N for k in range(3,9)},9:I},{1:25,2:40,**{k:21 for k in range(3,10)}})
s=sheet("2_10_Шепли", "2.10 Разложение изменения дисперсии", "Дисперсия в п.п.². Товарный и географический вклады Шепли суммируются в полное изменение.", SE, "2.10", "Водопад дисперсии по двум странам", "Сохранённые оценки модели")
for r,cn in COUNTRIES.items():
    x=PRIMARY[r];ini=next(q["variance_pp2"] for q in SAV["primary_states"] if q["reporter"]==r and q["state"]=="initial");fin=next(q["variance_pp2"] for q in SAV["primary_states"] if q["reporter"]==r and q["state"]=="final")
    rows=[["Начальная дисперсия","Итог",ini,None,None],["Товарный вклад","Изменение",x["mix_variance_pp2"],ci("mix_variance_pp2",r)["ci_low"],ci("mix_variance_pp2",r)["ci_high"]],["Географический вклад","Изменение",x["geography_variance_pp2"],ci("geography_variance_pp2",r)["ci_low"],ci("geography_variance_pp2",r)["ci_high"]],["Конечная дисперсия","Итог",fin,None,None],["Полное изменение","Справочно",x["delta_variance_pp2"],ci("delta_variance_pp2",r)["ci_low"],ci("delta_variance_pp2",r)["ci_high"]]]
    section(s,cn,["Компонент","Роль","Оценка, п.п.²","Нижняя 95%, п.п.²","Верхняя 95%, п.п.²"],rows,{3:N,4:N,5:N},{1:34,2:20,3:24,4:27,5:27})
s=sheet("2_11_Память_и_состав", "2.11 Доля памяти и состав продукции вне памяти", "Два компонента товарного вклада. Исследовательское разложение с 95% точечными интервалами, блок 12.", SE, "2.11", "Два вклада и их интервалы по каждой стране", "Сохранённые оценки модели")
labels={"memory_share":"Изменение доли памяти","within_nonmemory_mix":"Состав продукции вне памяти"}
rows=[[COUNTRIES[x["reporter"]],labels[x["factor"]],x["estimate_variance_pp2"],x["ci_low"],x["ci_high"]] for x in SAV["memory_share_decomposition"] if x["factor"] in labels]
section(s,"Компоненты",["Страна","Компонент","Вклад, п.п.²","Нижняя 95%, п.п.²","Верхняя 95%, п.п.²"],rows,{3:N,4:N,5:N},{1:26,2:42,3:24,4:27,5:27})
s=sheet("2_12_Ковариации", "2.12 Источники географического вклада", "Собственные дисперсии и перекрёстные ковариации. Интервалы отдельных компонент не складываются.", SE, "2.12", "Разнонаправленные столбцы и итог", "Сохранённые оценки модели")
labels={"own_variances":"Собственные дисперсии","cross_covariances":"Перекрёстные ковариации"}
rows=[]
for r,cn in COUNTRIES.items():
    for x in SAV["covariance_attribution_intervals"]:
        if x["reporter"]==r and x["factor"]=="geography": rows.append([cn,labels[x["component"]],x["estimate_variance_pp2"],x["ci_low"],x["ci_high"]])
    z=ci("geography_variance_pp2",r);rows.append([cn,"Географический вклад, всего",PRIMARY[r]["geography_variance_pp2"],z["ci_low"],z["ci_high"]])
section(s,"Компоненты",["Страна","Компонент","Вклад, п.п.²","Нижняя 95%, п.п.²","Верхняя 95%, п.п.²"],rows,{3:N,4:N,5:N},{1:26,2:42,3:24,4:27,5:27})
s=sheet("2_13_Вклады_направлений", "2.13 Географический вклад по направлениям", "Исследовательские 95% точечные интервалы без поправки на множественные сравнения. Блок 12 месяцев.", SE, "2.13", "Горизонтальные точки с интервалами", "Сохранённые оценки модели")
rows=[[COUNTRIES[x["reporter"]],DIRS[x["destination"]],str(x["destination"]),x["estimate_variance_pp2"],x["ci_low"],x["ci_high"]] for x in SAV["destination_attribution_intervals"] if x["factor"]=="geography"]
section(s,"Вклады",["Страна","Направление","Код","Вклад, п.п.²","Нижняя 95%, п.п.²","Верхняя 95%, п.п.²"],rows,{4:N,5:N,6:N},{1:26,2:34,3:12,4:24,5:27,6:27})
s=sheet("2_14_Исключение_года", "2.14 Чувствительность к исключению одного года", "В каждом варианте 72 месяца вместо 84. Границы интервалов здесь не оценивались.", SE, "2.14", "Линии оценок по исключённому году", "Сохранённая проверка чувствительности")
rows=[[COUNTRIES[x["reporter"]],x["omitted_year"],x["n"],x["delta_sd_pp"],PRIMARY[x["reporter"]]["delta_sd_pp"],x["mix_variance_pp2"],x["geography_variance_pp2"]] for x in SAV["leave_one_year_out"]]
section(s,"Оценки при исключении года",["Страна","Исключённый год","Месяцев","ΔSD, п.п.","Основная ΔSD, п.п.","Товарный вклад, п.п.²","География, п.п.²"],rows,{2:I,3:I,4:N,5:N,6:N,7:N},{1:26,2:24,3:15,4:24,5:27,6:27,7:27})

# Chapter 3: saved scenarios and transparent scale arithmetic.
s=sheet("3_1_Сценарии_памяти", "3.1 Изменение доли памяти и условная волатильность", "База — структура 2024. История 2018–2024. 95% точечные интервалы изменения SD, блок 12 месяцев.", S3, "3.1", "Сценарные кривые и полосы интервалов", "Условный исторический сценарий")
rows=[]
for x in E3["scenarios"]:
    z=next(q for q in E3["paired_intervals"] if q["reporter"]==x["reporter"] and q["shift_pp"]==x["shift_pp"] and q["block_months"]==12)
    rows.append([COUNTRIES[x["reporter"]],x["shift_pp"],x["memory_share_pct"]/100,x["sd_pp"],x["delta_sd_pp"],z["ci_low"],z["ci_high"]])
section(s,"Сценарные оценки",["Страна","Сдвиг доли, п.п.","Доля памяти","SD, п.п.","ΔSD к базе, п.п.","Нижняя 95%, п.п.","Верхняя 95%, п.п."],rows,{2:N,3:P,4:N,5:N,6:N,7:N},{1:26,**{k:24 for k in range(2,8)}})
s=sheet("3_2_Масштаб_расширения", "3.2 Рост продукции вне памяти при неизменном экспорте памяти", "Условная арифметика объёмов. Снижение доли памяти на 2,5 или 5 п.п. обеспечивается ростом остальных групп.", f"{SE}, {S3}", "3.2", "Требуемый прирост в млрд долл. и процентах", "Условный расчёт масштаба")
rows=[]
for r,cn in COUNTRIES.items():
    base=AP[r,2024,854232]/AT[r,2024]
    for drop in (2.5,5):
        rr=7+len(rows);target=base-drop/100;mem=AP[r,2024,854232];other=AT[r,2024]-mem;extra=mem/target-mem-other
        rows.append([cn,drop,mem,other,f(f'=C{rr}/SUM(C{rr}:D{rr})',base),f(f'=E{rr}-B{rr}/100',target),f(f'=C{rr}/F{rr}-C{rr}-D{rr}',extra),f(f'=G{rr}/10^9',extra/1e9),f(f'=G{rr}/D{rr}',extra/other)])
        z=next(x for x in E3["scenarios"] if x["reporter"]==r and x["shift_pp"]==-drop)
        assert abs(extra-z["extra_remaining_export_usd_if_memory_unchanged"])<.001
section(s,"Условия и результат",["Страна","Снижение доли, п.п.","Память 2024, долл.","Вне памяти 2024, долл.","Базовая доля памяти","Целевая доля памяти","Дополнительный экспорт, долл.","Дополнительный экспорт, млрд долл.","Рост экспорта вне памяти"],rows,{2:N,3:N,4:N,5:P,6:P,7:N,8:N,9:P},{1:26,2:24,3:27,4:28,5:23,6:23,7:30,8:30,9:28})
s=sheet("3_3_Выбор_рынка", "3.3 Сравнение географических сценариев", "Дополнение = 1% экспорта 2024. Сравнение с пропорциональным расширением. Основные интервалы совместные для 8 рынков.", SM, "3.3", "Точки и одновременные 95% интервалы", "Условный исторический сценарий")
rows=[[COUNTRIES[x["reporter"]],DIRS[x["partner"]],x["delta_vs_reference_pp"],x["family_ci_low_b12"],x["family_ci_high_b12"],x["point_ci_low_b12"],x["point_ci_high_b12"],x["extra_export_usd"],x["reference_sd_pp"],x["scenario_sd_pp"]] for x in M["rows"]]
section(s,"Сравнение восьми направлений",["Страна","Направление","ΔSD к сравнению, п.п.","Совместная нижняя 95%","Совместная верхняя 95%","Точечная нижняя 95%","Точечная верхняя 95%","Добавка, долл.","SD сравнения, п.п.","SD сценария, п.п."],rows,{**{k:'0.0000' for k in range(3,8)},8:N,9:N,10:N},{1:26,2:34,**{k:26 for k in range(3,11)}})
s=sheet("3_4_Рост_по_ячейкам", "3.4 Требуемое расширение ячеек «товар — рынок»", "Процент от исходного экспорта ячейки в 2024 году. Значения свыше 1000% сохранены без усечения.", SM, "3.4", "Тепловые карты 8 × 3", "Условный расчёт масштаба")
for r,cn in COUNTRIES.items():
    rows=[]
    for d in list(DIRS)[:-1]:
        rows.append([DIRS[d]]+[next(x["required_growth_pct"]/100 for x in M["cell_growth"] if x["reporter"]==r and x["partner"]==d and x["good"]==g) for g in GOODS if g!=854232])
    section(s,cn,["Направление"]+[GOODS[g] for g in GOODS if g!=854232],rows,{2:P,3:P,4:P},{1:34,2:30,3:24,4:32})
start=s["next_row"]+1;rows=[]
for x in M["cell_growth"]:
    rr=start+len(rows);rows.append([COUNTRIES[x["reporter"]],DIRS[x["partner"]],str(x["good"]),x["baseline_export_usd"],x["extra_export_usd"],f(f'=E{rr}/D{rr}',x["required_growth_pct"]/100)])
section(s,"Исходные суммы сценария",["Страна","Направление","HS","Экспорт 2024, долл.","Добавка, долл.","Требуемый рост"],rows,{4:N,5:N,6:P},{1:26,2:34,3:14,4:28,5:28,6:26})
s=sheet("3_5_Этапы_проекта", "3.5 Этапы отбора и реализации проекта", "Предлагаемые критерии, а не наблюдаемые бюджеты или сроки. Численные пороги должны задаваться по конкретному контракту.", "Авторские предложения, глава 3.2–3.3; MSS (2025), MOTIE (2025), METI (2024), Socionext (2025).", "3.5", "Схема этапов и развилок решения", "Рекомендательная схема")
section(s,"Этапы и условия",["ID","Этап","Участники","Данные для решения","Продолжить","Пересмотреть / остановить"],[['SEL','Отбор проекта','Разработчик и заказчик','Изделие, покупатель, применение, территория отгрузки','Подтверждена задача покупателя','Не определены спрос или маршрут поставок'],['DEV','Разработка','Разработчик и производственные партнёры','Техническое задание, лицензии, NRE, бюджет образца','Согласованы характеристики и распределение затрат','Недоступен процесс или не согласовано возмещение затрат'],['PILOT','Квалификация и пилот','Производитель, испытатель и заказчик','Результаты испытаний, выход годных, цена, условия серии','Изделие принято, экономика заказа подтверждена','Требуются доработка, изменение цены или маршрута'],['SCALE','Расширение поставок','Компания и финансирующая сторона','Заказы, маржа, оборотный капитал, структура покупателей','Экономика серии и источники спроса проверены','Низкая отдача либо неучтённая зависимость от покупателя']],widths={1:12,2:30,3:40,4:58,5:54,6:58})
section(s,"Связи",["От этапа","К этапу","Условие"],[['SEL','DEV','Техническое задание и заказчик подтверждены'],['DEV','PILOT','Образец готов к квалификации'],['PILOT','SCALE','Квалификация и экономика серии подтверждены'],['PILOT','DEV','Нужна техническая доработка'],['SCALE','SEL','Пересмотр применения или покупателя']],widths={1:12,2:30,3:40})

# Appendix A–H.
s=sheet("ПА_Рост_товаров", "Приложение А. Месячный рост по товарам", "Симметричный рост агрегированного экспорта каждого товара к тому же месяцу прошлого года. Единицы — п.п.", SP, "ПА", "Две тепловые карты 4 × 84")
for r,cn in COUNTRIES.items():
    rows=[]
    for p in MONTHS[12:]:
        a,b=MPR[r,p],MPR[r,p-100];row=[date(p)]
        for j,g in enumerate(GOODS,3):
            c=col(j);cur,prev=MP.loc[(r,p),g],MP.loc[(r,p-100),g]
            row.append(f(f"=200*('Месяцы_товары'!{c}{a}-'Месяцы_товары'!{c}{b})/('Месяцы_товары'!{c}{a}+'Месяцы_товары'!{c}{b})",200*(cur-prev)/(cur+prev)))
        rows.append(row)
    section(s,cn,["Месяц"]+list(GOODS.values()),rows,{1:'yyyy-mm',**{k:N for k in range(2,6)}},{1:16,2:30,3:24,4:24,5:30})
s=sheet("ПБ_Корреляции", "Приложение Б. Корреляции роста направлений", "Корреляция Пирсона, 84 месяца. Рост рассчитан по сумме четырёх товаров каждого направления; это не матрица 36 ячеек модели.", SP, "ПБ", "Две корреляционные матрицы 9 × 9")
growth_matrices={}
for r in COUNTRIES:
    a=MD.loc[r].to_numpy();growth_matrices[r]=200*(a[12:]-a[:-12])/(a[12:]+a[:-12])
# Matrices occupy rows 6–15 and 19–28, growth inputs start at row 33 and 121.
for r,cn in COUNTRIES.items():
    grow=34 if r==392 else 122; matrix=np.corrcoef(growth_matrices[r],rowvar=False);rows=[]
    for i,d in enumerate(DIRS):
        rows.append([DIRS[d]]+[f(f'=CORREL({col(i+2)}{grow}:{col(i+2)}{grow+83},{col(j+2)}{grow}:{col(j+2)}{grow+83})',matrix[i,j]) for j in range(9)])
    section(s,cn,["Направление"]+list(DIRS.values()),rows,{k:'0.000' for k in range(2,11)},{1:34,**{k:23 for k in range(2,11)}},row=6 if r==392 else 19)
for r,cn in COUNTRIES.items():
    rows=[]
    for i,p in enumerate(MONTHS[12:]):
        a,b=MDR[r,p],MDR[r,p-100]
        rows.append([date(p)]+[f(f"=200*('Месяцы_рынки'!{col(j+3)}{a}-'Месяцы_рынки'!{col(j+3)}{b})/('Месяцы_рынки'!{col(j+3)}{a}+'Месяцы_рынки'!{col(j+3)}{b})",growth_matrices[r][i,j]) for j in range(9)])
    section(s,f'{cn}: рост направлений, п.п.',["Месяц"]+list(DIRS.values()),rows,{1:'yyyy-mm',**{k:N for k in range(2,11)}},{1:34,**{k:23 for k in range(2,11)}},row=33 if r==392 else 121)
s=sheet("ПВ_Условные_индексы", "Приложение В. Временные ряды условных индексов", "Значения условного симметричного роста, п.п. Общая история 2018–2024; меняются только фиксированные веса.", SS, "ПВ", "Парные линии исходной и конечной структуры", "Сохранённые ряды модели")
rows=[[COUNTRIES[x.reporter],date(x.period),x.initial*100,x.product_change*100,x.geography_change*100,x.final*100] for x in SERIES.loc[SERIES.case.eq('primary')].itertuples()]
section(s,"Условные ряды",["Страна","Месяц","Исходный, п.п.","Товар 2024, п.п.","География 2024, п.п.","Конечный, п.п."],rows,{2:'yyyy-mm',3:N,4:N,5:N,6:N},{1:26,2:16,3:23,4:26,5:28,6:25})
s=sheet("ПГ_Потоки_2024", "Приложение Г. Потоки от товаров к направлениям", "Экспорт 2024 года. Толщина связи равна стоимости. Схема не отражает маршрут производства или конечное потребление.", SE, "ПГ", "Диаграмма потоков (Санкей) по каждой стране")
rows=[]
for r,cn in COUNTRIES.items():
    for g,gn in GOODS.items():
        for d,dn in DIRS.items():
            v=within[r,2024,g,d]["export_usd"];rr=7+len(rows)
            rows.append([cn,f'{r}_P{g}',gn,f'{r}_D{d}',dn,v,f(f'=F{rr}/10^9',v/1e9)])
section(s,"Связи с весами",["Страна","ID товара","Товар","ID направления","Направление","Экспорт, долл.","Экспорт, млрд долл."],rows,{6:N,7:N},{1:26,2:20,3:34,4:23,5:34,6:27,7:25})
s=sheet("ПД_Блоки_бутстрэпа", "Приложение Д. Интервалы при блоках 6 и 12 месяцев", "1999 повторений. 95% интервалы. SD измеряется в п.п., дисперсия и вклады — в п.п.²; панели разделять по единицам.", SE, "ПД", "Парные интервалы для двух длин блока", "Сохранённая проверка чувствительности")
ml={"delta_sd_pp":("Изменение SD","п.п."),"delta_variance_pp2":("Изменение дисперсии","п.п.²"),"mix_variance_pp2":("Товарный вклад","п.п.²"),"geography_variance_pp2":("Географический вклад","п.п.²")}
rows=[[COUNTRIES[x["reporter"]],ml[x["metric"]][0],ml[x["metric"]][1],x["block_months"],PRIMARY[x["reporter"]][x["metric"]],x["ci_low"],x["ci_high"],x["repetitions"]] for x in SAV["primary_intervals"] if x["metric"] in ml]
section(s,"Интервалы",["Страна","Показатель","Единица","Блок, месяцев","Оценка","Нижняя 95%","Верхняя 95%","Повторений"],rows,{4:I,5:N,6:N,7:N,8:I},{1:26,2:32,3:15,4:22,5:23,6:23,7:23,8:19})
s=sheet("ПЕ_Окна_ковариации", "Приложение Е. Результаты на двух окнах ковариации", "Веса 2017 и 2024 фиксированы. Меняется только период оценки совместной динамики; это не разложение по двум временным переходам.", SE, "ПЕ", "Сопоставление вкладов по двум окнам", "Сохранённая проверка чувствительности")
rows=[[COUNTRIES[x["reporter"]],f'{int(x["sigma_start"])}–{int(x["sigma_end"])}',x["n"],x["delta_sd_pp"],x["delta_variance_pp2"],x["mix_variance_pp2"],x["geography_variance_pp2"]] for x in SAV["all_specifications"] if x["case"] in ('sigma_2018_2020','sigma_2021_2024')]
section(s,"Результаты",["Страна","Окно","Месяцев","ΔSD, п.п.","Δдисперсии, п.п.²","Товарный вклад, п.п.²","География, п.п.²"],rows,{3:I,4:N,5:N,6:N,7:N},{1:26,2:20,3:15,4:25,5:27,6:27,7:27})
s=sheet("ПЖ_Память_по_окнам", "Приложение Ж. Сценарии памяти на двух окнах", "База — структура 2024. В каждом окне изменение SD считается относительно базовой структуры на том же окне.", S3, "ПЖ", "Сценарные кривые по окнам 2018–2020 и 2021–2024", "Сохранённая проверка чувствительности")
rows=[[COUNTRIES[x["reporter"]],x["window"],x["n"],x["shift_pp"],x["sd_pp"],x["delta_sd_pp"]] for x in E3["windows"]]
section(s,"Сценарные оценки",["Страна","Окно","Месяцев","Сдвиг доли, п.п.","SD, п.п.","ΔSD к базе окна, п.п."],rows,{3:I,4:N,5:N,6:N},{1:26,2:20,3:15,4:26,5:25,6:30})
s=sheet("ПЗ_Сверка_годовых", "Приложение З. Сверка месячных и годовых данных", "96 сопоставимых пар, по 12 месяцев. Коды 8542 и 854290 служат контрольными рядами и не входят в четыре товара основной модели.", SB, "ПЗ", "Диаграмма рассеяния и относительные расхождения")
rows=[]
for x in BRIDGE.to_dict("records"):
    rr=7+len(rows);rows.append([COUNTRIES[x["reporterCode"]],int(x["refYear"]),str(x["cmdCode"]),"Основной" if x["cmdCode"] in GOODS else "Контрольный",int(x["monthly_observations"]),bool(x["comparable"]),x["official_annual_usd"],x["sum_months_usd"],f(f'=G{rr}/10^9',x["official_annual_usd"]/1e9),f(f'=H{rr}/10^9',x["sum_months_usd"]/1e9),f(f'=(H{rr}-G{rr})/G{rr}',x["relative_gap"])])
section(s,"Сопоставимые наблюдения",["Страна","Год","HS","Ряд","Месяцев","Сопоставимо","Годовой ответ, долл.","Сумма месяцев, долл.","Годовой, млрд долл.","Месяцы, млрд долл.","Относительное отклонение"],rows,{2:I,5:I,7:N,8:N,9:N,10:N,11:'0.000%'},{1:26,2:14,3:14,4:20,5:15,6:19,7:28,8:28,9:25,10:25,11:27})

# Source registry and processed monthly observations preserve the original unit.
s=sheet("Данные", "Источники и определения", "Реестр сохранённых данных и методических обозначений. Исходные суммы не округлялись перед расчётом.")
section(s,"Источники в репозитории artyom4iklol/diploma",["ID","Файл","SHA-256"],SOURCES,widths={1:12,2:100,3:80})
definitions=[['Источник статистики','UN Comtrade, ежемесячный экспорт, текущие доллары США.'],['Период данных','Январь 2017 — декабрь 2024. История годового месячного роста: 2018–2024.'],['Товары','854231; 854232; 854233; 854239. Родительский 8542 и части 854290 исключены.'],['Направления','156; 344; 490; 704; 702; 608; 842; 764 и остаток −1.'],['Код 490','Other Asia, nes. Исходное статистическое наименование сохранено.'],['Агрегирование','Строки World (partnerCode=0) исключены из суммы направлений.'],['Рост','Симметричный: 200 × (текущий − прошлогодний)/(текущий + прошлогодний), п.п.'],['Волатильность','Выборочное стандартное отклонение условного индекса, п.п.'],['Дисперсия','Квадрат волатильности, п.п.². Не смешивать со стоимостным приростом.'],['Основные интервалы','95%, 1999 повторений, парный круговой блочный бутстрэп, блок 12 месяцев.'],['Сценарии','Условные исторические сопоставления. Не прогноз и не оценка причинного эффекта.'],['Пересчёт','Простые преобразования — формулы Excel. Оценки модели и интервалы — сохранённые результаты Python.'],['Обновление модели','Изменение месячных данных в Excel не пересчитывает замороженные ковариации, Шепли и бутстрэп.'],['Пустые ячейки','Нет годового месячного роста в 2017: отсутствует база 2016. Не заменять нулями.'],['Нумерация','Новая расширенная программа 30 рисунков. Номера могут отличаться от старой сборки Word.']]
section(s,"Определения",["Термин","Пояснение"],definitions,widths={1:32,2:100})
goodsrows=[[str(g),gn] for g,gn in GOODS.items()]+[[str(d),dn] for d,dn in DIRS.items()]
section(s,"Справочник кодов",["Код","Название"],goodsrows,widths={1:32,2:100})
s=sheet("Месяцы_товары", "Месячные суммы по товарам", "Обработанные наблюдения: сумма отдельных направлений, World исключён. Доллары США, текущие цены.", SP)
rows=[]
for i,((r,p),vals) in enumerate(MP.iterrows(),7):
    rows.append([COUNTRIES[r],date(p)]+[float(vals[g]) for g in GOODS]+[f(f'=SUM(C{i}:F{i})',float(vals.sum()))])
section(s,"Месячные суммы",["Страна","Месяц"]+[f"{g}, долл." for g in GOODS]+["Всего, долл."],rows,{2:'yyyy-mm',**{k:N for k in range(3,8)}},{1:26,2:16,**{k:27 for k in range(3,8)}})
s=sheet("Месяцы_рынки", "Месячные суммы по направлениям", "Обработанные наблюдения: четыре товара, восемь направлений и остаток. Доллары США, текущие цены.", SP)
rows=[[COUNTRIES[r],date(p)]+[float(v[d]) for d in DIRS] for (r,p),v in MD.iterrows()]
section(s,"Месячные суммы",["Страна","Месяц"]+list(DIRS.values()),rows,{2:'yyyy-mm',**{k:N for k in range(3,12)}},{1:26,2:16,**{k:27 for k in range(3,12)}})

# Index explicitly lists every table range and intended chart columns.
plot_columns={
    '1.1':'A:C — блоки и связи', '1.2':'A:C — блоки и связи',
    '1.3':'Кривые: A:D. Параметры: справочно',
    '2.1':'Стоимость: A:C; рост: A,D:E с 2018 года',
    '2.2':'Год: A; индексы: F:I', '2.3':'Год: A; доли: B:E',
    '2.4':'Элементы: A; величины: C; роль итогов: B',
    '2.5':'Год: B; HHI: C:D; фильтр страны: A',
    '2.6':'Направления: A; доли: C:D', '2.7':'Товары: A; матрица долей: B:J',
    '2.8':'Относительный квартал: A; индекс: D',
    '2.9':'Структура: B; SD: C; ошибки вниз/вверх: F:G',
    '2.10':'Компоненты: A; величины: C; роль: B',
    '2.11':'Компоненты: B; оценка: C; границы: D:E',
    '2.12':'Компоненты: B; оценка: C; границы: D:E',
    '2.13':'Направления: B; оценка: D; границы: E:F',
    '2.14':'Год: B; ΔSD и база: D:E; фильтр страны: A',
    '3.1':'Сдвиг: B; ΔSD: E; границы: F:G',
    '3.2':'Снижение доли: B; млрд долл.: H; рост: I',
    '3.3':'Рынки: B; ΔSD: C; совместные границы: D:E',
    '3.4':'Матрицы: A:D; исходные суммы: справочно',
    '3.5':'Все столбцы: этапы, критерии и связи',
    'ПА':'Месяцы: A; рост: B:E; при необходимости транспонировать',
    'ПБ':'Матрицы: A:J; нижние таблицы — исходный рост',
    'ПВ':'Месяц: B; исходный и конечный: C,F; страна: A',
    'ПГ':'Узлы: B,D; подписи: C,E; вес связи: F или G',
    'ПД':'Оценка: E; границы: F:G; блок: D; единица: C',
    'ПЕ':'Окно: B; SD: D; дисперсия/вклады: E:G, отдельно',
    'ПЖ':'Сдвиг: D; ΔSD: F; группы: A:B',
    'ПЗ':'Рассеяние: I:J; отклонения: K; фильтры: A:F'
}
catalog_rows=[]
for item in CATALOG:
    ss=item.pop("obj")
    for sec in ss["sections"]:
        a=sec["header_row"];b=a+len(sec["rows"]);end=col(len(sec["headers"]))
        catalog_rows.append([item["figure"],item["title"].split('. ',1)[-1],item["sheet"],sec["label"],f'A{a}:{end}{b}',plot_columns[item['figure']],item["visual"],item["status"]])
index=sheet("Оглавление", "Данные для 30 рисунков исследования", "22 рисунка основного текста и 8 приложений. Таблицы можно выделять по диапазонам из оглавления.")
section(index,"Диапазоны данных",["Рисунок","Содержание","Лист","Панель / таблица","Диапазон с заголовками","Столбцы для графика","Вид рисунка","Характер данных"],catalog_rows,widths={1:12,2:58,3:32,4:38,5:25,6:58,7:50,8:40})
section(index,"Как пользоваться",["Действие","Пояснение"],[['Найти рисунок','Выберите номер и соответствующий лист. У каждого блока указан диапазон вместе с заголовками.'],['Выбрать значения','В столбцах подписаны единицы. Страна и период служат фильтрами; подписи берутся из заголовков.'],['Интервалы','Нижняя и верхняя границы — координаты интервала. Для полос погрешностей нужны расстояния от оценки.'],['Отрицательный вклад','Сохраняйте знак. Не превращайте отрицательные вклады в положительные доли круговой диаграммы.'],['Формулы','Ячейки с формулами пересчитывают простые показатели. Расчёты модели сохранены как числовые оценки.'],['Схемы','Для 1.1, 1.2 и 3.5 приведены блоки и связи. Числовые значения для них не выдуманы.']],widths={1:26,2:110})
SHEETS.insert(0,SHEETS.pop())
assert len(CATALOG)==30 and len(SHEETS)==34
for sh in SHEETS:
    assert len(sh["name"])<=31
    last=0
    for sec in sorted(sh["sections"],key=lambda z:z["header_row"]):
        assert sec["header_row"]>last
        last=sec["header_row"]+len(sec["rows"])
        assert all(len(row)==len(sec["headers"]) for row in sec["rows"]),sh["name"]
for r in COUNTRIES:
    gsum=sum(x["estimate_variance_pp2"] for x in SAV["destination_attribution_intervals"] if x["reporter"]==r and x["factor"]=="geography")
    assert abs(gsum-PRIMARY[r]["geography_variance_pp2"])<1e-8
    st=SERIES.loc[SERIES.case.eq('primary') & SERIES.reporter.eq(r)]
    assert abs((st.final.std(ddof=1)-st.initial.std(ddof=1))*100-PRIMARY[r]["delta_sd_pp"])<1e-10
    CHECKS.append(dict(country=COUNTRIES[r],months=96,growth_months=84,delta_sd_pp=PRIMARY[r]["delta_sd_pp"],geography_sum_error=gsum-PRIMARY[r]["geography_variance_pp2"]))
assert float(RCHECKS.loc[RCHECKS.case.eq('primary'),'variance_identity_max_error'].max())<1e-8
payload=dict(created_date="2026-10-21",sheets=SHEETS,catalog=CATALOG,sources=SOURCES,checks=CHECKS)
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,indent=2))
print(json.dumps(dict(sheets=len(SHEETS),figures=len(CATALOG),tables=sum(len(s['sections']) for s in SHEETS),checks=CHECKS),ensure_ascii=False))
