import unittest

from api.util.collection import x_prod


class TestCollection(unittest.TestCase):

    def test_x_prod_noswap(self):
        a = [1, 2, 3]
        b = [4, 5]
        expected = [(1, 4), (1, 5), (2, 4), (2, 5), (3, 4), (3, 5)]
        self.assertListEqual(sorted(expected), sorted(x_prod(a, b, swap=False)))

    def test_x_prod_swap(self):
        a = [1, 2, 3]
        b = [4, 5]
        expected = [(1, 4), (1, 5), (2, 4), (2, 5), (3, 4), (3, 5),
                    (4, 1), (5, 1), (4, 2), (5, 2), (4, 3), (5, 3)]
        self.assertListEqual(sorted(expected), sorted(x_prod(a, b, swap=True)))
