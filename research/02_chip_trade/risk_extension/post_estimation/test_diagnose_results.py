import unittest
import numpy as np

from diagnose_results import grouped_weights, grouped_split


class GroupedAttributionChecks(unittest.TestCase):
    def setUp(self):
        self.w0 = np.array([.2, .6, .2])
        self.w1 = np.array([.3, .4, .3])
        self.p0 = np.array([[.8, .2], [.3, .7], [.5, .5]])
        self.p1 = np.array([[.7, .3], [.6, .4], [.4, .6]])
        z = np.random.default_rng(7).normal(size=(20, 6))
        self.cov = z.T@z

    def split(self, w0, w1, p0=None, p1=None):
        a = grouped_weights(w0, self.p0 if p0 is None else p0,
                            w1, self.p1 if p1 is None else p1, 1)
        v = np.einsum('ij,ik,kj->j', a, self.cov, a)
        result = grouped_split(v)
        self.assertAlmostEqual(result.sum(), v[-1]-v[0], places=12)
        return result

    def test_unchanged_memory_share_has_zero_memory_contribution(self):
        w1 = np.array([.1, .6, .3])
        self.assertAlmostEqual(self.split(self.w0, w1)[0], 0, places=12)

    def test_unchanged_nonmemory_proportions_have_zero_within_contribution(self):
        self.assertAlmostEqual(self.split(self.w0, self.w1)[1], 0, places=12)

    def test_unchanged_geography_has_zero_geographic_contribution(self):
        self.assertAlmostEqual(self.split(self.w0, self.w1, p1=self.p0)[2], 0, places=12)


if __name__ == '__main__':
    unittest.main()
