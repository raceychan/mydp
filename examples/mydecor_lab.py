import inspect
from functools import wraps, partial
from typing import Union, Callable, Dict

#函数签名替换 修改
def optional_debug(func):
    if 'debug' in inspect.getargspec(func).args:
        raise TypeError('debug argument already defined')

    @wraps(func)
    def wrapper(*args, debug=False, **kwargs):
        if debug:
            print('Calling', func.__name__)
        return func(*args, **kwargs)

    sig = inspect.signature(func)
    parms = list(sig.parameters.values())
    parms.append(inspect.Parameter('debug',
                inspect.Parameter.KEYWORD_ONLY,
                default=False))
    wrapper.__signature__ = sig.replace(parameters=parms)
    return wrapper

class Register:
    @classmethod
    def bind(cls, app):
        return app


class Decorator:
    def __init__(self, func=None, *deco_args, name='race', **deco_kwargs):
        print('setp 1: __init__')
        self.register = Register
        self._locals = locals()                                   
        self._without_params = True
        if func and inspect.isfunction(func):
            self.func = func
            wraps(self.func)(self)
        else:
            self.func = None                                                    
            self.deco_args = (func,) + deco_args
            self.deco_kwargs = deco_kwargs 
            self.deco_others = {k: v for k, v in self._locals.items(
            ) if k not in ('self', 'deco_args', 'deco_kwargs')}


    def __call__(self, func=None, *func_args, **func_kwargs):
        print('step 2: __call__')
        if self.func is None:   
            self.func = func                    
            self._without_params = False
        else:                                   
            self.func_args = (func,) + func_args
            self.func_kwargs = func_kwargs
        @wraps(self.func)
        def wrapper(*func_args, **func_kwargs):
            print('step 3: wrapper')
            if self._without_params:
                print('without param')
                result = self.func(*self.func_args, **self.func_kwargs)
            else:
                print('with param')
                result = self.func(*func_args, **func_kwargs)
            return result

        if self._without_params:
            return wrapper()
        else:
            return wrapper

    def __get__(self, obj, cls):
        print('step 5: __get__')
        if obj is None:
            return self
        else:     
            print('do sth here')
            return types.MethodType(self, obj)  
    
    def __set_name__(self, owner, func_name):
        print('step 4: __set_name__')


deco = Decorator(name='race')


@deco
def test(a: int = 3):
    return a
