import inspect
from functools import wraps, partial


def tpck(fn=None, *, debug: bool = True):
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
