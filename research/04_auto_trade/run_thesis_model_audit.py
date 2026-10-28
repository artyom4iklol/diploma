"""Post-analysis NL-only diagnostic with the unchanged preferred specification.

The only sample change is exclusion of NL. Both outcomes are required, all
results are retained, and no existing model outputs are overwritten.
"""
from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np
import ppml_engine_augmented as engine
from audit_thesis_strengthening import write

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/thesis_audit'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources=['results/augmented/panel_china_rest.csv','ppml_engine_augmented.py','augmented_model_spec.json']
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources}
    panel=pd.read_csv(ROOT/sources[0]);rows=[];validation={}
    for outcome,suffix in [('quantity','quantity'),('value_eur','value')]:
        full,sep=engine.trim_separation(panel,outcome)
        fitted=engine.fit(full,outcome);baseline=json.loads((ROOT/f'results/augmented/rest_preferred_{suffix}.json').read_text())
        delta=max(abs(float(b)-c['beta'])for b,c in zip(fitted['beta'],baseline['coefficients']))
        assert delta<1e-8,delta
        selected=panel[panel.reporter!='NL'];df,separation=engine.trim_separation(selected,outcome)
        result=engine.fit(df,outcome);summary=engine.summarize(result)
        summary.update({'outcome':outcome,'diagnostic':'Preferred four-FE design, same 2021-2025 period; exclude NL only; post-analysis robustness, not replacement of preferred model.', 'separation':separation,'source_sha256':source_hashes})
        assert summary['converged'] and summary['max_x_score_over_total_y']<1e-8 and summary['max_fe_score_over_total_y']<1e-8
        assert separation['positive_outcome_removed']==0
        write(OUT/f'exclude_NL_{suffix}.json',json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        validation[outcome]={'baseline_max_beta_difference':delta,'converged':True,'n':len(df),'positive_rows_removed':0,'max_x_score_over_total_y':summary['max_x_score_over_total_y'],'max_fe_score_over_total_y':summary['max_fe_score_over_total_y']}
        for c in summary['coefficients']:
            if not c['term'].endswith('__definitive'):continue
            before=next(x for x in baseline['coefficients']if x['term']==c['term'])
            rows.append({'outcome':outcome,'category':c['term'].split('__')[0],'full_multiplier':before['multiplier'],'exclude_NL_multiplier':c['multiplier'],'hac6_lo':c['hac6']['multiplier_ci95'][0],'hac6_hi':c['hac6']['multiplier_ci95'][1],'hac12_lo':c['hac12']['multiplier_ci95'][0],'hac12_hi':c['hac12']['multiplier_ci95'][1],'n':len(df)})
    for p,sha in source_hashes.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha
    write(OUT/'exclude_NL_comparison.csv',pd.DataFrame(rows).to_csv(index=False))
    result={'date':'2026-10-28','post_analysis':True,'preferred_model_unchanged':True,'diagnostic_models':2,'baseline_reproduction_fits':2,'source_sha256':source_hashes,'validation':validation,'all_passed':True,'limits':['Excluding NL changes the geographic estimand and does not correct the original source.','Only HAC uncertainty is recomputed for this diagnostic; no new block intervals are claimed.','Conditional associations remain noncausal.']}
    write(OUT/'model_audit_validation.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(pd.DataFrame(rows).to_string(index=False));print(json.dumps(result))


if __name__=='__main__':main()
