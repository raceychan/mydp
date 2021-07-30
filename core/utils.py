import pstats
import threading
import cProfile
import inspect
import types
import sqlalchemy

from time import time
from datetime import datetime
from typing import Callable, Optional, Dict, Any, Set, Union
from pandas.core.frame import DataFrame
from functools import wraps, partial


def tpck(fn: Callable = None, *, debug: bool = True) -> Callable:
    if not fn:
        return partial(tpck, debug=debug)

    if not debug:
        return fn

    @wraps(fn)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(fn)
        params = sig.parameters
        values = list(params.values())

        for index, arg in enumerate(args):
            param = values[index]
            if param.annotation is not param.empty and not isinstance(arg, param.annotation):
                raise TypeError(
                    f'Argument {param.name} must be {values[index].annotation}')

        for k, v in kwargs.items():
            if params[k].annotation is not inspect._empty and not isinstance(v, params[k].annotation):
                raise TypeError(
                    f'Argument {k} must be  {params[k].annotation}')
        return fn(*args, **kwargs)
    return wrapper


def set_column_types(df: DataFrame) -> dict:
    if not df:
        print("Input is empty")

    dtypedict = {}
    for column, dtype in zip(df.columns, df.dtypes):
        if "object" in str(dtype):
            dtypedict.update(
                {column: sqlalchemy.types.NVARCHAR(length=255)})

        if "datetime" in str(dtype):
            dtypedict.update({column: sqlalchemy.types.Date()})

        if "float" in str(dtype):
            dtypedict.update(
                {column: sqlalchemy.types.Float(precision=3, asdecimal=True)})

        if "int" in str(dtype):
            dtypedict.update({column: sqlalchemy.types.INT()})
    return dtypedict


def timeit(func: Callable) -> Callable:
    @wraps(func)
    def _time_it(*args, **kwargs):
        start = int(round(time() * 1000))
        try:
            return func(*args, **kwargs)
        finally:
            end_ = int(round(time() * 1000)) - start
            print(f"Total execution time: {end_ if end_ > 0 else 0} ms")
    return _time_it


def cache(*args, **kwargs):
    func = None
    if len(args) == 1 and __builtins__.callable(args[0]):
        func = args[0]
    if func:
        seconds = 60  # default values
    if not func:
        seconds = kwargs.get('seconds')

    def callable(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            cache_key = [func, args, kwargs]
            result = _cache.get(cache_key)
            if result:
                return result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, timeout=seconds)
            return result
        return wrapped

    return callable(func) if func else callable


def build_url(db_params, db_params_schema: Dict[str, Any]) -> str:
    v: Dict[str, str] = {param: db_params.get(key) for key in db_params.keys()
                         for param in db_params_schema
                         if (param in key or param.upper() in key)}
    if v.get('driver'):
        url = v.get('db', '') + '+' + v.get('driver', '') + '://'
    else:
        url = v.get('db', '') + '://'
    url += v.get('user', '')
    url += ':' if v.get('password') else ''
    url += '@' if v.get('user') or v.get('password') else ''
    url += v.get('host', '')
    url += ':' + v.get('port', '') if v.get('port') else ''
    url += v.get('path', '')
    url += '?' + v.get('query', '') if v.get('query') else ''
    url += '#' + v.get('fragment', '') if v.get('fragment') else ''
    return url


class _Profiler:
    def __init__(self, func, show_stats: bool = False, filename: str = None):
        wraps(func)(self)
        self.stats = None
        self.show_stats = show_stats
        self.filename = filename or func.__name__

    def __call__(self, *args, **kwargs):
        with cProfile.Profile() as pr:
            self.__wrapped__(*args, **kwargs)
        self.stats = pstats.Stats(pr)
        self.stats.sort_stats(pstats.SortKey.TIME)

        if self.show_stats:
            self.stats.print_stats()

        if self.filename:
            if 'prof' not in self.filename:
                self.filename = self.filename.split('.')[0] + '.prof'
            self.stats.dump_stats(filename=self.filename)

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return types.MethodType(self, instance)


def profiler(func: Optional[Callable] = None, *args, **kwargs):
    if func:
        return _Profiler(func)
    else:
        @wraps(func)
        def wrapper(func):
            return _Profiler(func, *args, **kwargs)
        return wrapper


def singleton(cls):
    _instance = {}
    singleton.__lock = threading.Lock()

    @wraps(cls)
    def _singleton(*args, **kwargs):
        with singleton.__lock:
            if cls not in _instance:
                _instance[cls] = cls(*args, **kwargs)
            return _instance[cls]

    return _singleton()


def flyweight(cls):
    ''' Note: this won't work for classes with default argument values
    '''
    _instance = {}

    def _make_arguments_to_key(*args, **kwargs):
        key = args
        if kwargs:
            for item in sorted(kwargs.items()):
                key += item
        return key

    @wraps(cls)
    def _flyweight(*args, **kwargs):
        cache_key = f'{cls}_{_make_arguments_to_key(*args, **kwargs)}'
        if cache_key not in _instance:
            _instance[cache_key] = cls(*args, **kwargs)
        return _instance[cache_key]

    return _flyweight

class Clock:
    def __init__(self,func):
        self._locals = locals()
        self._without_params = True
        self.time = self.click()

        if func and inspect.isfunction(func):
            self.func = func
            wraps(self.func)

        self._time = datetime.now()
        self._snap_time = self.click()

    def __get__(self):
        pass

    def __set__(self):
        pass

    def click(self):
        self._snap_time = datetime.now()
