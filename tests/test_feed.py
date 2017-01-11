import unittest

from scrapy.exceptions import DropItem
from scrapy.item import Item

from sharingan.item import feed, copy_item


class TestFeed(unittest.TestCase):
    def setUp(self):
        self.output_pack = ([([([(1,), (2,)],), ([(3,)],)],), ([([(4,)],), ([(5,), (6,)],)],)],)

    def makeitem(self, attr_dict):
        item = Item()
        return copy_item(attr_dict, item)

    def test_complex_feed(self):
        item = Item()
        output_pack = self.output_pack
        feed(item, 'a__b__c__d', output_pack, 'e__f__g__h')
        self.assertEqual(isinstance(item['a'], list), True)
        self.assertEqual(len(item['a']), 2)
        i = 1
        for sub_item in item['a']:
            self.assertEqual(isinstance(sub_item, Item), True)
            self.assertEqual(isinstance(sub_item['b'], list), True)
            for sub_sub_item in sub_item['b']:
                self.assertEqual(isinstance(sub_sub_item, Item), True)
                self.assertEqual(isinstance(sub_sub_item['c'], list), True)
                for sub_sub_sub_item in sub_sub_item['c']:
                    self.assertEqual(isinstance(sub_sub_sub_item, Item), True)
                    self.assertEqual(sub_sub_sub_item['d'], i)
                    i = i + 1

        feed(item, 'b__c__d', output_pack, 'e__f__g__h')
        self.assertEqual(isinstance(item['b'], list), True)
        self.assertEqual(len(item['b']), 4)
        i = 1
        for sub_item in item['b']:
            self.assertEqual(isinstance(sub_item, Item), True)
            self.assertEqual(isinstance(sub_item['c'], list), True)
            for sub_sub_item in sub_item['c']:
                self.assertEqual(isinstance(sub_sub_item, Item), True)
                self.assertEqual(sub_sub_item['d'], i)
                i = i + 1

        feed(item, 'c__d', output_pack, 'e__f__g__h')
        self.assertEqual(isinstance(item['c'], list), True)
        self.assertEqual(len(item['c']), 6)
        for i, sub_item in enumerate(item['c']):
            self.assertEqual(isinstance(sub_item, Item), True)
            self.assertEqual(sub_item['d'], i + 1)

        feed(item, 'd', output_pack, 'e__f__g__h')
        self.assertEqual(item['d'], [1, 2, 3, 4, 5, 6])

    def test_drop_item_in_lists(self):
        item = Item()
        output_pack = self.output_pack
        feed(item, 'c__d', output_pack, 'e__f__g__h')
        self.assertEqual(isinstance(item['c'], list), True)
        self.assertEqual(len(item['c']), 6)
        for sub_item in item['c']:
            self.assertEqual(isinstance(sub_item, Item), True)
        for i, sub_item in enumerate(item['c']):
            self.assertEqual(sub_item['d'], i + 1)

        feed(item, 'c__e', ([(DropItem(),), (2,), (3,), (4,), (5,), (6,)],), 'g__t')
        self.assertEqual(len(item['c']), 5)
        for i, sub_item in enumerate(item['c']):
            self.assertEqual(sub_item['d'], i + 2)

    def test_drop_item_as_single_value(self):
        value = 1
        item = Item()
        output_pack = ((value,),)
        feed(item, 'a__b', output_pack, 'e__f')
        self.assertEqual(isinstance(item['a'], Item), value)
        self.assertEqual(item['a']['b'], value)

        feed(item, 'a__c', ((DropItem(),),), 'e__g')
        self.assertEqual(item['a'], None)

    def test_wildcard(self):
        v1 = 1
        v2 = 2
        v3 = 3
        v4 = 4
        item = Item()
        args = ([(self.makeitem({'t': v1}),), (self.makeitem({'t': v2}),)],)
        feed(item, 'a__*', args, 'a__*')
        self.assertEqual(isinstance(item['a'], list), True)
        self.assertEqual(len(item['a']), 2)
        self.assertEqual(isinstance(item['a'][0], Item) and isinstance(item['a'][1], Item), True)
        self.assertEqual(item['a'][0]['t'], v1)
        self.assertEqual(item['a'][1]['t'], v2)

        args1 = ([(v1,), (v2,), (v3,), (v4,)],)
        feed(item, 'b__*', args1, 'b__*')
        self.assertEqual(item['b'], [v1, v2, v3, v4])

        feed(item, 'c__*', ((v1,),), 'c__*')
        self.assertEqual(item['c'], v1)

    def test_omitted_wildcard(self):
        v1 = 1
        v2 = 2
        item = Item()
        args = ([(self.makeitem({'t': v1}),), (self.makeitem({'t': v2}),)],)
        feed(item, 'a__', args, 'a__')
        self.assertEqual(isinstance(item['a'], list), True)
        self.assertEqual(len(item['a']), 2)
        self.assertEqual(isinstance(item['a'][0], Item) and isinstance(item['a'][1], Item), True)
        self.assertEqual(item['a'][0]['t'], v1)
        self.assertEqual(item['a'][1]['t'], v2)

    def test_missmatched_wildcard(self):
        v1 = 1
        v2 = 2
        item = Item()
        args = ([(self.makeitem({'t': v1}),), (self.makeitem({'t': v2}),)],)
        feed(item, 'a', args, 'a__')
        self.assertEqual(isinstance(item['a'], list), True)
        self.assertEqual(len(item['a']), 2)
        self.assertEqual(isinstance(item['a'][0], tuple) and isinstance(item['a'][1], tuple), True)
        self.assertEqual(isinstance(item['a'][0][0], Item) and isinstance(item['a'][1][0], Item), True)
        self.assertEqual(item['a'][0][0]['t'], v1)
        self.assertEqual(item['a'][1][0]['t'], v2)

        feed(item, 'b__c', args, 'a__')
        self.assertEqual(isinstance(item['b'], list), True)
        self.assertEqual(len(item['b']), 2)
        self.assertEqual(isinstance(item['b'][0], Item) and isinstance(item['b'][1], Item), True)
        self.assertEqual(isinstance(item['b'][0]['c'], Item) and isinstance(item['b'][1]['c'], Item), True)
        self.assertEqual(item['b'][0]['c']['t'], v1)
        self.assertEqual(item['b'][1]['c']['t'], v2)
