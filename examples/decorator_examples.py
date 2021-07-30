import inspect
import types
from functools import wraps, partial
# nomral decorator
# Utility decorator to attach a function as an attribute of obj


def attach_wrapper(obj, func=None):
    if func is None:
        return partial(attach_wrapper, obj)
    setattr(obj, func.__name__, func)
    return func


def dec(func):
    ''' basic dec, without params in deco
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        print('decorated')
        return func(*args, **kwargs)
    return wrapper


def dec_arg(*args, name='race', **kwargs):
    ''' dec with params
    '''
    def dec(func):
        _name = name if name else func.__module__

        @wraps(func)
        def wrapper(*args, **kwargs):
            print(_name, 'decorated')
            return func(*args, **kwargs)
        return wrapper
    return dec


def dec_opt_arg(func=None, *, name=None, **kwargs):
    ''' dec with Optional params
    '''
    if func is None:
        _locals = locals()
        return partial(dec_opt_arg, _locals)

    @wraps(func)
    def wrapper(*args, **kwargs):
        print('decorated')
        return func(*args, **kwargs)
    return wrapper


# for the purpose of validating first args
# from pydantic import parse_obj_as
# from typing import Dict, Union, Type, Callable
# parse_obj_as(Union[Type,Callable], test)


class Decorator:
    # class deco with optional params
    def __init__(self, func=None, *deco_args, name='race', **deco_kwargs):
        ''' with params: params in __init__,
                         func in __call__, 
            without params: func in __init__,

            Bug: with deco params, decorated func is still a func
            without params, func is a instance of Decorator class
            a = Decorator(func)              # without params:
            a: <__main__.Decorator at 0x25b77a5e910>
            b = Decorator(name='race')(func) # with params
            b: <function __main__.func(a=3)>
        '''
        self._locals = locals()                                     # func passed to __init__ without param in deco
        self._without_params = True

        if func and inspect.isfunction(func):
            self.func = func
            wraps(self.func)(self)
        else:
            # func passed to __call__ with param in deco
            self.func = None
            self.deco_args = (func,) + deco_args
            self.deco_kwargs = deco_kwargs
            self.name = self._locals.get('name')
#            self.deco_others = {k: v for k, v in self._locals.items(
#            ) if k not in ('self', 'deco_args', 'deco_kwargs')}

    def __call__(self, func=None, *func_args, **func_kwargs):
        ''' with params, deco __call__ called when func created
            without params, deco __call__ called when func called
        '''
        if self.func is None:   # with param in deco, first args is the func
            self.func = func                     # Todo: using type to create a class of func
            self._without_params = False
        else:                                    # without param in deco, all args are func_args
            self.func_args = (func,) + func_args
            self.func_kwargs = func_kwargs

        @wraps(self.func)
        def wrapper(*func_args, **func_kwargs):
            if self._without_params:
                print('decorated_without_params')
                result = self.func(*self.func_args, **self.func_kwargs)
            else:
                print('decorated_with_params')
                result = self.func(*func_args, **func_kwargs)
            return result

        if self._without_params:
            return wrapper()
        else:
            return wrapper

# works with methods inside class
# bug: does not work with func without params
class Decorator:
    def __init__(self, func=None, *deco_args, name='race', **deco_kwargs):
        self._locals = locals()
        self._without_params = True

        if func and inspect.isfunction(func):
            self.func = func
            wraps(self.func)(self)
        else:
            self.func = None
            self.deco_args = (func,) + deco_args
            self.deco_kwargs = deco_kwargs
            self.name = self._locals.get('name')

    def __call__(self, func_or_cls=None, *func_args, **func_kwargs):
        if self.func is None:
            self.func = func_or_cls
            self._without_params = False

        self.func_args = (func_or_cls,) + func_args
        self.func_kwargs = func_kwargs

        @wraps(self.func)
        def wrapper(*wrap_func_args, **wrap_func_kwargs):
            self.func_args = wrap_func_args or self.func_args
            func_result = self.func(*self.func_args, **wrap_func_kwargs) 
            return func_result 

        if self._without_params: # func = Decorator(func); func() = Decorator.__call__ = wrapper
            return wrapper()     # func()() = wrapper() = result
        else:                    # func = Decorator()(func) = Decorator.__call__(func) = wrapper
            return wrapper       # func() = wrapper() = result

    def __get__(self, obj, cls):
        if obj is None:          # instance method does not take call from class
            return self
        else:
            return types.MethodType(self, obj)


class class_decorator:
    # __set_name__ is called whenever the class owner is created
    def __init__(self, func):
        self.func = func
        print(self.func)

    def __set_name__(self, owner, func_name):
        # do something with owner, i.e.
        print(f"decorating {self.func} and using {owner}")

        self.func.class_name = owner.__name__
        # then replace ourself with the original method
        setattr(owner, func_name, self.func)
        setattr(owner, 'race', 'test')


# class A:
#     @class_decorator
#     def hello(self, x=42):
#         return x

#     def world(self):
#         return 'world'


