import unittest

from sharingan.pipelines import FragmentPipeline


def inc_one(num):
    return num + 1


def double_list(num_list):
    return num_list + num_list


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


if __name__ == '__main__':
    unittest.main()
