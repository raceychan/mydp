import inspect
import sys
from collections import UserList
from functools import partial
from itertools import islice, tee, zip_longest

FUNHEAD_TEMPLATE = """
def {fun_name}({fun_args}):
    return {fun_value}
"""


def _argsfromspec(spec, replace_defaults=True):
    if spec.defaults:
        split = len(spec.defaults)
        defaults = (list(range(len(spec.defaults))) if replace_defaults
                    else spec.defaults)
        positional = spec.args[:-split]
        optional = list(zip(spec.args[-split:], defaults))
    else:
        positional, optional = spec.args, []

    varargs = spec.varargs
    varkw = spec.varkw
    if spec.kwonlydefaults:
        kwonlyargs = set(spec.kwonlyargs) - set(spec.kwonlydefaults.keys())
        if replace_defaults:
            kwonlyargs_optional = [
                (kw, i) for i, kw in enumerate(spec.kwonlydefaults.keys())
            ]
        else:
            kwonlyargs_optional = list(spec.kwonlydefaults.items())
    else:
        kwonlyargs, kwonlyargs_optional = spec.kwonlyargs, []

    return ', '.join(filter(None, [
        ', '.join(positional),
        ', '.join(f'{k}={v}' for k, v in optional),
        f'*{varargs}' if varargs else None,
        '*' if (kwonlyargs or kwonlyargs_optional) and not varargs else None,
        ', '.join(kwonlyargs) if kwonlyargs else None,
        ', '.join(f'{k}="{v}"' for k, v in kwonlyargs_optional),
        f'**{varkw}' if varkw else None,
    ]))


def head_from_fun(fun, bound=False, debug=False):
    """Generate signature function from actual function."""
    # we use exec to create a new function
    # with an empty body, meaning it has the same performance as
    # as just calling a function.
    is_function = inspect.isfunction(fun)
    is_callable = hasattr(fun, '__call__')
    is_cython = fun.__class__.__name__ == 'cython_function_or_method'
    is_method = inspect.ismethod(fun)

    if not is_function and is_callable and not is_method and not is_cython:
        name, fun = fun.__class__.__name__, fun.__call__
    else:
        name = fun.__name__
    definition = FUNHEAD_TEMPLATE.format(
        fun_name=name,
        fun_args=_argsfromspec(inspect.getfullargspec(fun)),
        fun_value=1,
    )
    if debug:  # pragma: no cover
        print(definition, file=sys.stderr)
    namespace = {'__name__': fun.__module__}
    # pylint: disable=exec-used
    # Tasks are rarely, if ever, created at runtime - exec here is fine.
    exec(definition, namespace)
    result = namespace[name]
    result._source = definition
    if bound:
        return partial(result, object())
    return result

# def test(name:str='race',age:int=24)->str:
    return f'my_name is {name}'

# head_from_fun(test)
# <function __main__.test(name=0, age=1)>
# type(result)
# function


class Celery:
    ''' tasks created by @app.task would be registered 
        and then added to the instance attribute self._tasks
        of the app 
    '''

    def __init__(self):
        if not isinstance(self._tasks, TaskRegistry):
            self._tasks = self.registry_cls(self._tasks or {})

            '''    def register(self, task):
                    """Register a task in the task registry.
                    The task will be automatically instantiated if not already an
                    instance. Name must be configured prior to registration.
                    """
                    if task.name is None:
                        raise InvalidTaskError(
                            'Task class {!r} must specify .name attribute'.format(
                                type(task).__name__))
                    task = inspect.isclass(task) and task() or task
                    add_autoretry_behaviour(task)
                    self[task.name] = task
            '''

    def task(self, *args, **opts):
        """Decorator to create a task class out of any callable.
                @app.task
                def refresh_feed(url):
                    store_feed(feedparser.parse(url))

                @app.task(exchange='feeds')
                def refresh_feed(url):
                    return store_feed(feedparser.parse(url))
        """

        def inner_create_task_cls(shared=True, filter=None, lazy=True, **opts):
            _filt = filter

            def _create_task_cls(fun):
                if shared:
                    def cons(app):
                        return app._task_from_fun(fun, **opts)
                    cons.__name__ = fun.__name__

                    def connect_on_app_finalize(callback):
                        """Connect callback to be called when any app is finalized.
                            _on_app_finalizers = set()
                        """
                        _on_app_finalizers.add(callback)
                        return callback
                    connect_on_app_finalize(cons)

                ret = self._task_from_fun(fun, **opts)

                return ret

            return _create_task_cls

        if len(args) == 1:
            if callable(args[0]):
                return inner_create_task_cls(**opts)(*args)
            raise TypeError('argument 1 to @task() must be a callable')
        if args:  # does not take any positional arguments
            raise TypeError(
                '@task() takes exactly 1 argument ({} given)'.format(sum([len(args), len(opts)])))
        return inner_create_task_cls(**opts)

    def _task_from_fun(self, fun, name=None, base=None, bind=False, **options):
        if not self.finalized and not self.autofinalize:
            raise RuntimeError('Contract breach: app not finalized')
        name = name or self.gen_task_name(fun.__name__, fun.__module__)
        base = base or self.Task

        if name not in self._tasks:
            run = fun if bind else staticmethod(fun)
            task = type(fun.__name__, (base,), dict({
                'app': self,
                'name': name,
                'run': run,
                '_decorated': True,
                '__doc__': fun.__doc__,
                '__module__': fun.__module__,
                '__annotations__': fun.__annotations__,
                '__header__': staticmethod(head_from_fun(fun, bound=bind)),
                '__wrapped__': run}, **options))()
            # for some reason __qualname__ cannot be set in type()
            # so we have to set it here.
            task.__qualname__ = fun.__qualname__

            # add the task cls into the instance attribute app._tasks
            self._tasks[task.name] = task
            task.bind(self)               # connects task to this app
            '''    @classmethod
                    def bind(cls, app):
                        was_bound, cls.__bound__ = cls.__bound__, True
                        cls._app = app
                        conf = app.conf
                        cls._exec_options = None  # clear option cache

                        if cls.typing is None:
                            cls.typing = app.strict_typing

                        for attr_name, config_name in cls.from_config:
                            if getattr(cls, attr_name, None) is None:
                                setattr(cls, attr_name, conf[config_name])

                        # decorate with annotations from config.
                        if not was_bound:
                            cls.annotate()

                            from celery.utils.threads import LocalStack
                            cls.request_stack = LocalStack()

                        cls.on_bound(app)      # PeriodicTask uses this to add itself 
                        return app             # to the PeriodicTask schedule
            '''
            add_autoretry_behaviour(task, **options)
        else:
            task = self._tasks[name]
        return task
