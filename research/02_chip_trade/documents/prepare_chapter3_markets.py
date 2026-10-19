"""Equal-size geographic expansion comparisons, conditional on the saved panel."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
RISK=HERE.parent/'risk_extension'
sys.path.insert(0,str(RISK))
from analyze_monthly import cube,growth,periods

GOODS=(854231,854232,854233,854239)
SEED,NBOOT,EXPANSION=20261019,1999,.01
NAMES={156:'Китай',344:'Гонконг',490:'Other Asia, nes',704:'Вьетнам',702:'Сингапур',608:'Филиппины',842:'США',764:'Таиланд'}

def main():
    paths=[RISK/'data/monthly_panel_full.csv.gz',RISK/'results/monthly/risk_summary.csv',
           RISK/'results/monthly/risk_states.csv',HERE/'chapter3_market_protocol.md',Path(__file__)]
    panel=pd.read_csv(paths[0]);summary=pd.read_csv(paths[1]);states=pd.read_csv(paths[2])
    directions=[int(x) for x in summary.loc[summary.case.eq('primary'),'directions'].iloc[0].split(';')]
    assert set(directions)==set(NAMES)
    rows,checks,windows,cell_rows=[],[],[],[]
    for reporter in (392,410):
        x=cube(panel,reporter,GOODS,directions,2024);g=growth(x,12).reshape(84,36)
        assert np.isfinite(g).all()
        annual=x[periods(2024)//100==2024].sum(axis=0)
        assert (annual>0).all()
        total=annual.sum();other=np.array([0,2,3]);product=annual.sum(axis=1)
        proportions=product[other]/product[other].sum();extra=total*EXPANSION
        additions=[]
        prop=np.zeros_like(annual);prop[other]=extra*proportions[:,None]*annual[other]/product[other,None]
        additions.append(prop)
        for j in range(8):
            a=np.zeros_like(annual);a[other,j]=extra*proportions;additions.append(a)
        augmented=np.array([annual+a for a in additions])
        w=augmented.reshape(9,36).T/(total+extra)
        assert np.all(w>=0) and np.allclose(w.sum(axis=0),1,atol=1e-13)
        assert np.allclose(augmented.sum(axis=2),augmented[0].sum(axis=1),atol=1e-5)
        assert all(abs(a.sum()-extra)<1e-5 for a in additions)
        y=g@w;sd=y.std(axis=0,ddof=1)*100;delta=sd[1:]-sd[0]
        base_sd=np.std(g@(annual/total).reshape(36),ddof=1)*100
        saved=float(states.loc[states.case.eq('primary')&states.reporter.eq(reporter)&states.state.eq('final'),'variance_pp2'].iloc[0])
        assert abs(base_sd**2-saved)<1e-8
        cov=np.cov(g,rowvar=False,ddof=1)
        variance_error=float(np.max(np.abs(np.einsum('ik,ij,jk->k',w,cov,w)*10000-sd**2)))
        assert variance_error<1e-8
        ints={}
        for block in (12,6):
            rng=np.random.default_rng(SEED)
            starts=rng.integers(0,84,size=(NBOOT,int(np.ceil(84/block))))
            ix=((starts[:,:,None]+np.arange(block))%84).reshape(NBOOT,-1)[:,:84]
            bsd=np.std(y[ix],axis=1,ddof=1)*100
            bd=bsd[:,1:]-bsd[:,[0]]
            point=np.quantile(bd,[.025,.975],axis=0)
            radius=float(np.quantile(np.max(np.abs(bd-delta),axis=1),.95))
            ints[block]=(point,radius)
        for j,partner in enumerate(directions):
            r=dict(reporter=reporter,partner=partner,partner_name=NAMES[partner],
                baseline_sd_pp=float(base_sd),reference_sd_pp=float(sd[0]),scenario_sd_pp=float(sd[j+1]),
                delta_vs_reference_pp=float(delta[j]),extra_export_usd=float(extra),
                destination_remaining_export_usd=float(annual[other,j].sum()),
                required_destination_growth_pct=float(extra/annual[other,j].sum()*100),
                max_required_cell_growth_pct=float(np.max(extra*proportions/annual[other,j])*100),
                max_required_cell_good=int(GOODS[other[np.argmax(extra*proportions/annual[other,j])]]),
                baseline_memory_share_pct=float(product[1]/total*100),
                scenario_memory_share_pct=float(product[1]/(total+extra)*100))
            for block,(point,radius) in ints.items():
                r.update({f'point_ci_low_b{block}':float(point[0,j]),f'point_ci_high_b{block}':float(point[1,j]),
                          f'family_ci_low_b{block}':float(delta[j]-radius),f'family_ci_high_b{block}':float(delta[j]+radius),
                          f'family_radius_b{block}':radius})
            rows.append(r)
            for k,share in zip(other,proportions):
                cell_rows.append(dict(reporter=reporter,partner=partner,good=GOODS[k],
                    baseline_export_usd=float(annual[k,j]),extra_export_usd=float(extra*share),
                    required_growth_pct=float(extra*share/annual[k,j]*100)))
        years=periods(2024)[12:]//100
        for low,high in ((2018,2020),(2021,2024)):
            z=y[(years>=low)&(years<=high)].std(axis=0,ddof=1)*100
            for j,partner in enumerate(directions):windows.append(dict(reporter=reporter,partner=partner,window=f'{low}–{high}',delta_vs_reference_pp=float(z[j+1]-z[0])))
        checks.append(dict(reporter=reporter,finite_growth_cells=int(g.size),positive_cells=True,
             nonnegative_normalized_weights=True,equal_product_shares=True,equal_expansion=True,
             saved_baseline_error_pp2=abs(base_sd**2-saved),variance_identity_error_pp2=variance_error))
    out=dict(protocol='chapter3_market_protocol.md',expansion_share=EXPANSION,seed=SEED,repetitions=NBOOT,
             rows=rows,windows=windows,cell_growth=cell_rows,checks=checks,
             input_sha256={str(p.relative_to(HERE.parents[2])):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (HERE/'chapter3_market_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    pd.DataFrame(rows).to_csv(HERE/'chapter3_markets.csv',index=False,float_format='%.12g')
    print(pd.DataFrame(rows)[['reporter','partner_name','delta_vs_reference_pp','family_ci_low_b12','family_ci_high_b12','required_destination_growth_pct']].to_string(index=False))

if __name__=='__main__':main()
