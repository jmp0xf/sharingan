import unittest

from scrapy.item import Field

from sharingan.item import FragmentItem, pack_args


class TestItem(FragmentItem):
    a = Field()

class Test2Item(FragmentItem):
    a = Field()
    b = Field()

class AItem(FragmentItem):
    b = Field()


class BItem(FragmentItem):
    c = Field()


class CItem(FragmentItem):
    d = Field()

class TestPackArgs(unittest.TestCase):
    def test_single_value(self):
        item = TestItem()
        item['a'] = 1
        self.assertEqual(pack_args(item, 'a'), ({'a': 1},))

    def test_list_value(self):
        item = TestItem()
        item['a'] = [1]
        self.assertEqual(pack_args(item, 'a'), ({'a': [1]},))

    def test_nest_single_value(self):
        item = TestItem()
        a = AItem()
        item['a'] = a
        a['b'] = 1
        self.assertEqual(pack_args(item, 'a__b'), (({'a__b': 1},),))
        item['a'] = [a]
        self.assertEqual(pack_args(item, 'a__b'), ([({'a__b': 1},)],))

    def test_nest_list_value(self):
        item = TestItem()
        a = AItem()
        item['a'] = a
        a['b'] = [1]
        self.assertEqual(pack_args(item, 'a__b'), (({'a__b': [1]},),))
        item['a'] = [a]
        self.assertEqual(pack_args(item, 'a__b'), ([({'a__b': [1]},)],))

    def test_list_items_list_items_single_value(self):
        item = TestItem()
        a1 = AItem()
        a2 = AItem()
        b1 = BItem()
        b2 = BItem()
        b3 = BItem()
        b1['c'] = 1
        b2['c'] = 2
        b3['c'] = 3
        a1['b'] = [b1, b2]
        a2['b'] = [b3]
        item['a'] = [a1, a2]
        self.assertEqual(pack_args(item, 'a__b__c'), ([([({'a__b__c': 1},), ({'a__b__c': 2},)],), ([({'a__b__c': 3},)],)],))

    def test_complex_case(self):
        item = TestItem()
        a1 = AItem()
        a2 = AItem()
        b1 = BItem()
        b2 = BItem()
        b3 = BItem()
        b4 = BItem()
        c1 = CItem()
        c2 = CItem()
        c3 = CItem()
        c4 = CItem()
        c5 = CItem()
        c6 = CItem()
        c1['d'] = 1
        c2['d'] = 2
        c3['d'] = 3
        c4['d'] = 4
        c5['d'] = 5
        c6['d'] = 6
        b2['c'] = [c3]
        b3['c'] = [c4]
        b4['c'] = [c5, c6]
        a1['b'] = [b1, b2]
        a2['b'] = [b3, b4]
        b1['c'] = [c1, c2]
        item['a'] = [a1, a2]
        list_items_args = ([([([({'a__b__c__d': 1},), ({'a__b__c__d': 2},)],), ([({'a__b__c__d': 3},)],)],),
                 ([([({'a__b__c__d': 4},)],), ([({'a__b__c__d': 5},), ({'a__b__c__d': 6},)],)],)],)
        self.assertEqual(pack_args(item, 'a__b__c__d'), list_items_args)
        single_item_args = (([([({'a__b__c__d': 1},), ({'a__b__c__d': 2},)],), ([({'a__b__c__d': 3},)],)],),)
        item['a'] = a1
        self.assertEqual(pack_args(item, 'a__b__c__d'), single_item_args)

    def test_wildcard(self):
        item = TestItem()
        a = AItem()
        b1 = BItem()
        b2 = BItem()
        b1['c'] = 1
        b2['c'] = 2
        a['b'] = [b1, b2]
        item['a'] = [a]
        self.assertEqual(pack_args(item, 'a__b__c'), ([([({'a__b__c': 1},), ({'a__b__c': 2},)],)],))
        self.assertEqual(pack_args(item, 'a__b__'), ([([({'a__b__': {'c': 1}},), ({'a__b__': {'c': 2}},)],)],))
        self.assertEqual(pack_args(item, 'a__'), ([({'a__': {'b': [{'c': 1}, {'c': 2}]}},)],))
        self.assertEqual(pack_args(item, 'a__b'), ([({'a__b': [{'c': 1}, {'c': 2}]},)],))
        self.assertEqual(pack_args(item, 'a'), ({'a': [{'b': [{'c': 1}, {'c': 2}]}]},))
        item['a'] = a
        self.assertEqual(pack_args(item, 'a__'), (({'a__': {'b': [{'c': 1}, {'c': 2}]}},),))
        self.assertEqual(pack_args(item, 'a__b'), (({'a__b': [{'c': 1}, {'c': 2}]},),))
        self.assertEqual(pack_args(item, 'a'), ({'a': {'b': [{'c': 1}, {'c': 2}]}},))

    def test_wildcard_for_single_value(self):
        item = Test2Item()
        a = AItem()
        a['b'] = 1
        item['a'] = a
        item['b'] = 1
        self.assertEqual(pack_args(item, 'a'), ({'a': {'b': 1}},))
        self.assertEqual(pack_args(item, 'a__'), (({'a__': {'b': 1}},),))
        self.assertEqual(pack_args(item, 'b'), ({'b': 1},))
        self.assertEqual(pack_args(item, 'b__'), (({'b__': 1},),))