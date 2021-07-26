
import typing as t
from inspect import isclass, isfunction, ismethod,
from logging import getLogger
from functools import partial, wraps
from types import FunctionType, MethodType
from typing import Union


def get_fn_args(decorated, args):
    """Strip "self" and "cls" variables from args.
    For now, this avoids assuming that the "self" variable is called
    "self" on instance methods, although if this winds up being
    problematic for edge use cases, I might move to that model
    and make it clear that instance methods for which "self"
    isn't called "self" won't have their "self" argument stripped.
    """
    fn_args = args
    decor_name = (
        decorated.__name__ if hasattr(decorated, "__name__") else str(decorated)
    )

    # Check if the wrapped function is an attribute on args[0]
    if args and decor_name in dir(args[0]):

        # Check if args[0] is a class reference
        if isclass(args[0]):
            # Check if the wrapped function is a classmethod on the
            # class' class dict
            if type(args[0].__dict__[decor_name]) is classmethod:
                # The first argument is a reference to the class
                # containing the decorated function
                fn_args = args[1:]

        # Check if args[0] is a function defined on the class
        else:
            cls_dict = args[0].__class__.__dict__

            # Check if the wrapped function is a function on the class'
            # class dict (instance methods are functions on the class
            # dict, while classmethods and staticmethods are their own
            # types)
            if decor_name in cls_dict and isfunction(cls_dict[decor_name]):
                # The first argument is probably a "self" variable
                fn_args = args

    return fn_args


class ClassWrapper(object):
    """A generic class wrapper for decorating class functions/methods
    To be used in the context of a decorator that should percolate
    down to methods if used at the class level.
    Intended usage is to create a **new** class, for example by
    using the ``type()`` function, in which the ``wrapped``
    class attribute is replaced by a reference to the class
    being wrapped
    Usage:
    .. code:: python
        def meth_decorator(meth):
            '''The decorator that should be applied to class methods'''
            def wrapper(*args, **kwargs):
                print('performing wrapper tasks')
                func(*args, **kwargs)
                print('finished wrapper tasks')
            return wrapper
        def class_decorator(cls):
            '''Applies meth_decorator to class methods/functions'''
            wrapper = ClassWrapper.wrap(cls, meth_decorator)
            return wrapper
        @class_decorator
        class DecoratedClass:
            def automatically_decorated_method(self):
                pass
    """

    __wrapped__ = None
    __decorator__ = None
    __decoropts__ = None

    def __init__(self, *args, **kwargs):
        self.__wrapped__ = self.__wrapped__(*args, **kwargs)  # type: ignore

    def __getattribute__(self, item):

        if item in ("__wrapped__", "__decorator__", "__decoropts__"):
            return object.__getattribute__(self, item)

        wrapped = object.__getattribute__(self, "__wrapped__")
        attr = getattr(wrapped, item)

        if attr is None:
            raise AttributeError

        if ismethod(attr) or isfunction(attr):
            cls = object.__getattribute__(self, "__class__")
            decoropts = object.__getattribute__(cls, "__decoropts__")
            decor = object.__getattribute__(cls, "__decorator__")

            if decoropts["instance_methods_only"]:
                cls_attr = object.__getattribute__(cls, item)
                if type(cls_attr) is classmethod:
                    return attr
                if type(cls_attr) is staticmethod:
                    return attr

            return decor(attr)

        return attr

    @classmethod
    def _get_class_attrs(cls, wrapped, decorator, instance_methods_only):
        """Get the attrs for a new class instance
        :param type wrapped: a reference to the class to be wrapped
        :param Union[FunctionType,MethodType,type] decorator:
            the decorator to apply to the
            functions and methods of the wrapped class
        """
        attrs = {}

        for k, v in wrapped.__dict__.items():
            if not k.startswith("__"):
                if not instance_methods_only:
                    if type(v) is classmethod:
                        attrs[k] = partial(decorator(v.__func__), wrapped)
                    elif type(v) is staticmethod:
                        attrs[k] = decorator(v.__func__)
                    else:
                        attrs[k] = v
                else:
                    attrs[k] = v

        attrs.update(
            {
                "__wrapped__": wrapped,
                "__decorator__": decorator,
                "__decoropts__": {  # type: ignore
                    "instance_methods_only": instance_methods_only
                },
            }
        )

        return attrs

    @classmethod
    def wrap(cls, wrapped, decorator, instance_methods_only=False):
        """Return a new class wrapping the passed class
        :param type wrapped: a reference to the class to be wrapped
        :param Union[FunctionType,MethodType,type] decorator:
            the decorator to apply to the
            functions and methods of the wrapped class
        """
        name = "Wrapped{}".format(wrapped.__name__)
        return type(
            name,
            (cls,),
            # {'__decorator__': decorator}
            cls._get_class_attrs(wrapped, decorator, instance_methods_only),
        )

DecoratorType = Union[FunctionType, MethodType, type]


class Decorated(object):
    """A representation of a decorated class.
    This user-immutable object provides information about the decorated
    class, method, or function. The decorated callable can be called
    by directly calling the ``Decorated`` instance, or via the
    ``wrapped`` instance attribute.
    The example below illustrates direct instantiation of the
    ``Decorated`` class, but generally you will only deal with
    instances of this class when they are passed to the functions
    specified on generic decorators.
    .. code:: python
        from pydecor import Decorated
        def some_function(*args, **kwargs):
            return 'foo'
        decorated = Decorated(some_function, ('a', 'b'), {'c': 'c'})
        assert decorated.wrapped.__name__ == some_function.__name__
        assert decorated.args == ('a', 'b')
        assert decorated.kwargs == {'c': 'c'}
        assert decorated.result is None  # has not yet been called
        res = decorated(decorated.args, decorated.kwargs)
        assert 'foo' == res == decorated.result
    .. note::
        identity tests ``decorated.wrapped is some_decorated_function``
        will not work on the ``wrapped`` attribute of a ``Decorated``
        instance, because internally the wrapped callable is wrapped
        in a method that ensures that ``Decorated.result`` is set
        whenever the callable is called. It is wrapped using
        ``functools.wraps``, so attributes like ``__name__``,
        ``__doc__``, ``__module__``, etc. should still be the
        same as on an actual reference.
        If you need to access a real reference to the wrapped
        function for any reason, you can do so by accessing
        the ``__wrapped__`` property, on ``wrapped``, which is
        set by ``functools.wraps``, e.g.
        ``decorated.wrapped.__wrapped__``.
    :param wrapped: a reference to the wrapped callable. Calling the
        wrapped callable via this reference will set the ``result``
        attribute.
    :param args: a tuple of arguments with which the decorated function
        was called
    :param kwargs: a dict of arguments with which the decorated function
        was called
    :param result: either ``None`` if the wrapped callable has not yet
        been called or the result of that call
    """

    __slots__ = ("args", "kwargs", "wrapped", "result")

    args: tuple
    kwargs: dict
    wrapped: t.Callable
    result: t.Optional[t.Any]

    def __init__(self, wrapped, args, kwargs, result=None):
        """Instantiate a Decorated object
        :param callable wrapped: the callable object being wrapped
        :param tuple args: args with which the callable was called
        :param dict kwargs: keyword arguments with which the callable
            was called
        :param
        """
        sup = super(Decorated, self)
        sup.__setattr__("args", get_fn_args(wrapped, args))
        sup.__setattr__("kwargs", kwargs)
        sup.__setattr__("wrapped", self._sets_results(wrapped))
        sup.__setattr__("result", result)

    def __str__(self):
        """Return a nice string of self"""
        if hasattr(self.wrapped, "__name__"):
            name = self.wrapped.__name__
        else:
            name = str(self.wrapped)
        return "<Decorated {}({}, {})>".format(name, self.args, self.kwargs)

    def __call__(self, *args, **kwargs):
        """Call the function the specified arguments.
        Also set ``self.result``
        """
        return self.wrapped(*args, **kwargs)

    def __setattr__(self, key, value):
        """Disallow attribute setting"""
        raise AttributeError(
            'Cannot set "{}" because {} is immutable'.format(key, self)
        )

    def _sets_results(self, wrapped):
        """Ensure that calling ``wrapped()`` sets the result attr
        :param callable wrapped: the wrapped function, class, or method
        """

        @wraps(wrapped)
        def wrapped_wrapped(*args, **kwargs):
            """Set self.result after calling wrapped"""
            res = wrapped(*args, **kwargs)
            super(Decorated, self).__setattr__("result", res)
            return res

        return wrapped_wrapped


def before(
    func, implicit_method_decoration=True, instance_methods_only=False, **extras
):
    """Specify a callable to be run before the decorated resource.
    A callable provided to this decorator will be called
    any time the decorated function is executed, immediately _before_
    its execution.
    The callable is expected to either return ``None`` or to return
    a tuple and dict with which to replace the arguments to the
    decorated function.
    The callable is called with an instance of :any:`Decorated` as
    its first positional argument. Any kwargs provided to `before()`
    are also passed to the callable.
    :param Callable func:
        a callable to run before the decorated function. It is called
        with an instance of :any:`Decorated` as its first argument. In
        addition, any keyword arguments provided to `before` are passed
        through to the callable.
    :param bool implicit_method_decoration:
        (default True) if True, decorating a class implies decorating
        all of its methods. Otherwise, the decorator will be called
        when the class is instantiated.
    :param bool instance_methods_only:
        (default False) if True, decorating a class implies decorating
        only its instance methods (not ``classmethod``- or
        ``staticmethod``- decorated methods)
    :param **dict extras:
        any extra keyword arguments supplied to the decoration call,
        which will be passed directly to the provided callable.
    :return: the decorated function/method/class
    :rtype: Union[FunctionType,MethodType,type]
    """

    def decorator(decorated):
        """Return a decorated function."""

        def wrapper(*args, **kwargs):
            """Call the before and decorated functions."""
            fn = func

            decor = Decorated(decorated, args, kwargs)
            fret = fn(decor, **extras)

            if fret is not None:
                args, kwargs = fret

            ret = decor(*args, **kwargs)
            return ret

        if implicit_method_decoration and isclass(decorated):
            return ClassWrapper.wrap(
                decorated,
                decorator,
                instance_methods_only=instance_methods_only,
            )

        # Equivalent to @wraps(decorated) on `wrapper`
        return wraps(decorated)(wrapper)

    return decorator


def after(
    func, implicit_method_decoration=True, instance_methods_only=False, **extras
):
    """Specify a callable to be run after the decorated resource.
    A callable provided to this decorator will be called
    any time the decorated function is executed, immediately _after_
    its execution.
    If the callable returns a value, that value will replace the
    return value of the decorated function.
    The callable is called with an instance of :any:`Decorated` as
    its first positional argument. Any kwargs provided to `after()`
    are also passed to the callable.
    :param Callable func:
        a callable to run after the decorated function. It is called
        with an instance of :any:`Decorated` as its first argument. In
        addition, any keyword arguments provided to `before` are passed
        through to the callable.
    :param bool implicit_method_decoration:
        (default True) if True, decorating a class implies decorating
        all of its methods. Otherwise, the decorator will be called
        when the class is instantiated.
    :param bool instance_methods_only:
        (default False) if True, decorating a class implies decorating
        only its instance methods (not ``classmethod``- or
        ``staticmethod``- decorated methods)
    :param **dict extras:
        any extra keyword arguments supplied to the decoration call,
        which will be passed directly to the provided callable.
    :return: the decorated function/method/class
    :rtype: Union[FunctionType,MethodType,type]
    """

    def decorator(decorated):
        """The function that returns a replacement for the original"""

        def wrapper(*args, **kwargs):
            """The function that replaces the decorated one"""
            decor = Decorated(decorated, args, kwargs)
            orig_ret = decor(*args, **kwargs)
            fret = func(decor, **extras)

            if fret is not None:
                return fret

            return orig_ret

        if implicit_method_decoration and isclass(decorated):
            return ClassWrapper.wrap(
                decorated,
                decorator,
                instance_methods_only=instance_methods_only,
            )

        # Equivalent to @wraps(decorated) on `wrapper`
        return wraps(decorated)(wrapper)

    return decorator


def instead(
    func, implicit_method_decoration=True, instance_methods_only=False, **extras
):
    """Specify a callable to be run in the place of the decorated resource.
    A callable provided to this decorator will be called any time the
    decorated function is executed. The decorated function **will not**
    be called unless the provided callable calls it.
    Whatever the provided callable returns is the return value of the
    decorated function.
    The callable is called with an instance of :any:`Decorated` as
    its first positional argument. Any kwargs provided to `instead()`
    are also passed to the callable.
    :param Callable func:
        a callable to run in place of the decorated function. It is called
        with an instance of :any:`Decorated` as its first argument. In
        addition, any keyword arguments provided to `before` are passed
        through to the callable.
    :param bool implicit_method_decoration:
        (default True) if True, decorating a class implies decorating
        all of its methods. Otherwise, the decorator will be called
        when the class is instantiated.
    :param bool instance_methods_only:
        (default False) if True, decorating a class implies decorating
        only its instance methods (not ``classmethod``- or
        ``staticmethod``- decorated methods)
    :param **dict extras:
        any extra keyword arguments supplied to the decoration call,
        which will be passed directly to the provided callable.
    :return: the decorated function/method/class
    :rtype: Union[FunctionType,MethodType,type]
    """

    def decorator(decorated):
        """The function that returns a replacement for the original"""

        def wrapper(*args, **kwargs):
            """The function that replaces the decorated one"""
            decor = Decorated(decorated, args, kwargs)
            return func(decor, **extras)

        if implicit_method_decoration and isclass(decorated):
            return ClassWrapper.wrap(
                decorated,
                decorator,
                instance_methods_only=instance_methods_only,
            )

        # Equivalent to @wraps(decorated) on `wrapper`
        return wraps(decorated)(wrapper)

    return decorator


def decorate(
    before=None,
    after=None,
    instead=None,
    before_kwargs=None,
    after_kwargs=None,
    instead_kwargs=None,
    implicit_method_decoration=True,
    instance_methods_only=False,
    **extras
):
    """A decorator that combines before, after, and instead decoration.
    The ``before``, ``after``, and ``instead`` decorators are all
    stackable, but this decorator provides a straightforward interface
    for combining them so that you don't have to worry about
    decorator precedence.
    The order the callables are executed in is:
    * before
    * instead / wrapped function
    * after
    This decorator takes three optional keyword arguments, ``before``,
    ``after``, and ``instead``, each of which may be any callable that
    might be provided to those decorators.
    The provided callables will be invoked with the same default
    call signature as for the individual decorators. Call signatures
    and other options may be adjusted by passing ``before_kwargs``,
    ``after_kwargs``, and ``instead_kwargs`` dicts to this decorator,
    which will be directly unpacked into the invocation of the
    individual decorators.
    The ``instance_methods_only`` and ``implicit_method_decoration``
    options may only be changed globally as arguments to this
    decorator, in order to avoid confusion between which decorator
    is being applied to which methods.
    You may specify decorator-specific extras in the various ``opts``
    dictionaries. These will be passed to the provided callables in
    addition to any keyword arguments supplied to the call to
    `decorate()`. If there is a naming conflict, the latter override
    the former.
    :param Callable before:
        a callable to run before the decorated function. It is called
        with an instance of :any:`Decorated` as its first argument. In
        addition, any keyword arguments provided to `before` are passed
        through to the callable.
    :param Callable after:
        a callable to run after the decorated function. It is called
        with an instance of :any:`Decorated` as its first argument. In
        addition, any keyword arguments provided to `before` are passed
        through to the callable.
    :param Callable instead:
        a callable to run in place of the decorated function. It is called
        with an instance of :any:`Decorated` as its first argument. In
        addition, any keyword arguments provided to `before` are passed
        through to the callable.
    :param dict before_kwargs:
        a dictionary of keyword arguments to pass to the ``before``
        decorator. See :any:`before` for supported options.
    :param dict after_kwargs:
        a dictionary of keyword arguments to pass to the ``after``
        decorator. See :any:`after` for supported options.
    :param dict instead_kwargs:
        a dictionary of keyword arguments to pass to the ``instead``
        decorator. See :any:`instead` for supported options
    :param bool implicit_method_decoration:
        (default True) if True, decorating a class implies decorating
        all of its methods. This value overrides any values set in
        the various ``opts`` dictionaries. If False, the decorator(s)
        will be called when the class is instantiated.
    :param bool instance_methods_only:
        (default False) if True, decorating a class implies decorating
        only its instance methods (not ``classmethod``- or
        ``staticmethod``- decorated methods). This value overrides
        any values set in the various ``opts`` dictionaries.
    :param **dict extras:
        any extra keyword arguments supplied to the decoration call.
        These will be passed directly to the `before`, `after`,
        and/or `instead` callables.
    :return: the decorated function/method/class
    :rtype: Union[FunctionType,MethodType,type]
    """

    if all(arg is None for arg in (before, after, instead)):
        raise ValueError(
            'At least one of "before," "after," or "instead" must be provided'
        )

    my_before = before
    my_after = after
    my_instead = instead

    before_kwargs = before_kwargs or {}
    after_kwargs = after_kwargs or {}
    instead_kwargs = instead_kwargs or {}

    for opts in (before_kwargs, after_kwargs, instead_kwargs):
        # Disallow mixing of class-level functionality
        opts["implicit_method_decoration"] = implicit_method_decoration
        opts["instance_methods_only"] = instance_methods_only

    def decorator(decorated):

        wrapped = decorated

        if my_instead is not None:

            global instead
            wrapped = instead(my_instead, **{**instead_kwargs, **extras})(
                wrapped
            )

        if my_before is not None:

            global before
            wrapped = before(my_before, **{**before_kwargs, **extras})(wrapped)

        if my_after is not None:

            global after
            wrapped = after(my_after, **{**after_kwargs, **extras})(wrapped)

        def wrapper(*args, **kwargs):

            return wrapped(*args, **kwargs)

        if implicit_method_decoration and isclass(wrapped):
            return ClassWrapper.wrap(
                decorated,
                decorator,
                instance_methods_only=instance_methods_only,
            )

        return wraps(decorated)(wrapper)

    return decorator


def construct_decorator(
    before=None,
    after=None,
    instead=None,
    before_kwargs=None,
    after_kwargs=None,
    instead_kwargs=None,
    implicit_method_decoration=True,
    instance_methods_only=False,
    **extras
):
    """Return a custom decorator.
    Options are all the same as for :any:`decorate` and are, in fact,
    passed directly to it.
    Once the decorator has been created, it can be used like any
    other decorators in this module. Passing extra keyword arguments
    during the decoration call will pass those extras to the
    provided callables, even if some default extras were already set
    when creating the decorator.
    :return: a decorator that can be used to decorate functions,
        classes, or methods
    :rtype: FunctionType
    """
    return partial(
        decorate,
        before=before,
        after=after,
        instead=instead,
        before_kwargs=before_kwargs,
        after_kwargs=after_kwargs,
        instead_kwargs=instead_kwargs,
        implicit_method_decoration=implicit_method_decoration,
        instance_methods_only=instance_methods_only,
        **extras
    )

########################### EASY READING #####################################
class Decorated:
    args: tuple
    kwargs: dict
    wrapped: t.Callable
    result: t.Optional[t.Any]

    def __init__(self, wrapped, args, kwargs, result=None):
        sup = super(Decorated, self)
        sup.__setattr__("args", get_fn_args(wrapped, args))
        sup.__setattr__("kwargs", kwargs)
        sup.__setattr__("wrapped", self._sets_results(wrapped))
        sup.__setattr__("result", result)

    def __str__(self):
        if hasattr(self.wrapped, "__name__"):
            name = self.wrapped.__name__
        else:
            name = str(self.wrapped)
        return "<Decorated {}({}, {})>".format(name, self.args, self.kwargs)

    def __call__(self, *args, **kwargs):
        return self.wrapped(*args, **kwargs)

    def __setattr__(self, key, value):
        raise AttributeError(
            'Cannot set "{}" because {} is immutable'.format(key, self))

    def _sets_results(self, wrapped):
        @wraps(wrapped)
        def wrapped_wrapped(*args, **kwargs):
            res = wrapped(*args, **kwargs)
            super(Decorated, self).__setattr__("result", res)
            return res
        return wrapped_wrapped


def before(func, implicit_method_decoration=True, instance_methods_only=False, **extras):
    def decorator(decorated):
        def wrapper(*args, **kwargs):
            fn = func
            decor = Decorated(decorated, args, kwargs)
            fret = fn(decor, **extras)

            if fret is not None:
                args, kwargs = fret

            ret = decor(*args, **kwargs)
            return ret

        if implicit_method_decoration and isclass(decorated):
            return ClassWrapper.wrap(decorated, decorator,
                instance_methods_only=instance_methods_only,)
        return wraps(decorated)(wrapper)
    return decorator


def after(func, implicit_method_decoration=True, instance_methods_only=False, **extras):
    def decorator(decorated):
        def wrapper(*args, **kwargs):
            decor = Decorated(decorated, args, kwargs)
            orig_ret = decor(*args, **kwargs)
            fret = func(decor, **extras)

            if fret is not None:
                return fret
            return orig_ret

        if implicit_method_decoration and isclass(decorated):
            return ClassWrapper.wrap(decorated, decorator,
                instance_methods_only=instance_methods_only,)
        return wraps(decorated)(wrapper)
    return decorator


def instead(
    func, implicit_method_decoration=True, instance_methods_only=False, **extras):
    def decorator(decorated):
        def wrapper(*args, **kwargs):
            decor = Decorated(decorated, args, kwargs)
            return func(decor, **extras)

        if implicit_method_decoration and isclass(decorated):
            return ClassWrapper.wrap(decorated, decorator,
                instance_methods_only=instance_methods_only,)
        return wraps(decorated)(wrapper)
    return decorator


def decorate(
    before=None,
    after=None,
    instead=None,
    before_kwargs=None,
    after_kwargs=None,
    instead_kwargs=None,
    implicit_method_decoration=True,
    instance_methods_only=False,
    **extras
):
    if all(arg is None for arg in (before, after, instead)):
        raise ValueError('At least one of "before," "after," or "instead" must be provided')

    my_before = before
    my_after = after
    my_instead = instead

    before_kwargs = before_kwargs or {}
    after_kwargs = after_kwargs or {}
    instead_kwargs = instead_kwargs or {}

    for opts in (before_kwargs, after_kwargs, instead_kwargs):
        opts["implicit_method_decoration"] = implicit_method_decoration
        opts["instance_methods_only"] = instance_methods_only

    def decorator(decorated):
        wrapped = decorated
        if my_instead is not None:
            global instead
            wrapped = instead(my_instead, **{**instead_kwargs, **extras})(wrapped)

        if my_before is not None:
            global before
            wrapped = before(my_before, **{**before_kwargs, **extras})(wrapped)

        if my_after is not None:
            global after
            wrapped = after(my_after, **{**after_kwargs, **extras})(wrapped)

        def wrapper(*args, **kwargs):
            return wrapped(*args, **kwargs)

        if implicit_method_decoration and isclass(wrapped):
            return ClassWrapper.wrap(decorated,decorator,
                instance_methods_only=instance_methods_only,)
        return wraps(decorated)(wrapper)
    return decorator

def construct_decorator(
    before=None,
    after=None,
    instead=None,
    before_kwargs=None,
    after_kwargs=None,
    instead_kwargs=None,
    implicit_method_decoration=True,
    instance_methods_only=False,
    **extras):
    return partial(
        decorate,
        before=before,
        after=after,
        instead=instead,
        before_kwargs=before_kwargs,
        after_kwargs=after_kwargs,
        instead_kwargs=instead_kwargs,
        implicit_method_decoration=implicit_method_decoration,
        instance_methods_only=instance_methods_only,
        **extras)