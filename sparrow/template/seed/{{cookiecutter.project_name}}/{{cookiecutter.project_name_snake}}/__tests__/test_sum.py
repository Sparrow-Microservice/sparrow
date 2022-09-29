# -*- coding: utf-8 -*-
import unittest


class SumTest(unittest.TestCase):

    def f(self, a, b):
        return a + b

    def test_sum(self):
        a = 10
        b = 20
        print('******************', a, b)
        self.assertEqual(a + b, self.f(a, b))


if __name__ == '__main__':
    unittest.main()
