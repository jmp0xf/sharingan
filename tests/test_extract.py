import unittest

from scrapy.item import Field

from sharingan.item import FragmentItem


class TestItem(FragmentItem):
    a = Field()


class AItem(FragmentItem):
    b = Field()


class BItem(FragmentItem):
    c = Field()


class CItem(FragmentItem):
    d = Field()


class TestExtract(unittest.TestCase):
    def setUp(self):
        self.item = TestItem()

    def makea(self, value=1):
        a = AItem()
        a['b'] = value
        return a

    def makeb(self, value=1):
        b = BItem()
        b['c'] = value
        return b

    def test_item_single_value(self):
        value = 1
        a = self.makea(value)
        self.item['a'] = a
        self.assertEqual(self.item.extract('a__b'), value)

    def test_list_item_single_value(self):
        value = 1
        a = self.makea(value)
        self.item['a'] = [a]
        self.assertEqual(self.item.extract('a__b'), [value])

    def test_item_list_item_single_value(self):
        v1 = 1
        v2 = 2
        b1 = self.makeb(v1)
        b2 = self.makeb(v2)
        a = self.makea([b1, b2])
        self.item['a'] = a
        self.assertEqual(self.item.extract('a__b__c'), [v1, v2])
        self.assertEqual(isinstance(self.item.extract('a__b'), list), True)
        self.assertEqual(len(self.item.extract('a__b')), 2)
        self.assertEqual(self.item.extract('a__b')[0]['c'], v1)
        self.assertEqual(self.item.extract('a__b')[1]['c'], v2)

    def test_list_item_list_item_single_value(self):
        v1 = 1
        v2 = 2
        b1 = self.makeb(v1)
        b2 = self.makeb(v2)
        a = self.makea([b1, b2])
        self.item['a'] = [a]
        self.assertEqual(self.item.extract('a__b__c'), [[v1, v2]])
