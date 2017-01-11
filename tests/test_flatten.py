import unittest

from sharingan.utils import flatten


class TestFlatten(unittest.TestCase):
    def test_nest_elems(self):
        elems = ([([([(1,), (2,)],), ([(3,)],)],), ([([(4,)],), ([(5,), (6,)],)],)],)
        self.assertEqual(flatten(elems, 0), elems)
        self.assertEqual(flatten(elems, 1), ([([(1,), (2,)],), ([(3,)],), ([(4,)],), ([(5,), (6,)],)],))
        self.assertEqual(flatten(elems, 2), ([(1,), (2,), (3,), (4,), (5,), (6,)],))
        self.assertEqual(flatten(elems, 3), ([1, 2, 3, 4, 5, 6],))
        self.assertEqual(flatten(elems, 4), ([1, 2, 3, 4, 5, 6],))
        self.assertEqual(flatten(elems), ([1, 2, 3, 4, 5, 6],))

    def test_nest_items(self):
        nest_item = ((((1,),),),)
        self.assertEqual(flatten(nest_item, 0), nest_item)
        self.assertEqual(flatten(nest_item, 1), (((1,),),))
        self.assertEqual(flatten(nest_item, 2), ((1,),))
        self.assertEqual(flatten(nest_item, 3), (1,))
        self.assertEqual(flatten(nest_item, 4), (1,))
        self.assertEqual(flatten(nest_item), (1,))

    def test_nest_list(self):
        nest_list = [[[1, 2], [3]], [[4], [5, 6]]]
        self.assertEqual(flatten(nest_list, 0), nest_list)
        self.assertEqual(flatten(nest_list, 1), [[1, 2], [3], [4], [5, 6]])
        self.assertEqual(flatten(nest_list, 2), [1, 2, 3, 4, 5, 6])
        self.assertEqual(flatten(nest_list, 3), [1, 2, 3, 4, 5, 6])
        self.assertEqual(flatten(nest_list, 4), [1, 2, 3, 4, 5, 6])
        self.assertEqual(flatten(nest_list), [1, 2, 3, 4, 5, 6])
