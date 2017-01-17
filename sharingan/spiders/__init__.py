# -*- encoding: utf-8 -*-
from abc import ABCMeta
from collections import deque

import lxml.html
import six
from scrapy.http import Request, FormRequest
from scrapy.item import Item
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.spiders import Spider

from ..item import is_load_list, copy_item
from ..loader import FragmentItemLoader
from ..selector import Selector


# Scrapy会读取Spider的类变量作为设置 所以是用元类修改设置
class FragmentSpiderMeta(ABCMeta):
    def __new__(mcs, class_name, bases, attrs):
        # customise pipeline per spider
        fragment_pipeline = attrs.get('fragment_pipeline')
        if fragment_pipeline:
            custom_settings = attrs.get('custom_settings', {})
            item_pipelines = custom_settings.get('ITEM_PIPELINES', {})
            item_pipelines[fragment_pipeline] = 1000
            custom_settings['ITEM_PIPELINES'] = item_pipelines
            attrs['custom_settings'] = custom_settings
        return super(ABCMeta, mcs).__new__(mcs, class_name, bases, attrs)


@six.add_metaclass(FragmentSpiderMeta)
class FragmentSpider(Spider):
    fragment_pipeline = None
    start_url = None
    start_item = None
    cookies = None # dict
    get_cookies = None # 自定义无参数方法
    login_url = None # 字符串
    login_form = None # dict

    def __init__(self, *args, **kwargs):
        super(FragmentSpider, self).__init__(*args, **kwargs)

        if not self.start_urls:
            if self.start_url:
                self.start_urls = [self.start_url]
            # 如果起始Item只是用来自启动 本身不对应有意义的文档 则使用dummy request来满足Scrapy的要求
            elif self.start_item.contain_url():
                self.start_urls = ['https://www.baidu.com/?dummy_request']

    def login(self):
        if self.login_url:
            return FormRequest(self.login_url,
                                   formdata=self.login_form,
                                   callback=self.start_url_requests)
        return None

    def get_cookies(self):
        return None

    def start_requests(self):
        login_request = self.login()
        if login_request:
            yield login_request
        else:
            for url_request in self.start_url_requests():
                yield url_request

    def start_url_requests(self, response=None):
        # 先尝试调用获取cookie的方法
        if not self.cookies:
            self.cookies = self.get_cookies()
        for url in self.start_urls:
            yield self.make_requests_from_url(url, self.cookies)

    def make_requests_from_url(self, url, cookies=None):
        return Request(url, dont_filter=True, cookies=cookies)

    def parse(self, response):
        # 实际上应该找这个url对应的start_item
        initial = False
        item_cls = response.meta.get('item_cls')
        if not item_cls:
            # 实际上应该找这个url对应的start_item
            initial = True
            item_cls = self.start_item

        loader = FragmentItemLoader(item=item_cls(), response=response)
        item = loader.load_item()

        request_stack = response.meta.get('request_stack', deque())
        # 之所以不使用成员变量来存储root_item是因为不排除多个起始urls被parse 这样必须每个parse一个root_item
        root_item = response.meta.get('root_item', item if initial else None)

        self.sub_parse_or_follow(item, request_stack, response, root_item)

        container = response.meta.get('container')
        if isinstance(container, list):
            index = response.meta.get('index')
            # 保证SubItem的顺序
            # WARNING 可能不一定是线程安全的
            container[index] = item
        elif isinstance(container, Item):
            copy_item(from_item=item, to_item=container)

        # 如果没有Follow URL 则返回Item
        # 深度优先策略
        # 注意这个地方必须保证完全是独立的逻辑 不能假设push和pop的顺序
        try:
            request = request_stack.pop()
        except IndexError:
            # TODO 进行由上至下路径子item粒度的拆分
            yield root_item
        else:
            yield request

    def errback(self, failure):
        if failure.check(HttpError):
            # TODO 记录
            re = failure.value.response
        else:
            # TODO 记录
            re = failure.request
        root_item = re.meta.get('root_item')
        request_stack = re.meta.get('request_stack', deque())
        try:
            request = request_stack.pop()
        except IndexError:
            # TODO 进行由上至下路径子item粒度的拆分
            yield root_item
        else:
            yield request

    # 当前文档进行子文档parse或者进行url的跟进
    def sub_parse_or_follow(self, item, request_stack, response, root_item, selector=None):
        if selector == None:
            selector = Selector(response=response)
        for field_name, field in item.fields.items():
            item_cls = field.get('item_cls')
            load_list = is_load_list(field)
            # 如果是子FragmentItem
            if item_cls:
                # 强制认为字段的值都是个list
                # 目前从fragments过来的都是list 注意这里以后可能会有变
                # 使用list的第一个元素作为下一步处理的依据
                fragments = item[field_name]
                if not isinstance(fragments, list):
                    fragments = [fragments]
                first_fragment = fragments[0]
                # MARK 注意其实这样判断该field为空语义是有问题的
                if first_fragment is None:
                    item[field_name] = None
                    continue
                    # raise TypeError("unexpected empty content for field '{}' in {}".format(field_name, item_cls))

                # Naive的判断提取了子文档还是跟进链接
                # 如果是合法的html文档字串 则提取子文档建立子FragmentItem
                # TODO 如果是子Json等其他文档类型
                if lxml.html.fromstring(first_fragment).find('.//*') is not None:
                    sub_items = []
                    sub_sel = item.fields[field_name].get('xpath')
                    if sub_sel:
                        sub_selectors = selector.xpath(FragmentItemLoader.force_rel_xpath(sub_sel))
                    else:
                        sub_sel = item.fields[field_name].get('css')
                        # 不支持多余的css_root初始化参数
                        # sub_selectors = [Selector(response=response, css_root=sub_selector_html) for sub_selector_html in selector.css(sub_sel)]
                        # 使用dummy selectors让loader自动生成selector 但注意此时生成的selector使用的xpath选择器将带又多余的html标签(css选择器不受影响)
                        sub_selectors = [None] * len(selector.css(sub_sel))
                    for index, fragment in enumerate(fragments):
                        sub_response = response.replace(body=fragment)
                        sub_selector = sub_selectors[index]
                        # 之所以使用这个模式是因为子文档直接塞给loader Scrapy会默认让子文档HTML规范化(增加<html>和<body>标签)
                        l = FragmentItemLoader(item=item_cls(), response=sub_response, selector=sub_selector)
                        sub_item = l.load_item(relative=True)
                        self.sub_parse_or_follow(sub_item, request_stack, sub_response, root_item, sub_selector)
                        sub_items.append(sub_item)
                    if load_list:
                        item[field_name] = sub_items
                    else:
                        item[field_name] = sub_items[0]
                # 否则则认为是链接 进行跟进
                else:
                    # TODO 外部链接和内部链接的判断
                    urls = map(lambda url: response.urljoin(url), fragments)
                    # WARNING 不一定是线程安全的 可以用嵌套list避免对同一list进行操作
                    # container的做法对分布式不友好 需要有方式来做到只要材料齐全 能生产一个是一个
                    if load_list:
                        container = [None] * len(urls)
                    else:
                        container = item_cls()
                    item[field_name] = container

                    # 其实现在似乎单个压栈也没啥区别
                    for index, url in enumerate(urls):
                        meta = {
                            'item_cls': item_cls,
                            'root_item': root_item,
                            'container': container,
                            'index': index,
                            'request_stack': request_stack,
                        }
                        r = Request(url=url, meta=meta, callback=self.parse, dont_filter=True, errback=self.errback)
                        request_stack.append(r)
        return request_stack
