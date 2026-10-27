"""Build the writing registers from saved results without trade downloads or model fits."""
from pathlib import Path
import hashlib,json,re
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'writing'
def load(path):return json.loads((ROOT/path).read_text())
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(path):return json.loads(pd.read_csv(ROOT/path).to_json(orient='records'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

sources=load('literature/expanded_catalog.json')
official=load('literature/official_sources_catalog.json')
access=load('literature/writing_reading_access.json')
updates={r['id']:r for r in access['updates']}
for row in sources:
    ident=row['id']
    row['bibliography_status']='eligible_when_actually_cited'
    row['use_rule']='Опора только на фактически проверенные фрагменты; выводы авторов отделять от наших результатов.'
    if ident=='S07':
        row['bibliography_status']='exclude_until_year_verified'
        row['use_rule']='Вспомогательный материал с непроверенным годом; не включать в финальную библиографию сейчас.'
    elif ident=='S09':
        row['use_rule']='Близкая публикация; основной полный текст не получен. Разрешены проверенные библиографические сведения и оговорка о неполном сопоставлении. Не приписывать результаты, не заявлять мировой приоритет.'
    elif ident in ['S01','S06']:
        row['use_rule']='Явно обозначить студенческий тип; использовать для сравнения постановок, не как единственную теоретическую опору.'
    if ident in updates:
        row['read_version']=updates[ident]['review_status']
        row['targeted_reading_use']=updates[ident]['permitted_use']
    row['sections']=[x.strip()for x in row['sections'].split(';')]
for row in official:
    row['sections']=[x.strip()for x in row['sections'].split(';')]
    row['use_rule']='Первичный источник определений или контекста. Продажи, регистрации и импорт имеют разный охват.'
    if row['id'] in ['O09','O10']:row['use_rule']='Последующий контекст 2026 года; не включать в оценочное окно 2021–2025 и не выводить неустановленные юридические параметры.'
save('source_use_register.json',{'date':'2026-10-26','scientific_and_student_works':sources,'official_sources':official,
     'citation_workflow':'S/O — устойчивые рабочие ID. В Word использовать обычные подстрочные сноски; итоговый список содержит только реально использованные и проверенные записи. Страницы не придумывать; у препринта указывать прочитанную версию.'})

evidence=[]
def add(ident,title,sections,files,values,interpretation):
    evidence.append({'id':ident,'title':title,'sections':sections,'source_files':files,'source_sha256':{p:sha(p)for p in files},'values':values,'interpretation':interpretation})

req='data/full_raw/request.json';raw='data/full_raw/eurostat_full.json'
add('E01','Охват и исходный ответ',['2.1'],[req],load(req),'Месячная импортная статистика Comext; происхождение не равно бренду. Сырой ответ проверяется отдельно по SHA-256 из запроса.')
add('E02','Наблюдаемость и восстановленные нули',['2.1'],['results/full/data_audit.json','results/full/observability_details.json'],
    load('results/full/data_audit.json'),'Нули восстановлены условно на неотрицательности, исчерпывающем агрегате и точном сложении. Они не объявляются явными опубликованными нулями.')
add('E03','Панель CN/REST и информативность модели',['2.1','2.2'],['results/augmented/data_audit.json','results/augmented/conditional_share_equivalence.json'],
    {'audit':load('results/augmented/data_audit.json'),'share_equivalence':load('results/augmented/conditional_share_equivalence.json')},'Сетка 9720 потоков отличается от 8500 модельных строк и 4118 информативных пар. REST — меняющийся остаток, не незатронутый контроль.')
f='results/full/annual_eu_flows.csv'
add('E04','Годовые количества и стоимость',['2.3','3.1'],[f],table(f),'Три новых автомобильных кода. Статистическая стоимость и количество, не весь рынок и не продажи.')
f='results/full/accounting_decompositions.json'
add('E05','Доли Китая и точные структурные вклады',['2.2','2.3','2.6','3.1'],[f],load(f),'Доли используют одинаковую выбранную корзину внешнего импорта. Вклады в процентных пунктах; бухгалтерское сложение не причинный механизм.')
f='results/full/china_value_change_accounting.json'
add('E06','Разложение изменения стоимости',['2.2','2.3'],[f],load(f),'Unit values отражают также модельный и качественный состав; компонент не называется чистой ценой.')
f='results/full/entry_concentration.csv'
add('E07','Концентрация по технологиям и доля BE/NL',['2.4','3.1','3.2'],[f],table(f),'HHI на шкале 0–1, эффективное число стран = 1/HHI. География оформления не равна конечному спросу или физической логистике.')
f='results/geography_focus/decompositions.json'
add('E08','Стандартизация и разложения концентрации',['2.2','2.4','2.6','3.1'],[f],load(f),'Показать оба начала 2023/2024, количество/стоимость, оба порядка замены и взаимодействие. Расчётные корзины не являются миром без пошлин.')
f='results/geography_focus/entry_margin_summary.csv'
add('E09','Продолжающие и новые положительные страны',['2.4','2.6','3.2'],[f],table(f),'Граница — положительный годовой поток по стране; не вход фирмы, модели или конечного покупателя. Выход HEV сохранён.')
fs=['results/augmented/rest_preferred_quantity.json','results/augmented/rest_preferred_value.json','results/augmented/paired_block_summary.json']
vals={}
for name in ['quantity','value']:
    m=load('results/augmented/rest_preferred_'+name+'.json')
    vals[name]={'n':m['n'],'outcome':m['outcome'],'coefficients':m['coefficients'],'ci_method':m['ci_method']}
vals['paired_block']=load(fs[2])
add('E10','Предпочтительные фазовые модели и интервалы',['2.2','2.5','2.6'],fs,vals,'Условные относительные множители гибрид/BEV у Китая относительно REST при контролях. Не причинный эффект и не рост фактических продаж. Интервалы приблизительные, условные на модели.')
f='results/augmented/coefficients.csv'
add('E11','Все расширенные спецификации',['2.5','2.6'],[f],table(f),'18 фиксированных вариантов; выбор предпочтительного не зависит от желаемого знака или значимости. Старая оценка 6,17 не заменяет текущую 1,510.')
fs=['results/augmented/rest_halfyear_quantity.json','results/augmented/rest_halfyear_value.json','results/augmented/rest_geographic_quantity.json','results/augmented/rest_geographic_value.json']
vals={Path(f).stem:{k:v for k,v in load(f).items()if k in ['coefficients','joint_pre_investigation','ci_method','n','outcome']}for f in fs}
add('E12','Предшествующая динамика и географические контрасты',['2.5','2.6'],fs,vals,'Полугодовая нормировка на 2022 раскрыта. Малые асимптотические p — диагностический сигнал, не экспериментальная проверка. Географические интервалы не доказывают разницу конечных рынков.')
f='results/augmented/clearance_jurisdiction_exposure.csv'
add('E13','Механические сценарии оформления',['3.2','3.4'],[f],table(f),'Колонки *_registered_units исторического файла означают учтённый таможенный ввоз, а не регистрации автомобилей. Фиксированная структура 2025; 10%/25% ограничения BE/NL без реакции. Это экспозиция, не потери продаж и не физическое закрытие порта.')
save('evidence_register.json',{'date':'2026-10-26','base_commit':'6ca3b0ecf3373fced79dd65f224913e3e9a94b8b','records':evidence})

# No refits: repeat integrity and adding-up checks against the saved original bytes.
checks={}
full=load('results/full/output_validation.json');aug=load('results/augmented/output_validation.json');geo=load('results/geography_focus/validation.json')
checks['prior_validation_reports_passed']=all(x['passed']for x in [full,aug,geo])
checks['raw_response_matches_request']=sha(raw)==load(req)['response_sha256']
fp=hashlib.sha256(b''.join((ROOT/p).read_bytes()for p in ['augmented_model_spec.json','ppml_engine_augmented.py','run_augmented_model.py','results/full/panel.csv'])).hexdigest()
checks['preferred_inputs_match_recorded_fingerprint']=fp==aug['fingerprint']
co=pd.read_csv(ROOT/'results/augmented/coefficients.csv');checks['eighteen_models_present']=co.model.nunique()==18
maxscore=0.
for name in co.model.unique():
    m=load('results/augmented/'+name+'.json')
    assert m['converged'] and m['fingerprint']==fp and m['separation']['positive_outcome_removed']==0
    maxscore=max(maxscore,m['max_fe_score_over_total_y'],m['max_x_score_over_total_y'])
checks['all_scores_and_model_provenance_valid']=maxscore<1e-8
draw=load('results/augmented/paired_block_draws.json')['draws']
checks['all_398_weighted_refits_successful']=len(draw)==398 and all(x['success']for x in draw)
checks['independent_full_panel_equivalence_passed']=load('results/augmented/conditional_share_equivalence.json')['passed']
g=load('results/geography_focus/decompositions.json')
checks['all_sixteen_concentration_identities_exact']=len(g['pooled'])==4 and len(g['by_category'])==12 and all(abs(x['identity_error'])<1e-12 for x in g['pooled']+g['by_category'])
for row in g['pooled']:assert abs(row['HHI_change']-row['product_mix_component']-row['within_product_geography_component'])<1e-12
checks['all_evidence_files_exist']=all((ROOT/p).is_file()for x in evidence for p in x['source_files'])
ids={x['id']for x in sources+official};eids={x['id']for x in evidence}
texts='\n'.join((OUT/p).read_text()for p in ['RESEARCH_PASSPORT.md','CHAPTER_EVIDENCE_MAP.md'])
checks['source_and_evidence_ids_resolved']=set(re.findall(r'\b[SO]\d{2}\b',texts))<=ids and set(re.findall(r'\bE\d{2}\b',texts))<=eids
checks['literature_depth_and_exclusion_disclosed']=len(sources)==31 and len(official)==10 and next(x for x in sources if x['id']=='S07')['bibliography_status']=='exclude_until_year_verified'
checks['hypotheses_retrospective_and_PHEV_interval_disclosed']='не является предварительной регистрацией' in texts and '[0,748; 3,050]'in texts
result={'date':'2026-10-26','passed':all(checks.values()),'checks':checks,'max_relative_score':maxscore,'evidence_groups':len(evidence),'research_records':len(sources),'official_records':len(official),
        'main_period':'2021-01/2025-12','source_file_hashes':{p:sha(p)for p in sorted({p for x in evidence for p in x['source_files']})},
        'readiness':'ready_to_start_chapter_1','not_yet_completed':['chapter_texts','final_figures','final_thesis_word','final_cited_only_bibliography'],
        'not_claimed':['causal_identification','universal_novelty','full_reading_of_all_sources','journal_acceptance']}
save('WRITING_CHECKS.json',result)
assert result['passed'],result
print(json.dumps({k:v for k,v in result.items()if k!='source_file_hashes'},ensure_ascii=False,indent=2))
