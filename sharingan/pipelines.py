# -*- encoding: utf-8 -*-
import types
from collections import deque

from scrapy.exceptions import DropItem

from .exceptions import DropFragment
from .item import pack_args, feed


class FragmentPipeline(object):
    def __init__(self):
        pass

    def apply_method(self, method, args_pack):
        if args_pack is None:
            ret = None
        # 如果是已经打包好的参数 传入处理方法计算出产出值
        elif isinstance(args_pack, tuple) and isinstance(args_pack[0], dict):
            try:
                ret = method(**args_pack[0])
            except DropItem:
                ret = DropItem()
            ret = (ret,)
        else:
            ret = []
            for sub_args_pack in args_pack:
                try:
                    result = self.apply_method(method, sub_args_pack)
                except DropFragment:
                    continue
                if isinstance(result[0], types.GeneratorType):
                    ret.extend(map(lambda elem: (elem,), result[0]))
                else:
                    ret.append(result)
            if isinstance(args_pack, tuple):
                ret = tuple(ret)
        return ret

    def process_in_stack(self, arg_name, pipeline_method_name_stack):
        arg_name = arg_name.split('__')
        arg_name_len = len(arg_name)
        for i in range(0, arg_name_len):
            name = '__'.join(arg_name[:arg_name_len - i])
            if name in pipeline_method_name_stack:
                return True
        return False

    def process_item(self, item, spider):
        # 简陋的获取__dict__的方法
        __dict__ = {}
        for cls in self.__class__.mro():
            if cls == FragmentPipeline:
                break
            __dict__.update(cls.__dict__)
        # 滤出pipeline field的处理定义
        # TODO rename
        pipeline_methods_dict = {attr_name: attr for attr_name, attr in __dict__.items()
                                 if not attr_name.startswith('__') and callable(attr.__class__)}
        pipeline_method_name_stack = deque(pipeline_methods_dict.keys())
        while pipeline_method_name_stack:
            method_name = pipeline_method_name_stack.popleft()
            method = pipeline_methods_dict[method_name]
            # 拿到方法的参数列表(不包括self)
            arg_names = method.func_code.co_varnames[1:method.func_code.co_argcount]
            not_ready = False
            # 如果只有一个参数 就应该直接在最后的最小粒度迭代 但是返回结果要还原成之前的结构 ?
            for arg_name in arg_names:
                # 认为预定义的Fragment Input也只是一种特殊的中间结果  难点变成了如何根据method name合并出新实体以及根据异常进行抛弃
                # 如果参数名与当前重写任务名不同且队列中存在重写任务 则推迟当前任务
                # 否则如果没有定义则报错 有定义则可以操作
                if arg_name != method_name and self.process_in_stack(arg_name, pipeline_method_name_stack):
                    not_ready = True
                    break
                elif not item.contain(arg_name):
                    raise NotImplementedError(
                        "'{}' is not configured as a fragment or an intermidiate result.".format(arg_name))
            # 如果有依赖结果还没有生成 该处理重新入队列
            if not_ready:
                pipeline_method_name_stack.append(method_name)
                continue

            # 首先提取出Fragment输入
            # 每一组args可以直接喂给Pipeline的一个处理
            # !!这里的处理原则是尽量让process方法拿到的参数都是最小粒度的
            args_pack = pack_args(item, arg_names)

            # 嵌套应用process method并返回嵌套结果
            output_pack = self.apply_method(getattr(self, method_name), args_pack)

            # 将嵌套结果根据method_name的控制来放回item
            feed(item, method_name, output_pack, arg_names[0])

        return item
