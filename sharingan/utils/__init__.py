# -*- encoding: utf-8 -*-
import collections
import json

from parsel.utils import extract_regex


def flatten(elems, max_depth=None):
    # REFACTOR 只考虑包裹括号的情况
    if max_depth < 1:
        return elems
    add_parenthesis = False
    if isinstance(elems, tuple):
        elems = elems[0]
        if not isinstance(elems, tuple):
            add_parenthesis = True
    if max_depth is not None:
        max_depth = max_depth - 1
    if isinstance(elems, list):
        ret = []
        for elem in elems:
            elem = flatten(elem, max_depth)
            if isinstance(elem, tuple):
                elem = elem[0]
            if isinstance(elem, list):
                ret.extend(elem)
            else:
                ret.append(elem)
    else:
        if isinstance(elems, tuple):
            elems = flatten(elems, max_depth)
        ret = elems
    if add_parenthesis:
        ret = (ret,)
    return ret


def filter_regex(regex, texts):
    if regex:
        if not isinstance(texts, collections.Iterable):
            texts = extract_regex(regex, texts)
        else:
            text_group = texts
            texts = []
            for text in text_group:
                if isinstance(text, dict):
                    text = json.dumps(text)
                text = unicode(text)
                text = extract_regex(regex, text)
                if text:
                    texts.extend(text)
    return texts
