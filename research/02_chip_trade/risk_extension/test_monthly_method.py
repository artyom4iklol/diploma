"""Economically interpretable controls for the new numerical analysis.

Synthetic fixtures are tests only; they are never written to research outputs.
"""
import unittest
import numpy as np
import pandas as pd
from analyze_monthly import GOODS,REPORTERS,growth,run_case,bootstrap,periods


def fixture(change_products=False,change_geography=False):
    rows=[]
    for reporter in REPORTERS:
        for t,period in enumerate(periods(2020)):
            total=1e6*np.exp(.005*t+.1*np.sin(t/4)+.07*np.cos(t/7))
            w=np.exp(np.array([0.,.3,.6,.9])*(1+t/40 if change_products else 1))
            w=w/w.sum()
            p=np.exp(np.array([1.,.7,.2,0.])*(1+t/50 if change_geography else 1))
            p=p/p.sum()
            for i,cmd in enumerate(GOODS):
                for j,destination in enumerate([156,344,702,842]):
                    rows.append(dict(reporterCode=reporter,period=int(period),refYear=int(period)//100,
                                     cmdCode=cmd,partnerCode=destination,primaryValue=total*w[i]*p[j]))
    return pd.DataFrame(rows)


class MonthlyMethodControls(unittest.TestCase):
    def run_fixture(self,data):
        return run_case(data,'synthetic_control',end_year=2020,final_year=2020,
                        sigma_end=2020,directions=[156,344,702])

    def test_unchanged_structure_has_no_attributed_effect(self):
        output=self.run_fixture(fixture())
        for row in output['summary']:
            self.assertEqual(row['status'],'ok')
            self.assertAlmostEqual(row['delta_variance_pp2'],0,places=8)
            self.assertAlmostEqual(row['mix_variance_pp2'],0,places=8)
            self.assertAlmostEqual(row['geography_variance_pp2'],0,places=8)

    def test_product_only_change_has_zero_geographic_contribution(self):
        for row in self.run_fixture(fixture(change_products=True))['summary']:
            self.assertAlmostEqual(row['geography_variance_pp2'],0,places=8)

    def test_geography_only_change_has_zero_product_contribution(self):
        for row in self.run_fixture(fixture(change_geography=True))['summary']:
            self.assertAlmostEqual(row['mix_variance_pp2'],0,places=8)

    def test_zero_flow_does_not_become_zero_risk(self):
        g=growth(np.array([[0.],[0.],[5.],[0.]]),1).ravel()
        self.assertTrue(np.isnan(g[0]))
        self.assertEqual(g[1],2)
        self.assertEqual(g[2],-2)

    def test_paired_bootstrap_preserves_identical_portfolios(self):
        y=np.tile(np.sin(np.arange(36)/3)[:,None],(1,4))
        rows=bootstrap(y,block=12,repetitions=99)
        for row in rows:
            if row['metric'] in ['delta_variance_pp2','mix_variance_pp2','geography_variance_pp2','delta_sd_pp']:
                self.assertEqual(row['ci_low'],0)
                self.assertEqual(row['ci_high'],0)


if __name__=='__main__':unittest.main()
