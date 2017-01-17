# -*- encoding: utf-8 -*-
import json

from pyquery import PyQuery as pq
from scrapy.selector import Selector as NaiveSelector

from .utils.jsonpath import jsonpath as jsonpath_extract


class Selector(NaiveSelector):
    def __init__(self, *args, **kwargs):
        super(Selector, self).__init__(*args, **kwargs)
        self.css_root = kwargs.get('css_root')
        text = None
        if getattr(self, 'text', None):
            text = self.text
        elif getattr(self, 'response'):
            text = self.response.text
        if text and not getattr(self, 'css_root', None):
            self.css_root = pq(text)
        self.json = None
        # 当使用xpath进行链式操作时将不存在response
        if self.response:
            try:
                self.json = json.loads(self.response.body_as_unicode())
            except ValueError:
                pass

    def jsonpath_extract(self, jsonpath):
        return jsonpath_extract(self.json, jsonpath)

    def css(self, query):
        # 分解query
        at_index = query.find('@')
        if at_index > -1:
            nodes = self.css_root(query[:at_index]).items()
            parentheses_index = query.find('()')
            # 如果有括号说明为方法
            if parentheses_index > -1:
                attr = query[at_index + 1:parentheses_index]
                ret = [getattr(node, attr)() for node in nodes]
            # 没括号则取属性
            else:
                attr = query[at_index + 1:]
                ret = [getattr(node, 'attr')[attr] for node in nodes]
        else:
            nodes = self.css_root(query).items()
            # 如果没有属性指示，则默认使用元素节点源码
            ret = [getattr(node, 'outerHtml')() for node in nodes]

        return ret
