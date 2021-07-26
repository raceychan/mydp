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
        self.Register = Register
        self._locals = locals()
        self._without_params = True
        self._tasks = {}

        # func passed to __init__ no param in deco
        if func and inspect.isfunction(func):
            self.func = func
            wraps(self.func)(self)
        else:                                                       # func passed to __call__ with param in deco
            self.deco_args = (self._locals['func'],) + \
                self._locals['deco_args']
            self.deco_kwargs = self._locals['deco_kwargs']
            self.deco_others = {k: v for k, v in self._locals.items(
            ) if k not in ('self', 'deco_args', 'deco_kwargs')}

    def __call__(self, func=None, *func_args, **func_kwargs):
        # with param in deco, first args is the func
        if func and inspect.isfunction(func):
            # self.func = func                        # Todo: using type to create a class of func\

            self._without_params = False
        else:                                       # without param in deco, all args are func_args
            self.func_args = (func,) + func_args
            self.func_kwargs = func_kwargs

        @wraps(self.func)
        def wrapper(*func_args, **func_kwargs):
            if self._without_params:
                result = self.func(*self.func_args, **self.func_kwargs)
            else:
                result = self.func(*func_args, **func_kwargs)
            return result

        if self._without_params:
            return wrapper()
        else:
            return wrapper

    def Task(self, func=None, **func_kwargs):
        base = self.Register
        run = func
        task = type(func.__name__, (base,), dict({'app': self,
                                                  'name': func.__name__,
                                                  'run': run,
                                                  '__annotations__': func.__annotations__,
                                                  '__doc__': func.__doc__,
                                                  '__wrapped__': run
                                                  }, **func_kwargs))()
        task.bind(self)
        task.__qualname__ = func.__qualname__  # both func and task are classes here
        self._tasks[task.name] = task
        self.func = task


deco = Decorator(name='race')


@deco
def test(a: int = 3):
    return a
