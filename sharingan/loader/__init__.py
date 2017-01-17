# -*- encoding: utf-8 -*-

from scrapy.loader import ItemLoader
from scrapy.utils.misc import arg_to_iter
from scrapy.utils.python import flatten

from ..item import is_load_list, is_css, is_xpath, is_jsonpath, is_regex, is_sel
from ..selector import Selector
from ..utils import filter_regex
from ..utils.jsonpath import jsonpath as jsonpath_extract


class FragmentItemLoader(ItemLoader):
    default_selector_class = Selector

    def _get_xpathvalues(self, xpaths, **kw):
        self._check_selector_method()
        xpaths = arg_to_iter(xpaths)
        ret = self._extract_hier_xpaths(self.selector, xpaths, **kw)
        if not flatten(ret):
            return None
        else:
            return ret

    def _extract_hier_xpaths(self, node, xpaths, **kw):
        xpaths = arg_to_iter(xpaths)
        # 如果是分层xpath 非首xpath需要重写为相对xpath
        if len(xpaths) > 1:
            child_xpaths = xpaths[1:]
            # handle relative xpaths
            # ref: https://doc.scrapy.org/en/master/topics/selectors.html#working-with-relative-xpaths
            for index, xpath in enumerate(child_xpaths):
                child_xpaths[index] = self.__class__.force_rel_xpath(xpath)
            return [self._extract_hier_xpaths(child_node, child_xpaths, **kw) for child_node in node.xpath(xpaths[0])]
        else:
            return filter_regex(kw.get('regex'), node.xpath(xpaths[0]).extract())

    def _extract_hier_csss(self, node, csss, **kw):
        csss = arg_to_iter(csss)
        if len(csss) > 1:
            child_csss = csss[1:]
            return [self._extract_hier_csss(Selector(text=child_node_html), child_csss, **kw) for child_node_html in
                    node.css(csss[0])]
        else:
            return filter_regex(kw.get('regex'), node.css(csss[0]))

    # TODO 由于scrapy自带的css与xpath等价 没有实操价值 改为PySpider的Pyquery比较有意义
    def _get_cssvalues(self, csss, **kw):
        self._check_selector_method()
        csss = arg_to_iter(csss)
        ret = self._extract_hier_csss(self.selector, csss, **kw)
        # ret = filter_regex(kw.get('regex'), (self.selector.css(csss)))
        if not flatten(ret):
            return None
        else:
            return ret

    def _extract_hier_jsonpaths(self, json_dict, jsonpaths, **kw):
        jsonpaths = arg_to_iter(jsonpaths)
        # 如果是分层jsonpath 非首jsonpath需要重写为相对jsonpath
        if len(jsonpaths) > 1:
            child_jsonpaths = jsonpaths[1:]
            # handle relative jsonpaths
            # ref: https://doc.scrapy.org/en/master/topics/selectors.html#working-with-relative-xpaths
            for index, jsonpath in enumerate(child_jsonpaths):
                child_jsonpaths[index] = self.__class__.force_rel_xpath(jsonpath)
            return [self._extract_hier_jsonpaths(child_node, child_jsonpaths, **kw) for child_node in
                    jsonpath_extract(json_dict, jsonpaths[0])]
        else:
            # TODO self.selector.jsonpath(jsonpath).extract()
            return filter_regex(kw.get('regex'), jsonpath_extract(json_dict, jsonpaths[0]))

    def _get_jsonpathvalues(self, jsonpaths, **kw):
        self._check_selector_method()
        jsonpaths = arg_to_iter(jsonpaths)
        ret = self._extract_hier_jsonpaths(self.selector.json, jsonpaths, **kw)
        if not flatten(ret):
            return None
        else:
            return ret

    def add_jsonpath(self, field_name, jsonpath, *processors, **kw):
        values = self._get_jsonpathvalues(jsonpath, **kw)
        self.add_value(field_name, values, *processors, **kw)

    def _get_revalues(self, regexes, **kw):
        self._check_selector_method()
        regexes = arg_to_iter(regexes)
        return flatten(self.selector.re(regex) for regex in regexes)

    def add_regex(self, field_name, regex, *processors, **kw):
        values = self._get_revalues(regex, **kw)
        self.add_value(field_name, values, *processors, **kw)

    # 强制将子文档的绝对xpath转换为根文档的相对xpath
    @classmethod
    def force_rel_xpath(cls, xpath):
        # 可能还是比较Naive
        # 这个方式从理论上来说还是有缺陷 不等价于xpath选择后重构Selector后用xpath的行为
        xpaths = xpath.split('|')
        for index, xpath in enumerate(xpaths):
            if xpath.startswith('/'):
                xpaths[index] = '.' + xpath
        return '|'.join(xpaths)

    def load_item(self, relative=False):
        item = self.item
        for field_name in item.fields.keys():
            # TODO 重构
            regex = item.fields[field_name].get('regex')
            if is_xpath(item.fields[field_name]):
                xpaths = item.fields[field_name]['xpath']
                # 如果传进来的是相对路径的Selector 要强制更改xpath为相对寻径
                if relative:
                    xpaths = arg_to_iter(xpaths)
                    xpaths[0] = self.__class__.force_rel_xpath(xpaths[0])
                self.add_xpath(field_name, xpaths, regex=regex)
            elif is_css(item.fields[field_name]):
                css = item.fields[field_name]['css']
                self.add_css(field_name, css, regex=regex)
            elif is_jsonpath(item.fields[field_name]):
                jsonpath = item.fields[field_name]['jsonpath']
                self.add_jsonpath(field_name, jsonpath, regex=regex)
            elif is_sel(item.fields[field_name]):
                sel = item.fields[field_name]['sel']
                doc = getattr(self.context['response'], 'body')
                if isinstance(sel, basestring):
                    item[field_name] = getattr(item, sel)(doc)
                else:
                    item[field_name] = sel(doc)
            elif is_regex(item.fields[field_name]):
                self.add_regex(field_name, regex)
            elif item.fields[field_name].get('urls'):
                item[field_name] = arg_to_iter(item.fields[field_name]['urls'])
            elif item.fields[field_name].get('url'):
                item[field_name] = arg_to_iter(item.fields[field_name]['url'])
            else:
                # TODO
                pass
        item = super(FragmentItemLoader, self).load_item()

        for field_name in item.fields.keys():
            # 如果标记为load_list为false 则在能取单值的情况下取单值
            if not is_load_list(item.fields[field_name]):
                if isinstance(item.get(field_name), list):
                    # 由于目前允许分层xpath  所以取首值在嵌套列表中还需要handle 或者禁用分层xpath
                    if len(item[field_name]) > 1:
                        # TODO 如果原候选值个数大于1 则需要作出警告
                        pass
                    item[field_name] = item[field_name][0]
        # item['url'] = self.context['response'].url
        # try:
        #     item['created_at'] = datetime.datetime.strptime(self.context['response'].headers['Date'],
        #                                                     '%a, %d %b %Y %H:%M:%S GMsT')
        # except (ValueError, KeyError):
        #     item['created_at'] = time.time()
        # 需要有方式进行控制
        # request = {_:getattr(self.context['response'].request, _) for _ in ['url', 'method', 'headers']}
        # for ignored_field_name in ['Accept', 'Accept-Encoding', 'Accept-Language', 'Cookie']:
        #     request['headers'].pop(ignored_field_name, None)
        # item['request'] = request
        return item
