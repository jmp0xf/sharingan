import unittest

from sharingan.pipelines import FragmentPipeline


def inc_one(num):
    return num + 1


def double_list(num_list):
    return num_list + num_list


def append_elem(elem):
    yield elem
    if elem == 2:
        yield 3


def duplicate(elem):
    yield elem
    yield elem

class TestApplyMethod(unittest.TestCase):
    def setUp(self):
        self.pipeline = FragmentPipeline()

    def test_nest_item(self):
        self.assertEqual(self.pipeline.apply_method(inc_one, ({'num': 1},)), (2,))

    def test_list_item(self):
        self.assertEqual(self.pipeline.apply_method(inc_one, ([({'num': 1},)],)), ([(2,)],))

    def test_list_value(self):
        self.assertEqual(self.pipeline.apply_method(double_list, ({'num_list': [1]},)), ([1, 1],))

    def test_nest_list_value(self):
        self.assertEqual(self.pipeline.apply_method(double_list, (({'num_list': [1]},),)), (([1, 1],),))

    def test_append_elem(self):
        self.assertEqual(self.pipeline.apply_method(append_elem, ([({'elem': 1},), ({'elem': 2},)],)),
                         ([(1,), (2,), (3,)],))

    def test_duplicate(self):
        self.assertEqual(self.pipeline.apply_method(duplicate, ([({'elem': 1},), ({'elem': 2},)],)),
                         ([(1,), (1,), (2,), (2,)],))

if __name__ == '__main__':
    unittest.main()
