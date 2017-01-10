# -*- encoding: utf-8 -*-
import json

from scrapy.selector import Selector as NaiveSelector

from .utils.jsonpath import jsonpath as jsonpath_extract


class Selector(NaiveSelector):
    def __init__(self, *args, **kwargs):
        super(Selector, self).__init__(*args, **kwargs)
        self.json = None
        # 当使用xpath进行链式操作时将不存在response
        if self.response:
            try:
                self.json = json.loads(self.response.body_as_unicode())
            except ValueError:
                pass

    def jsonpath_extract(self, jsonpath):
        return jsonpath_extract(self.json, jsonpath)
