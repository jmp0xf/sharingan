# -*- encoding: utf-8 -*-
import copy
import logging

from scrapy.exceptions import DropItem
from scrapy.item import Item, Field
from scrapy.utils.misc import arg_to_iter

from .utils import flatten

logger = logging.getLogger(__name__)


def is_load_list(field):
    if field.get('load_list') is not None and not field['load_list']:
        return False
    return True


def is_jsonpath(field):
    if field.get('jsonpath'):
        return True
    return False


def is_xpath(field):
    if field.get('xpath'):
        return True
    return False


def is_css(field):
    if field.get('css'):
        return True
    return False


def is_regex(field):
    if field.get('regex'):
        return True
    return False

def is_sel(field):
    if field.get('sel'):
        return True
    return False

def copy_item(from_item, to_item=None):
    if to_item is None:
        to_item = Item()
    if hasattr(from_item, 'fields'):
        to_item.fields = from_item.fields
    for key, value in from_item.items():
        if key not in to_item:
            to_item.fields[key] = {}
        to_item[key] = value
    return to_item


# 根据query_strings拆包分组
# 这里的处理原则是尽量让process方法拿到的参数都是最小粒度的
# query_string必须是按单树层级分布的 不能有旁支zx12x
def pack_args(item, query_strings, query_parent_string='', curr_args=None):
    if not query_strings:
        return None
    if not curr_args:
        curr_args = {}
    else:
        curr_args = copy.copy(curr_args)
    query_strings = arg_to_iter(query_strings)

    if query_strings[0].endswith('__'):
        # 标记为取特殊字段* 表示全部取出
        query_strings[0] = query_strings[0] + '*'
    # 消除其他无效后缀'__'
    for index, query_string in enumerate(query_strings):
        if query_string.endswith('__'):
            query_strings[index] = query_string[:-2]
    first_query_string = query_strings[0]
    first_field_name_path = first_query_string.split('__')
    for query_string in query_strings:
        # 可在当前层取出的字段立即入包
        if '__' not in query_string:
            if query_parent_string:
                raw_query_string = query_parent_string + '__' + query_string
            else:
                raw_query_string = query_string
            # 如果是特殊字段* 则表示要整体入包 同时query_string要还原到尾部为__的形式 因为参数名不能有*
            if query_string == '*':
                raw_query_string = raw_query_string[:-1]
                curr_args.update({raw_query_string: item})
            else:
                # TODO 假如self[query_string]是个list(value) 想按value的粒度取 是怎样
                curr_args.update({raw_query_string: item[query_string]})
    # 分解query_string为query字段的访问路径
    field_name_paths = [_.split('__') for _ in query_strings if '__' in _]

    raw_sub_query_parent_string = None
    # 如果首query还没有取值 选择第一个parent query path来进入
    if field_name_paths and first_field_name_path == field_name_paths[0]:
        raw_sub_query_parent_string = first_field_name_path[0]
    # 没有share相同路径的要提取出来作为arg传进去
    new_field_name_paths = []
    for field_name_path in field_name_paths:
        if field_name_path[0] != raw_sub_query_parent_string:
            qs = '__'.join(field_name_path)
            if query_parent_string:
                raw_query_string = query_parent_string + '__' + qs
            else:
                raw_query_string = qs
            curr_args[raw_query_string] = item.extract(qs)
        else:
            new_field_name_paths.append(field_name_path)
    field_name_paths = new_field_name_paths

    ret = None
    # 如果不存在有次级访问的字段 则说明所有的信息已取出 返回
    if not field_name_paths:
        ret = curr_args
    else:
        if query_parent_string:
            sub_query_parent_string = query_parent_string + '__' + raw_sub_query_parent_string
        else:
            sub_query_parent_string = raw_sub_query_parent_string
        sub_query_strings = ['__'.join(_[1:]) for _ in field_name_paths]

        curr_field = item[field_name_paths[0][0]]
        # 如果值为list
        if isinstance(curr_field, list):
            ret = []
            sub_items = curr_field
            for sub_item in sub_items:
                # 实际上目前设想的场景sub_item为None应该不会发生
                if sub_item is None:
                    ret.append(None)
                else:
                    ret.append(pack_args(sub_item, sub_query_strings, sub_query_parent_string, curr_args))
        # 如果值为Item
        elif curr_field is not None:
            sub_item = curr_field
            ret = pack_args(sub_item, sub_query_strings, sub_query_parent_string, curr_args)

    return (ret,)


def feed(item, receive_query_path, output_pack, output_query_path):
    if isinstance(receive_query_path, basestring):
        if receive_query_path.endswith('__'):
            receive_query_path = receive_query_path + '*'
        receive_query_path = receive_query_path.split('__')
    if isinstance(output_query_path, basestring):
        if output_query_path.endswith('__'):
            output_query_path = output_query_path + '*'
        output_query_path = output_query_path.split('__')

    # len(output_query_path) 必须大于等于 len(receive_query_path)
    if len(output_query_path) < len(receive_query_path):
        raise AttributeError("The structure cannot be received by {}".format('__'.join(receive_query_path)))

    field_name = receive_query_path[0]
    if field_name not in item.fields:
        item.fields[field_name] = {}

    if output_pack is None:
        item[field_name] = None
        return

    # TODO 判断是否触底 即层次
    receive_depth = len(receive_query_path)
    output_depth = len(output_query_path)

    # 没有同名字段的话 则使用最小粒度匹配
    # 如果有同名 则在flatten到同名级别后进行匹配
    matched_index = output_depth - receive_depth
    try:
        matched_index = output_query_path.index(field_name)
    except ValueError:
        pass
    # for index, query_path in enumerate(output_query_path):
    #     if field_name == query_path:
    #         matched_index = index
    #         break

    # 利用matched_index进行深度控制的flatten
    sub_output_packs = flatten(output_pack, matched_index)
    sub_output_packs = sub_output_packs[0]  # 从tuple中取出
    sub_output_query_path = output_query_path[matched_index + 1:]

    if receive_depth > 1:
        # 判断该字段是否需要生成Item列表
        # TODO 直接按该逻辑判断进行分情况代码应该更清晰
        if isinstance(sub_output_packs, list):
            if not isinstance(item.get(field_name), list):
                item[field_name] = [Item() for _ in sub_output_packs]
            items_num = len(item[field_name])
        else:
            if item.get(field_name) is None:
                item[field_name] = Item()
            items_num = 1
        sub_output_packs_num = len(sub_output_packs)
        if items_num != sub_output_packs_num:
            logger.warning(
                "Items number {} diverges from output packs number {}.".format(items_num, sub_output_packs_num))
        drop_indexes = []
        if isinstance(item[field_name], list):
            item_pack_pair = zip(item[field_name], sub_output_packs)
        else:
            item_pack_pair = zip([item[field_name]], [sub_output_packs])
        for index, (sub_item, sub_output_pack) in enumerate(item_pack_pair):
            if isinstance(sub_output_pack[0], DropItem):
                drop_indexes.append(index)
            elif sub_item is not None:
                sub_receive_query_path = receive_query_path[1:]
                if len(sub_receive_query_path)==1 and sub_receive_query_path[0]=='*':
                    if isinstance(item[field_name], list):
                        item[field_name][index] = sub_output_pack[0]
                    else:
                        item[field_name] = sub_output_pack[0]
                else:
                    feed(sub_item, sub_receive_query_path, sub_output_pack, sub_output_query_path)
            else:
                # 如果sub item为空 则应该忽略?
                pass
        # 移除标记有DropItem异常的子Item
        if isinstance(item[field_name], list):
            for index in drop_indexes:
                del item[field_name][index]
        else:
            if 0 in drop_indexes:
                item[field_name] = None
    # 如果触底
    else:
        # # 此时sub_output_packs与sub_output_query_path也可以组合出新的Item
        # if output_depth>1 and field_name in output_query_path:
        #     sub_receive_query_path = [field_name]
        #     sub_receive_query_path.extend(sub_output_query_path)
        #     feed(item, sub_receive_query_path, sub_output_packs, sub_receive_query_path)
        # else:
        #     item[field_name] = sub_output_packs
        item[field_name] = sub_output_packs


class FragmentItem(Item):
    # Fragment的Field的命名原则是最好使用原文档中元素唯一的class名或id名 或加上HTML Tag作为后缀
    url = Field()  # Reserved Field
    # request = Field()  # Reserved Field
    created_at = Field()  # Reserved Field

    def add_field(self, fields):
        if not isinstance(fields, basestring):
            fields = arg_to_iter(fields)
        for field in fields:
            if field not in self.fields:
                self.fields[field] = {}

    def contain_url(self):
        for field_name in self.fields.keys():
            if self.fields[field_name].get('urls') or self.fields[field_name].get('url'):
                return True
        return False

    # 根据query_string返回嵌套层次的数据
    def extract(self, query_string):
        field_name_path = query_string.split('__')
        field_name = field_name_path[0]
        if len(field_name_path) > 1:
            sub_query_string = '__'.join(query_string.split('__')[1:])
            ret = None
            sub_items = self[field_name]
            if isinstance(sub_items, list):
                ret = []
                for sub_item in sub_items:
                    if sub_item is None:
                        ret.append(None)
                    else:
                        ret.append(sub_item.extract(sub_query_string))
            elif isinstance(sub_items, Item):
                ret = sub_items.extract(sub_query_string)
        else:
            ret = self[field_name]
        return ret

    # 判断query_string是否合法
    def contain(self, query_string):
        field_name_path = query_string.split('__')
        root_cls = self.__class__
        root_item = self
        for field_name in field_name_path:
            # 如果既不能满足item_cls的要求 又不能在item中找到对应的field 则判定不存在
            if not root_cls or field_name not in root_cls.fields:
                if not hasattr(root_item, 'fields') or root_item.fields.get(field_name) is None:
                    return False
            else:
                root_cls = root_cls.fields[field_name].get('item_cls')
            # 如果root_item为空且root_cls为空时 query_string严格来说是不一定合法
            if root_item:
                root_items = root_item.get(field_name)
                if isinstance(root_items, list) and root_items and isinstance(root_items[0], Item):
                    root_item = root_items[0]
                else:
                    root_item = root_items
        return True
