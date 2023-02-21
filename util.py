# -*- coding: utf-8 -*-
"""Some helper functions
"""
import hashlib
import hmac
from datetime import datetime
import json
import math
import re
import uuid
import functools
import yaml
from decimal import Decimal
from collections import defaultdict



LSKU_REGEX = re.compile(r'\w+\-[vbs]\-[A-Z]{3}\-\d+')

class AppServerJsonEncoder(json.JSONEncoder):
    """Custom json encoder to support more data type
    """

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    def default(self, o):
        """
        """
        if isinstance(o, datetime.datetime):
            return int(o.timestamp())

        if isinstance(o, bytes):
            return o.decode('utf8')

        if isinstance(o, uuid.UUID):
            return str(o)

        ''' 
        if isinstance(o, BaseGeometry):
            return shapely.geometry.mapping(o)

        if isinstance(o, DateTimeRange):
            return [o.lower, o.upper]
        '''

        if isinstance(o, Decimal):
            float_value = float(o)
            return float_value if not float_value.is_integer() else int(float_value)

        '''
        if isinstance(o, Base):
            return o.as_dict()
        '''

        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)

        return super(self.__class__, self).default(o)


class AttrDict(dict):

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

def read_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return list(yaml.safe_load_all(f))

def to_lower_dict(dict_obj):
    """Convert All dict keys to lowercase
    :param dict_obj: dict object
    :return: dict object with all keys convert to lowercase
    """
    if all(map(lambda x: x.islower(), dict_obj.keys())):
        return dict_obj
    else:
        return {k.lower(): v for k, v in dict_obj.items()}

def combine_dict(*kwargs):
    # combine user_permissions and role_permission
    # https://gist.github.com/hrldcpr/2012250
    def tree():
        return defaultdict(tree)

    def dicts(t):
        try:
            return dict((k, dicts(t[k])) for k in t)
        except:
            return t

    def add(t, path, value):
        for i, node in enumerate(path):
            if i == len(path) - 1:
                try:
                    current = t[node]
                    if isinstance(current, list):
                        t[node] = list(set(current + value))
                    else:
                        # {'b': {}} {'b': {"c": {"d": 1}}}
                        t[node] = t[node] or value or tree()
                except KeyError:
                    # {"a":{}} {"a":{"b":{}}}
                    t[node] = value or tree()

            t = t[node]

    t = tree()

    def walk_dict(a_dict, path=()):
        for k in a_dict:
            if a_dict[k] == {} or (not isinstance(a_dict[k], dict)):
                add(t, path + (k,), a_dict[k])
            else:
                walk_dict(a_dict[k], path + (k,))

    for i in kwargs:
        walk_dict(i or {})

    return dicts(t)

def json_value_from_dic(res, path):
    if not isinstance(path, list):
        raise TypeError('path should be list type, check type!!')

    if not isinstance(res, dict) and not isinstance(res, list):
        raise TypeError('response should be list or dict type, check type!!')

    for val in path:
        if val == 'root':
            return res
        else:
            # print('current val: {}, current res: {}'.format(val, res))
            if isinstance(res, dict):
                res = res.get(val)
                continue
            elif isinstance(res, list):
                res = res[0].get(val)
                continue
    return res


def get_common_header(method, url, token, secrets):
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json, text/plain, */*',
              'Authorization': None,
              'LG-Timestamp': None,
              'LG-Content-Sig': None
              }
    current_time = str(int(datetime.now().timestamp()))

    payload = '{} {} {}'.format(method, url, current_time)
    signature = hmac.new(bytes(secrets,encoding='utf8'), payload.encode('ascii'), digestmod=hashlib.sha256).hexdigest()

    header["Authorization"] = "Bearer " + token
    header["LG-Timestamp"] = current_time
    header["LG-Content-Sig"] = signature
    header["X-disable-encrypt"] = 'true'
    return header


def decrype(response):
    response = response.content
    response = bytes([255 - x for x in response[::-1]])
    return response.decode()

if __name__ == '__main__':
    res = {'hits': [{'a': [{'c': 1}], 'b': 2}]}
    path = ['hits','a','c']
    path = ['hits', 'b']
    path = ['root']
    print (json_value_from_dic(res, path))
    print('OK')

def loads_json(path):
    lines = []     #  第一步：定义一个列表， 打21开文件
    with open(path) as f:
        for row in f.readlines(): # 第二步：读取文件内容
            if row.strip().startswith("//"):   # 第三步：对每一行进行过滤
                continue
            lines.append(row)                   # 第四步：将过滤后的行添加到列表中.
    return json.loads("\n".join(lines))       #将列表中的每个字符串用某一个符号拼接为一整个字符串，用json.loads()函数加载，这样就大功告成啦！！

def load_json(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return data

def get_operator(operation_dict):
    return operation_dict['op']


def validate_last_modified_time(modified_time_header, ssd_modified_time):
    if modified_time_header:
        return int(modified_time_header) >= int(ssd_modified_time.timestamp())
    else:
        return False


def sorted_by_section_floor(iterable, floor_number=None, section_name=None):
    if not floor_number:
        floor_number = lambda x: getattr(x, 'floor_number')
    if not section_name:
        section_name = lambda x: getattr(x, 'section_name', '') if getattr(x, 'section_name') else ''

    key_func = lambda x: (section_name(x), float(floor_number(x).replace('B', '-').replace('L', '')))

    return sorted(iterable, key=key_func)


def snapshot_to_timestamp(snapshot):
    return datetime.datetime.strptime(snapshot, '%Y%m%d').timestamp()


def first_in_list(object_list, cmp=None):
    if cmp:
        for obj in object_list:
            if cmp(obj):
                return obj
        return None
    else:
        return None


def hash_any(obj):
    if isinstance(obj, list):
        s = ''.join(sorted([hash_any(x) for x in obj]))
    elif isinstance(obj, dict):
        s = ''.join(["'{}':'{}';".format(key, hash_any(val)) for (key, val) in sorted(obj.items()) if val is not None])
    else:
        s = str(obj)

    return hashlib.md5(s.encode('utf8')).hexdigest()


def pipe(funcs, init=None, init_exists=False):
    """ Pipline functions

    Pass the result from prev function to next function, and return the result of last function

    :param funcs: functions, all function should any accept one parameter
    :param init: parameter of first function
    :param init_exists: if the first function parameter is false value in python, then init_exists should be set to true
    """
    init_exists = True if init else init_exists

    if init_exists:
        head = lambda: init
        tail = funcs
    else:
        head, *tail = funcs

    return functools.reduce(lambda x, f: f(x), tail, head())


class Pipe:

    def __init__(self, function):
        self.function = function
        functools.update_wrapper(self, function)

    def __rshift__(self, other):
        if isinstance(other, Pipe):
            return Pipe(lambda x: self.function(x) >> other)
        else:
            raise Exception('Can not pipe to a non-pipable object')

    def __rrshift__(self, other):
        if isinstance(other, Pipe):
            return Pipe(lambda x: self.function(x >> other))
        else:
            return self.function(other)

    def curry(self, *args, **kwargs):
        return Pipe(lambda x: self.function(x, *args, **kwargs))

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)


@Pipe
def wrap_into_list(parameter):
    """Wrap the parameter into a list if the parameter is not a list"""
    return parameter if isinstance(parameter, list) else parameter


def stream_to_generator(stream, buffer_size=1024):
    chunk = stream.read(buffer_size)
    while chunk:
        yield chunk
        chunk = stream.read(buffer_size)

